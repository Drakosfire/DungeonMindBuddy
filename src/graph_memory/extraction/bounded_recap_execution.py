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

DEEPSEEK_MODEL = "deepseek/deepseek-v4.1-flash"

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
) -> tuple[Path, str]:
    """Atomically preserve one returned response without making it public graph data."""
    if not re.fullmatch(r"[a-z0-9_-]+", pass_name):
        raise ValueError("invalid recap pass name for response evidence")

    directory = Path(directory)
    private_root = directory.parent
    for path in (private_root, directory):
        path.mkdir(mode=0o700, parents=False, exist_ok=True)
        if path.is_symlink() or not path.is_dir():
            raise OSError("private response evidence path is not a directory")
        if stat.S_IMODE(path.stat().st_mode) & 0o077:
            raise PermissionError("private response evidence directory is not private")

    request_bytes = _canonical_json_bytes(request)
    system_prompt = request.get("system_prompt")
    user_prompt = request.get("user_prompt")
    response_bytes = response_text.encode("utf-8") if response_text is not None else None
    envelope = {
        "schema": "dmb_private_recap_pass_response_v1",
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
    artifact_bytes = _canonical_json_bytes(envelope) + b"\n"
    filename = f"{ordinal:02d}-{pass_name}.json"
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
    per_call_deadline_ms: int = 60_000
    run_deadline_ms: int = 480_000
    max_output_tokens: int = 8192
    edge_max_output_tokens: int | None = None

    def __post_init__(self) -> None:
        if (self.provider, self.model) not in {
            ("openai", "gpt-6-luna"),
            ("openrouter", DEEPSEEK_MODEL),
        }:
            raise ValueError("unsupported bounded recap provider/model selection")
        for name, ceiling in (
            ("max_calls", 8),
            ("per_call_deadline_ms", 60_000),
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
        return {
            "schema": "dmb_bounded_recap_execution_v1",
            "limits": asdict(self.limits),
            "calls": self.calls,
            "stopped": self._stopped,
        }

    def run_pass(
        self, pass_name, *, model_id, instructions, user_content, pass_spec=None
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
        deepseek = self.limits.provider == "openrouter"
        route = None
        system_prompt = instructions
        if deepseek:
            from generationengine.types import ProviderRoute

            route = ProviderRoute(order=("DeepSeek",), allow_fallbacks=False)
            system_prompt = (
                f"{instructions}\n\nThe JSON object MUST conform to this schema:\n"
                + json.dumps(fmt["schema"], sort_keys=True, separators=(",", ":"))
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
                json_object=True,
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
                {"order": list(route.order), "allow_fallbacks": route.allow_fallbacks}
                if route is not None
                else None
            ),
            "deadline_ms": request.deadline_ms,
            "max_output_tokens": request.max_output_tokens,
            "observation": None,
        }
        self.calls.append(entry)
        result = None
        try:
            request_payload = request.model_dump(mode="json")
            outcome = _execute_in_owned_process(
                self._engine_factory, request_payload,
                deadline=wall_started + request.deadline_ms / 1000,
            )
            entry["wall_clock_ms"] = int((time.monotonic() - wall_started) * 1000)
            entry["worker_cleanup"] = "terminated" if outcome.terminated else "reaped"
            if outcome.terminated:
                self._stopped = True
            receipt = outcome.receipt
            if receipt is None:
                entry["external_outcome"] = "unknown"
                raise CategoryGraphExtractionError(
                    "bounded inference outcome unknown: worker ended without receipt",
                    pass_name=pass_name,
                )
            if receipt["kind"] == "provider_failure":
                entry["observation"] = receipt["observation"]
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
            raw_result = receipt.get("result")
            raw_observation = (
                raw_result.get("observation")
                if isinstance(raw_result, Mapping)
                else None
            )
            raw_text = (
                raw_result.get("text")
                if isinstance(raw_result, Mapping)
                and isinstance(raw_result.get("text"), str)
                else None
            )
            if self._response_artifact_dir is not None:
                # The GE result is already known even if durable evidence cannot be
                # written. Preserve its safe accounting before the fallible sink.
                entry["observation"] = _safe_observation_snapshot(raw_observation)
                try:
                    response_path, response_digest = _write_private_response_evidence(
                        self._response_artifact_dir,
                        ordinal=len(self.calls),
                        pass_name=pass_name,
                        request=request_payload,
                        context_hashes=self._request_context_hashes,
                        raw_observation=raw_observation,
                        response_text=raw_text,
                    )
                except Exception:
                    self._stopped = True
                    entry["consumer_failure"] = "PrivateResponseEvidenceWriteFailed"
                    raise CategoryGraphExtractionError(
                        "private recap response evidence could not be written",
                        pass_name=pass_name,
                        raw_model_response=raw_text,
                    ) from None
                entry["response_artifact_path"] = str(response_path)
                entry["response_artifact_sha256"] = response_digest
            result = TextResult.model_validate(receipt["result"])
            observation = result.observation.model_dump(mode="json")
            entry["observation"] = observation
            if (
                observation["state"] != "completed"
                or observation["retry_count"] != 0
                or observation["conformance_retry_count"] != 0
                or observation.get("transport_retry_count") not in (None, 0)
                or (
                    deepseek
                    and (
                        observation.get("provider") != "openrouter"
                        or observation.get("requested_model") != self.limits.model
                        or observation.get("resolved_model") != self.limits.model
                        or observation.get("provider_attempt_count") != 1
                        or observation.get("response_model") != self.limits.model
                    )
                )
            ):
                raise CategoryGraphExtractionError(
                    "inference did not complete within one attempt", pass_name=pass_name,
                    raw_model_response=result.text,
                )
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
            parsed = json.loads(result.text or "")
            if not isinstance(parsed, dict):
                raise NonObjectResponseError("expected JSON object")
            if deepseek:
                validate_json_schema(parsed, fmt["schema"])
        except (json.JSONDecodeError, NonObjectResponseError, JsonSchemaValidationError) as exc:
            self._stopped = True
            entry["consumer_failure"] = type(exc).__name__
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
