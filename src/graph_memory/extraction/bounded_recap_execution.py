"""Recap pass budgets and metadata receipts; GenerationEngine owns inference IO."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import time
from dataclasses import asdict, dataclass
from functools import partial
from typing import Any, Mapping

from jsonschema import ValidationError as JsonSchemaValidationError
from jsonschema import validate as validate_json_schema

from src.bootstrap_env import load_dungeonmindbuddy_dotenv
from src.graph_memory.extraction._recap_inference_worker import (
    _execute_in_owned_process, _WorkerStartFailure,
)
from src.graph_memory.extraction.category_candidate_graph_extractor import (
    CategoryGraphExtractionError,
)
from src.graph_memory.extraction.category_candidate_graph_schema import (
    category_pass_text_format,
    category_pass_text_format_for_spec,
)

DEEPSEEK_MODEL = "deepseek/deepseek-v4.1-flash-1017"

_SAFE_OBSERVATION_FIELDS = (
    "provider",
    "requested_model",
    "resolved_model",
    "response_model",
    "state",
    "provider_attempt_count",
    "retry_count",
    "conformance_retry_count",
    "transport_retry_count",
    "input_tokens",
    "output_tokens",
    "cached_input_tokens",
    "reasoning_tokens",
    "cost_usd",
    "pricing_source",
    "latency_ms",
    "provider_response_id",
    "failure_code",
)

_SAFE_ATTEMPT_FIELDS = (
    "operation_id",
    "event_id",
    "ordinal",
    "kind",
    "response_status",
    "provider",
    "requested_model",
    "resolved_model",
    "response_model",
    "provider_request_id",
    "provider_response_id",
    "input_tokens",
    "cached_input_tokens",
    "output_tokens",
    "reasoning_tokens",
)

_SAFE_REQUEST_FIELDS = (
    "provider",
    "model",
    "temperature",
    "max_transport_retries",
    "max_output_tokens",
    "deadline_ms",
    "reasoning_effort",
    "json_object",
    "provider_route",
)


def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def _safe_observation_snapshot(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    return {key: value[key] for key in _SAFE_OBSERVATION_FIELDS if key in value}


def _write_private_response_evidence(
    directory: Path,
    *,
    ordinal: int,
    pass_name: str,
    request: Mapping[str, Any],
    context_hashes: Mapping[str, str],
    raw_observation: Any,
    response_text: str | None,
    attempt_event: Mapping[str, Any] | None = None,
) -> tuple[Path, str]:
    """Atomically preserve one returned response without making it public graph data."""
    if not re.fullmatch(r"[a-z0-9_-]+", pass_name):
        raise ValueError("invalid recap pass name for response evidence")

    directory = Path(directory)
    private_root = directory.parent
    private_root.mkdir(mode=0o700, parents=True, exist_ok=True)
    for path in (private_root, directory):
        path.mkdir(mode=0o700, exist_ok=True)
        if path.is_symlink() or not path.is_dir():
            raise OSError("private response evidence path is not a directory")
        if stat.S_IMODE(path.stat().st_mode) & 0o077:
            raise PermissionError("private response evidence directory is not private")

    request_bytes = _canonical_json_bytes(request)
    system_prompt = request.get("system_prompt")
    user_prompt = request.get("user_prompt")
    response_bytes = response_text.encode("utf-8") if response_text is not None else None
    event_facts = None
    if attempt_event is not None:
        event_facts = {
            key: attempt_event.get(key) for key in _SAFE_ATTEMPT_FIELDS
        }
        if type(event_facts["ordinal"]) is not int or event_facts["ordinal"] < 1:
            raise ValueError("invalid GE attempt ordinal")
        if not isinstance(event_facts["event_id"], str) or not event_facts["event_id"]:
            raise ValueError("invalid GE attempt event identifier")
    envelope = {
        "schema": (
            "dmb_private_recap_attempt_response_v1"
            if event_facts is not None
            else "dmb_private_recap_pass_response_v1"
        ),
        "capture_state": "unvalidated_snapshot",
        "pass_ordinal": ordinal,
        "pass_name": pass_name,
        "request": {
            "sha256": hashlib.sha256(request_bytes).hexdigest(),
            "system_prompt_sha256": hashlib.sha256(
                str(system_prompt or "").encode("utf-8")
            ).hexdigest(),
            "user_prompt_sha256": hashlib.sha256(
                str(user_prompt or "").encode("utf-8")
            ).hexdigest(),
            "facts": {key: request[key] for key in _SAFE_REQUEST_FIELDS if key in request},
        },
        "context_sha256": dict(sorted(context_hashes.items())),
        "ge_observation": _safe_observation_snapshot(raw_observation),
        "response": {
            "text": response_text,
            "utf8_bytes": len(response_bytes) if response_bytes is not None else None,
            "sha256": (
                hashlib.sha256(response_bytes).hexdigest()
                if response_bytes is not None
                else None
            ),
        },
    }
    if event_facts is not None:
        envelope["ge_attempt"] = event_facts
    artifact_bytes = _canonical_json_bytes(envelope) + b"\n"
    filename = (
        f"{ordinal:02d}-{pass_name}-attempt-{event_facts['ordinal']:02d}.json"
        if event_facts is not None
        else f"{ordinal:02d}-{pass_name}.json"
    )
    destination = directory / filename
    temporary = directory / f".{filename}.{os.getpid()}.{time.time_ns()}.pending"
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(artifact_bytes)
            stream.flush()
            os.fsync(stream.fileno())
        # Hard-link publication is atomic and fails if the evidence path exists.
        os.link(temporary, destination)
        directory_fd = os.open(directory, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        temporary.unlink(missing_ok=True)

    return destination, hashlib.sha256(artifact_bytes).hexdigest()


def _private_attempt_evidence_index(
    directory: Path,
    *,
    pass_ordinal: int,
    pass_name: str,
    exclude_names: set[str] | None = None,
) -> list[dict[str, Any]]:
    """Index durable response events without copying their private text into the ledger."""
    directory = Path(directory)
    if not directory.is_dir() or directory.is_symlink():
        return []
    prefix = f"{pass_ordinal:02d}-{pass_name}-attempt-"
    excluded = exclude_names or set()
    entries: list[dict[str, Any]] = []
    for path in sorted(directory.glob(f"{prefix}*.json")):
        if path.name in excluded:
            continue
        if path.is_symlink() or not path.is_file():
            continue
        artifact_bytes = path.read_bytes()
        try:
            artifact = json.loads(artifact_bytes)
            event = artifact.get("ge_attempt")
            if not isinstance(event, dict):
                continue
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
        entries.append(
            {
                "event_id": event.get("event_id"),
                "ordinal": event.get("ordinal"),
                "kind": event.get("kind"),
                "response_status": event.get("response_status"),
                "path": str(path),
                "sha256": hashlib.sha256(artifact_bytes).hexdigest(),
            }
        )
    return entries


class NonObjectResponseError(ValueError):
    """A completed JSON response was not the object required by a pass."""


def _safe_validation_path(path, schema: dict[str, Any]) -> list[str | int]:
    """Retain schema-known path labels, never arbitrary response field names."""
    allowed = {
        "properties", "items", "type", "required", "additionalProperties",
        "enum", "minLength", "minimum", "maximum", "pattern", "anyOf",
        "oneOf", "allOf",
    }

    def collect(value: Any) -> None:
        if isinstance(value, dict):
            properties = value.get("properties")
            if isinstance(properties, dict):
                allowed.update(properties)
            for child in value.values():
                collect(child)
        elif isinstance(value, list):
            for child in value:
                collect(child)

    collect(schema)
    return [
        segment if isinstance(segment, int) or segment in allowed else "<unknown>"
        for segment in list(path)[:16]
    ]


@dataclass(frozen=True)
class RecapExecutionLimits:
    provider: str = "openai"
    model: str = "gpt-6-luna"
    max_calls: int = 8
    per_call_deadline_ms: int = 120_000
    run_deadline_ms: int = 480_000
    max_output_tokens: int = 8192
    edge_max_output_tokens: int | None = None

    def __post_init__(self) -> None:
        if (self.provider, self.model) not in {
            ("openai", "gpt-6-luna"),
            ("openrouter", DEEPSEEK_MODEL),
        }:
            raise ValueError("unsupported bounded recap provider/model selection")
        if type(self.max_calls) is not int or self.max_calls < 1:
            raise ValueError("max_calls must be a positive integer")
        for name, ceiling in (
            ("per_call_deadline_ms", 120_000),
            ("run_deadline_ms", 480_000),
            ("max_output_tokens", 8192),
        ):
            value = getattr(self, name)
            if type(value) is not int or not 1 <= value <= ceiling:
                raise ValueError(f"{name} must be 1..{ceiling}")
        if self.edge_max_output_tokens is not None and (
            type(self.edge_max_output_tokens) is not int
            or not 1 <= self.edge_max_output_tokens <= 16_384
        ):
            raise ValueError("edge_max_output_tokens must be None or an int in 1..16384")


def _default_engine_for(provider: str):
    from generationengine import GenerationClient

    if provider == "openrouter":
        from generationengine.providers.openrouter_text import OpenRouterTextProvider

        load_dungeonmindbuddy_dotenv(override=False)
        key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get(
            "DUNGEONBUDDY_OPENROUTER"
        )
        if not key or not key.strip():
            raise CategoryGraphExtractionError(
                "OpenRouter credential is unavailable for bounded recap extraction"
            )
        return GenerationClient(
            text_providers={"openrouter": OpenRouterTextProvider(api_key=key.strip())}
        )
    return GenerationClient()


class BoundedRecapPassClient:
    supports_actor_source_handles = True

    def __init__(
        self,
        limits: RecapExecutionLimits,
        *,
        engine_factory=None,
        clock=time.monotonic,
        response_artifact_dir: str | os.PathLike[str] | None = None,
        request_context_hashes: Mapping[str, str] | None = None,
    ):
        from generationengine.types import TextRequest

        if (response_artifact_dir is None) != (request_context_hashes is None):
            raise ValueError(
                "private response evidence requires both a sink and context hashes"
            )
        if request_context_hashes is not None:
            if not request_context_hashes or any(
                not isinstance(name, str)
                or not name
                or not isinstance(digest, str)
                or not re.fullmatch(r"[0-9a-f]{64}", digest)
                for name, digest in request_context_hashes.items()
            ):
                raise ValueError("private response context must contain SHA-256 digests")

        self.limits = limits
        self._engine_factory = engine_factory or partial(_default_engine_for, limits.provider)
        self._request_type = TextRequest
        self._clock = clock
        self._started = clock()
        self._response_artifact_dir = (
            Path(response_artifact_dir) if response_artifact_dir is not None else None
        )
        self._request_context_hashes = dict(request_context_hashes or {})
        self.calls: list[dict[str, Any]] = []
        self._stopped = False

    def ledger(self) -> dict[str, Any]:
        def aggregate(field: str) -> dict[str, Any]:
            known = 0
            complete = True
            for call in self.calls:
                observation = call.get("observation")
                value = observation.get(field) if isinstance(observation, Mapping) else None
                if type(value) is int and value >= 0:
                    known += value
                elif call.get("external_outcome") == "not_started":
                    continue
                else:
                    complete = False
            return {
                "total": known if complete else None,
                "known_total": known,
                "complete": complete,
            }

        return {
            "schema": "dmb_bounded_recap_execution_v1",
            "limits": asdict(self.limits),
            "pass_invocation_count": len(self.calls),
            "pass_invocation_limit": self.limits.max_calls,
            "attempt_counts": {
                "provider_attempts": aggregate("provider_attempt_count"),
                "transport_retries": aggregate("transport_retry_count"),
                "conformance_retries": aggregate("conformance_retry_count"),
                "semantics": (
                    "max_calls is a pass-invocation budget, not a provider-attempt "
                    "or authorization ceiling; provider-attempt counts include "
                    "GE conformance corrections"
                ),
            },
            "calls": self.calls,
            "stopped": self._stopped,
        }

    def run_pass(
        self, pass_name, *, model_id, instructions, user_content, pass_spec=None,
        source_evidence_packet=None,
    ):
        from generationengine.types import TextResult

        wall_started = time.monotonic()

        remaining = self.limits.run_deadline_ms - int(
            (self._clock() - self._started) * 1000
        )
        if (
            self._stopped
            or model_id != self.limits.model
            or len(self.calls) >= self.limits.max_calls
            or remaining <= 0
        ):
            self._stopped = True
            raise CategoryGraphExtractionError(
                "bounded recap execution stopped before inference", pass_name=pass_name
            )
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            pass
        else:
            self._stopped = True
            raise CategoryGraphExtractionError(
                "bounded recap execution requires a synchronous worker",
                pass_name=pass_name,
            )
        fmt = (
            category_pass_text_format_for_spec(pass_spec)
            if pass_spec
            else category_pass_text_format(pass_name)
        )["format"]
        canonical_schema = fmt["schema"]
        context_hashes = dict(self._request_context_hashes)
        if source_evidence_packet is not None:
            from src.graph_memory.extraction.source_sentence_evidence import actor_wire_schema
            if pass_name != "actor_pass":
                raise CategoryGraphExtractionError("source handles require actor pass", pass_name=pass_name)
            expected_source = context_hashes.get("source_content")
            if expected_source is not None and expected_source != source_evidence_packet.source_sha256:
                raise CategoryGraphExtractionError("source packet does not match run source", pass_name=pass_name)
            fmt["schema"] = actor_wire_schema(canonical_schema, source_evidence_packet)
            context_hashes.update(
                actor_source=source_evidence_packet.source_sha256,
                actor_source_packet=source_evidence_packet.packet_id,
            )
        deepseek = self.limits.provider == "openrouter"
        route = None
        system_prompt = instructions
        if deepseek:
            from generationengine.types import ProviderRoute

            route = ProviderRoute(
                order=("DeepSeek",),
                allow_fallbacks=False,
                require_parameters=True,
            )
            system_prompt = (
                f"{instructions}\n\n"
                "Return exactly one complete JSON object, without Markdown fences "
                "or surrounding prose. Escape quotes, backslashes, and control "
                "characters as JSON requires, and close every string and "
                "container."
            )
        request_kwargs: dict[str, Any] = {
            "user_prompt": user_content,
            "system_prompt": system_prompt,
            "provider": self.limits.provider,
            "model": self.limits.model,
            "temperature": None,
            "max_transport_retries": 0,
            "max_output_tokens": (
                self.limits.edge_max_output_tokens
                if pass_spec is not None
                and getattr(pass_spec, "kind", None) == "edge"
                and self.limits.edge_max_output_tokens is not None
                else self.limits.max_output_tokens
            ),
            "deadline_ms": min(remaining, self.limits.per_call_deadline_ms),
        }
        if deepseek:
            request_kwargs.update(
                provider_route=route,
                reasoning_effort="none",
                json_schema=fmt["schema"],
                schema_name=fmt["name"],
            )
        else:
            request_kwargs.update(json_schema=fmt["schema"], schema_name=fmt["name"])
        request = self._request_type(**request_kwargs)
        entry = {
            "ordinal": len(self.calls) + 1,
            "pass_name": pass_name,
            "requested_provider": self.limits.provider,
            "model": self.limits.model,
            "requested_route": (
                {
                    "order": list(route.order),
                    "allow_fallbacks": route.allow_fallbacks,
                    "require_parameters": route.require_parameters,
                }
                if route is not None
                else None
            ),
            "deadline_ms": request.deadline_ms,
            "max_output_tokens": request.max_output_tokens,
            "observation": None,
            "attempt_evidence": [],
            "source_evidence_context": context_hashes if source_evidence_packet is not None else None,
        }
        self.calls.append(entry)
        result = None
        try:
            request_payload = request.model_dump(mode="json")
            evidence_prefix = f"{len(self.calls):02d}-{pass_name}-attempt-"
            preexisting_evidence = (
                {
                    path.name
                    for path in self._response_artifact_dir.glob(f"{evidence_prefix}*.json")
                }
                if self._response_artifact_dir is not None
                and self._response_artifact_dir.is_dir()
                else set()
            )
            outcome = _execute_in_owned_process(
                self._engine_factory, request_payload,
                deadline=wall_started + request.deadline_ms / 1000,
                attempt_evidence=(
                    {
                        "directory": str(self._response_artifact_dir),
                        "pass_ordinal": len(self.calls),
                        "pass_name": pass_name,
                        "context_hashes": context_hashes,
                    }
                    if self._response_artifact_dir is not None
                    else None
                ),
            )
            entry["wall_clock_ms"] = int((time.monotonic() - wall_started) * 1000)
            entry["worker_cleanup"] = "terminated" if outcome.terminated else "reaped"
            if outcome.terminated:
                self._stopped = True
            if self._response_artifact_dir is not None:
                entry["attempt_evidence"] = _private_attempt_evidence_index(
                    self._response_artifact_dir,
                    pass_ordinal=len(self.calls),
                    pass_name=pass_name,
                    exclude_names=preexisting_evidence,
                )
            receipt = outcome.receipt
            if receipt is None:
                entry["external_outcome"] = "unknown"
                raise CategoryGraphExtractionError(
                    "bounded inference outcome unknown: worker ended without receipt",
                    pass_name=pass_name,
                )
            if receipt["kind"] == "provider_failure":
                entry["observation"] = _safe_observation_snapshot(receipt["observation"])
                entry["failure_code"] = receipt["failure_code"]
                entry["external_outcome"] = "known_failure"
                if receipt["failure_code"] == "STRUCTURED_OUTPUT_INVALID":
                    entry["consumer_outcome"] = "invalid_structured_output"
                elif receipt["failure_code"] == "ATTEMPT_EVIDENCE_PERSISTENCE_FAILED":
                    entry["consumer_failure"] = "AttemptEvidencePersistenceFailed"
                raise CategoryGraphExtractionError(
                    "bounded inference failed: " + receipt["failure_code"],
                    pass_name=pass_name,
                )
            if receipt["kind"] == "worker_failure":
                entry["external_outcome"] = "unknown"
                entry["consumer_failure"] = receipt["error_type"]
                raise CategoryGraphExtractionError(
                    "bounded inference outcome unknown: worker failed without GE receipt",
                    pass_name=pass_name,
                )
            if entry["attempt_evidence"]:
                final_attempt = entry["attempt_evidence"][-1]
                entry["response_artifact_path"] = final_attempt["path"]
                entry["response_artifact_sha256"] = final_attempt["sha256"]
            result = TextResult.model_validate(receipt["result"])
            observation = result.observation.model_dump(mode="json")
            entry["observation"] = observation
            conformance_retries = observation["conformance_retry_count"]
            if (
                observation["state"] != "completed"
                or observation["retry_count"] != 0
                or conformance_retries not in (0, 1)
                or observation.get("transport_retry_count") not in (None, 0)
                or observation.get("provider_attempt_count") != 1 + conformance_retries
                or (
                    deepseek
                    and (
                        observation.get("provider") != "openrouter"
                        or observation.get("requested_model") != self.limits.model
                        or observation.get("resolved_model") != self.limits.model
                        or observation.get("response_model") != self.limits.model
                    )
                )
            ):
                raise CategoryGraphExtractionError(
                    "inference did not complete within the bounded structured attempt policy",
                    pass_name=pass_name,
                    raw_model_response=result.text,
                )
            entry["external_outcome"] = "completed"
        except CategoryGraphExtractionError:
            self._stopped = True
            raise
        except Exception as exc:
            self._stopped = True
            entry["consumer_failure"] = type(exc).__name__
            if isinstance(exc, _WorkerStartFailure):
                entry["external_outcome"] = "not_started"
            raise CategoryGraphExtractionError(
                "bounded extraction pass failed", pass_name=pass_name,
                raw_model_response=result.text if result is not None else None,
            ) from None
        try:
            # GE validates structured output and may accept fenced provider text.
            # Keep raw text as evidence; consume its parsed contract when supplied.
            parsed = result.parsed if result.parsed is not None else json.loads(result.text or "")
            if not isinstance(parsed, dict):
                raise NonObjectResponseError("expected JSON object")
            if deepseek or source_evidence_packet is not None:
                validate_json_schema(parsed, fmt["schema"])
            if source_evidence_packet is not None:
                from src.graph_memory.extraction.source_sentence_evidence import materialize_actor_evidence
                parsed = materialize_actor_evidence(
                    source_evidence_packet, parsed,
                    expected_packet_id=context_hashes["actor_source_packet"],
                )
                validate_json_schema(parsed, canonical_schema)
                if self._response_artifact_dir is not None:
                    path, sha = _write_private_response_evidence(
                        self._response_artifact_dir,
                        ordinal=len(self.calls), pass_name=pass_name + "-normalized",
                        request=request_payload, context_hashes=context_hashes,
                        raw_observation=observation,
                        response_text=json.dumps({
                            "parsed": parsed,
                            "source_units": [asdict(unit) for unit in source_evidence_packet.units],
                        }, ensure_ascii=False),
                    )
                    entry["normalized_artifact"] = {"path": str(path), "sha256": sha}
        except (json.JSONDecodeError, NonObjectResponseError, JsonSchemaValidationError) as exc:
            self._stopped = True
            entry["consumer_failure"] = type(exc).__name__
            if isinstance(exc, json.JSONDecodeError):
                entry["consumer_outcome"] = "invalid_json"
            entry["validation_failure"] = {
                "kind": (
                    "schema" if isinstance(exc, JsonSchemaValidationError)
                    else "invalid_json" if isinstance(exc, json.JSONDecodeError)
                    else "non_object"
                ),
                "validator": (
                    exc.validator
                    if isinstance(exc, JsonSchemaValidationError)
                    and exc.validator in {
                        "type", "required", "additionalProperties", "enum", "minLength",
                        "minimum", "maximum", "pattern", "anyOf", "oneOf", "allOf",
                    }
                    else None
                ),
                "instance_path": (
                    _safe_validation_path(exc.path, fmt["schema"])
                    if isinstance(exc, JsonSchemaValidationError) else []
                ),
                "schema_path": (
                    _safe_validation_path(exc.schema_path, fmt["schema"])
                    if isinstance(exc, JsonSchemaValidationError) else []
                ),
                **(
                    {
                        "position": exc.pos,
                        "line": exc.lineno,
                        "column": exc.colno,
                        "response_chars": len(result.text or ""),
                        "response_utf8_bytes": len((result.text or "").encode("utf-8")),
                        "response_sha256": hashlib.sha256(
                            (result.text or "").encode("utf-8")
                        ).hexdigest(),
                    }
                    if isinstance(exc, json.JSONDecodeError)
                    else {}
                ),
            }
            raise CategoryGraphExtractionError(
                "bounded extraction pass failed", pass_name=pass_name,
                raw_model_response=result.text,
            ) from None
        except Exception as exc:
            self._stopped = True
            entry["consumer_failure"] = type(exc).__name__
            raise CategoryGraphExtractionError(
                "bounded extraction pass failed", pass_name=pass_name,
                raw_model_response=result.text,
            ) from None
        return {
            "parsed": parsed,
            "raw_text": result.text,
            "usage": {
                "input_tokens": observation["input_tokens"],
                "output_tokens": observation["output_tokens"],
                "cached_tokens": observation["cached_input_tokens"],
            },
            "cost_usd": observation["cost_usd"],
            "elapsed_ms": observation["latency_ms"],
            "response_id": observation["provider_response_id"],
        }
