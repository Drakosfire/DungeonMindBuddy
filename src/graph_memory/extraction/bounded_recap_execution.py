"""Recap pass budgets and metadata receipts; GenerationEngine owns inference IO."""

from __future__ import annotations

import asyncio
import hashlib
import json
import math
import os
import re
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

from src.graph_memory.extraction.recap_extraction_profile import RECAP_EXTRACTION_PROFILE

DEEPSEEK_MODEL = "deepseek/deepseek-v4.1-flash-1017"
SUPPORTED_INGESTION_PROVIDERS = frozenset({"openai", "openrouter", "vercel"})

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
    "known_cost_usd",
    "cost_status",
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
    "cost_usd",
    "pricing_source",
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
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")


def _safe_observation_snapshot(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    return {key: value[key] for key in _SAFE_OBSERVATION_FIELDS if key in value}


def _acknowledged_attempts(entries) -> list[dict[str, Any]]:
    """One safe metric view per acknowledged GE event, never a full-operation receipt."""
    if not isinstance(entries, list):
        raise ValueError("invalid retained attempt evidence")
    events: dict[str, dict[str, Any]] = {}
    responses: dict[str, str] = {}
    for entry in entries:
        if not isinstance(entry, Mapping):
            raise ValueError("invalid retained attempt evidence")
        if entry.get("response_status") not in {"returned", "refused", "incomplete"}:
            continue
        event_id = entry.get("event_id")
        if not isinstance(event_id, str) or not event_id:
            raise ValueError("returned attempt requires a stable event identifier")
        safe = {key: entry[key] for key in _SAFE_ATTEMPT_FIELDS if key in entry}
        for field in ("input_tokens", "output_tokens", "cached_input_tokens", "reasoning_tokens"):
            value = safe.get(field)
            if value is not None and (type(value) is not int or value < 0):
                raise ValueError("invalid returned attempt token count")
        cost = safe.get("cost_usd")
        if cost is not None and (isinstance(cost, bool) or not isinstance(cost, (int, float))
                                 or not math.isfinite(cost) or cost < 0):
            raise ValueError("invalid returned attempt cost")
        prior = events.setdefault(event_id, {})
        for key, value in safe.items():
            if value is not None and prior.get(key) is not None and prior[key] != value:
                raise ValueError("conflicting returned attempt evidence")
            if value is not None or key not in prior:
                prior[key] = value
        response_id = prior.get("provider_response_id")
        if response_id is not None:
            if not isinstance(response_id, str) or not response_id:
                raise ValueError("invalid returned response identifier")
            if responses.setdefault(response_id, event_id) != event_id:
                raise ValueError("returned response belongs to multiple attempt events")
    return list(events.values())


def _private_response_envelope(
    *, binding: Mapping[str, Any], ordinal: int, pass_name: str,
    request: Mapping[str, Any], context_hashes: Mapping[str, str],
    raw_observation: Any, response_text: str | None,
    attempt_event: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Preserve private response bytes/context without inventing source authority."""
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
    envelope["execution_binding"] = dict(binding)
    envelope["capture_id"] = (
        f"attempt:{ordinal}:{event_facts['event_id']}"
        if event_facts is not None else f"normalized:{ordinal}:{pass_name}"
    )
    return envelope


def _persist_attempt_response(evidence, request, event) -> dict[str, Any]:
    from application_state.ingest.components import persist_execution_event

    payload = event.model_dump(mode="json")
    envelope = _private_response_envelope(
        binding=evidence["binding"], ordinal=evidence["pass_ordinal"],
        pass_name=evidence["pass_name"], request=request,
        context_hashes=evidence["context_hashes"], raw_observation=payload,
        response_text=event.text, attempt_event=payload,
    )
    digest = persist_execution_event(
        binding=evidence["binding"], kind="raw_model_response",
        payload=_canonical_json_bytes(envelope) + b"\n",
    )
    return {key: payload[key] for key in ("event_id", "ordinal", "kind", "response_status")} | {
        "capture_id": envelope["capture_id"], "sha256": digest,
    }


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
    reasoning_effort: str | None = None

    def __post_init__(self) -> None:
        if (
            not isinstance(self.provider, str)
            or self.provider.strip().lower() not in SUPPORTED_INGESTION_PROVIDERS
        ):
            raise ValueError("unsupported bounded recap provider selection")
        if not isinstance(self.model, str) or not self.model.strip():
            raise ValueError("bounded recap model must be nonblank")
        object.__setattr__(self, "provider", self.provider.strip().lower())
        object.__setattr__(self, "model", self.model.strip())
        if self.reasoning_effort is not None:
            if (
                not isinstance(self.reasoning_effort, str)
                or not self.reasoning_effort.strip()
            ):
                raise ValueError("reasoning effort must be None or nonblank")
            object.__setattr__(self, "reasoning_effort", self.reasoning_effort.strip())
        if type(self.max_calls) is not int or self.max_calls < 1:
            raise ValueError("max_calls must be a positive integer")
        for name, ceiling in (
            ("per_call_deadline_ms", 240_000),
            ("run_deadline_ms", 900_000),
            ("max_output_tokens", 32_768),
        ):
            value = getattr(self, name)
            if type(value) is not int or not 1 <= value <= ceiling:
                raise ValueError(f"{name} must be 1..{ceiling}")
        if self.edge_max_output_tokens is not None and (
            type(self.edge_max_output_tokens) is not int
            or not 1 <= self.edge_max_output_tokens <= 32_768
        ):
            raise ValueError("edge_max_output_tokens must be None or an int in 1..32768")


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
    if provider == "vercel":
        load_dungeonmindbuddy_dotenv(override=False)
    return GenerationClient()


class BoundedRecapPassClient:
    supports_node_source_handles = True

    def __init__(
        self,
        limits: RecapExecutionLimits,
        *,
        engine_factory=None,
        clock=time.monotonic,
        request_context_hashes: Mapping[str, str] | None = None,
        supplemental_context: str | None = None,
    ):
        from generationengine.types import TextRequest

        if request_context_hashes is not None:
            if not request_context_hashes or any(
                not isinstance(name, str)
                or not name
                or not isinstance(digest, str)
                or not re.fullmatch(r"[0-9a-f]{64}", digest)
                for name, digest in request_context_hashes.items()
            ):
                raise ValueError("private response context must contain SHA-256 digests")

        if supplemental_context is not None and (
            not isinstance(supplemental_context, str) or len(supplemental_context) > 26000
        ):
            raise ValueError("Supplemental evidence context exceeds its bound")
        self.supplemental_context=supplemental_context
        self.limits = limits
        self._engine_factory = engine_factory or partial(_default_engine_for, limits.provider)
        self._request_type = TextRequest
        self._clock = clock
        self._started = clock()
        self.execution_binding: dict[str, Any] | None = None
        self.retention_failed = False
        self._request_context_hashes = dict(request_context_hashes or {})
        self.calls: list[dict[str, Any]] = []
        self._advertised_node_span_ids: tuple[str, ...] | None = None
        self._stopped = False

    def bind_to_run(self, run) -> None:
        from application_state.ingest.components import execution_evidence_binding

        if self.calls or self.execution_binding is not None:
            raise ValueError("bounded client already used or bound")
        binding = execution_evidence_binding(run_id=run.run_id, expected_revision=run.revision)
        if binding["model_id"] != self.limits.model:
            raise ValueError("bounded client model differs from prepared run")
        expected = self._request_context_hashes.get("source_content")
        if expected is not None and expected != binding["source_sha256"]:
            raise ValueError("bounded client context differs from prepared source")
        self.execution_binding = binding
        self._request_context_hashes.update({
            "source_content": binding["source_sha256"],
            "source_identity": hashlib.sha256(binding["source_artifact_id"].encode()).hexdigest(),
            "profile_identity": hashlib.sha256(binding["profile_id"].encode()).hexdigest(),
        })

    def retain_compact_evidence_context(self, record: Mapping[str, Any]) -> None:
        """Seal the request-local dictionary before any provider dispatch."""
        if (self.execution_binding is None or self.calls or self._advertised_node_span_ids is not None
                or record.get("schema") != "dmb_compact_recap_evidence_context_v1"
                or record.get("source_sha256") != self.execution_binding["source_sha256"]):
            raise ValueError("compact evidence context differs from prepared source")
        span_ids = tuple(entry["source_span_ref_id"] for entry in record["entries"])
        self._persist_capture("pass_telemetry", {
            "schema": "dmb_private_compact_evidence_context_v1",
            "capture_id": "context:compact-evidence-v1",
            "execution_binding": dict(self.execution_binding),
            "context": dict(record),
            "node_evidence_status": "available" if span_ids else "no_advertised_paragraphs",
        })
        if not span_ids:
            self._stopped = True
            raise ValueError("standard recap node passes require advertised source paragraphs")
        self._advertised_node_span_ids = span_ids

    def _persist_capture(self, kind, record):
        from application_state.ingest.components import persist_execution_event

        try:
            return persist_execution_event(
                binding=self.execution_binding, kind=kind,
                payload=_canonical_json_bytes(record) + b"\n",
            )
        except Exception:
            self.retention_failed = True
            raise

    def _execution_records(self):
        from application_state.ingest.components import list_private_execution_events

        try:
            return list_private_execution_events(
                binding=self.execution_binding,
                expected_revision=self.execution_binding["prepared_revision"],
            )
        except Exception:
            self.retention_failed = True
            raise

    def _attempt_index(self, ordinal, pass_name):
        entries = []
        for row in self._execution_records():
            record = row["record"]
            if (record.get("pass_ordinal") != ordinal or record.get("pass_name") != pass_name
                    or "ge_attempt" not in record):
                continue
            event = record["ge_attempt"]
            entries.append({key: event[key] for key in _SAFE_ATTEMPT_FIELDS if key in event} | {
                "capture_id": record["capture_id"], "sha256": row["sha256"],
            })
        _acknowledged_attempts(entries)  # Reject conflicting identities/metrics before sealing.
        return sorted(entries, key=lambda entry: (entry["ordinal"], entry["event_id"]))

    def seal_execution(self, *, private_response=None, error=None):
        """Compose existing advisory evidence and committed captures before freeze."""
        if self.execution_binding is None:
            raise RuntimeError("execution evidence has no prepared binding")
        binding = self.execution_binding
        self._persist_capture("pass_telemetry", {
            "schema": "dmb_bounded_recap_execution_v1",
            "execution_binding": binding, "capture_id": "execution-outcome",
            "execution": self.ledger(),
        })
        if self.retention_failed:
            raise RuntimeError("required execution capture needs reconciliation")
        records = self._execution_records()
        if private_response is not None:
            try:
                bundle = json.loads(private_response)
            except (ValueError, TypeError):
                bundle = None
        else:
            bundle = None
        if private_response is not None and error is None and (
            not isinstance(bundle, dict)
            or bundle.get("schema") != "dmb_private_extraction_review_bundle_v1"
        ):
            raise ValueError("invalid private extraction success evidence")
        if (isinstance(bundle, dict) and bundle.get("schema") in {
                "dmb_private_extraction_review_bundle_v1", "dmb_private_extraction_failure_bundle_v1"}):
            if (bundle.get("source_artifact_id") != binding["source_artifact_id"]
                    or bundle.get("source_sha256") != binding["source_sha256"]
                    or bundle.get("profile") != binding["profile_id"]):
                raise ValueError("private advisory evidence identity mismatch")
            bundle["original_review_evidence_utf8"] = private_response
        else:
            bundle = {
                "schema": "dmb_private_extraction_failure_bundle_v1" if error else "dmb_private_extraction_review_bundle_v1",
                "profile": binding["profile_id"],
                "source_artifact_id": binding["source_artifact_id"],
                "source_sha256": binding["source_sha256"],
                "completed_passes": [], "pending_pass": None, "advisory": None,
                "execution_observations": self.ledger()["calls"],
            }
            if error is not None or private_response is not None:
                bundle["failure"] = {"type": type(error).__name__ if error else None,
                                     "raw_text": private_response}
        bundle["execution_evidence"] = {"binding": binding, "records": [
            {"kind": row["kind"], "sha256": row["sha256"], "envelope": row["record"]}
            for row in records
        ]}
        ledger = {**self.ledger(), "binding": binding, "run_id": binding["run_id"],
                  "source_artifact_id": binding["source_artifact_id"],
                  "source_sha256": binding["source_sha256"]}
        return _canonical_json_bytes(bundle) + b"\n", _canonical_json_bytes(ledger) + b"\n"

    def ledger(self) -> dict[str, Any]:
        def aggregate(field: str) -> dict[str, Any]:
            known = 0
            complete = True
            for call in self.calls:
                observation = call.get("observation")
                value = observation.get(field) if isinstance(observation, Mapping) else None
                returned = len(_acknowledged_attempts(call.get("attempt_evidence", [])))
                uncertain = call.get("external_outcome") == "unknown" or (
                    isinstance(observation, Mapping) and observation.get("state") == "unknown"
                )
                if type(value) is int and value >= 0:
                    if field == "provider_attempt_count" and value < returned and not uncertain:
                        raise ValueError("operation count conflicts with returned attempts")
                    known += max(value, returned) if field == "provider_attempt_count" else value
                    complete = complete and not uncertain
                elif call.get("external_outcome") == "not_started":
                    if returned:
                        raise ValueError("not-started operation has returned attempts")
                    continue
                else:
                    complete = False
                    if field == "provider_attempt_count":
                        known += returned
            return {
                "total": known if complete else None,
                "known_total": known,
                "complete": complete,
            }

        return {
            "schema": "dmb_bounded_recap_execution_v1",
            "limits": asdict(self.limits),
            "pass_invocation_count": len(self.calls),
            "acknowledged_response_count": sum(len(_acknowledged_attempts(call.get("attempt_evidence", []))) for call in self.calls),
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
        advertised_node_schema = (
            self._advertised_node_span_ids is not None
            and pass_spec is not None and pass_spec.kind == "node"
            and source_evidence_packet is None
        )
        if advertised_node_schema:
            from src.graph_memory.extraction.category_candidate_graph_schema import node_schema_with_advertised_spans
            fmt["schema"] = node_schema_with_advertised_spans(
                canonical_schema, self._advertised_node_span_ids,
            )
        if source_evidence_packet is not None:
            from src.graph_memory.extraction.source_sentence_evidence import node_wire_schema
            if ((pass_spec is not None and pass_spec.kind != "node")
                    or pass_name not in {p.pass_id for p in RECAP_EXTRACTION_PROFILE.node_passes}):
                raise CategoryGraphExtractionError("source handles require a recap node pass", pass_name=pass_name)
            expected_source = context_hashes.get("source_content")
            if expected_source is not None and expected_source != source_evidence_packet.source_sha256:
                raise CategoryGraphExtractionError("source packet does not match run source", pass_name=pass_name)
            fmt["schema"] = node_wire_schema(canonical_schema, source_evidence_packet)
            context_hashes.update(
                node_source=source_evidence_packet.source_sha256,
                node_source_packet=source_evidence_packet.packet_id,
            )
        deepseek = (self.limits.provider, self.limits.model) == ("openrouter", DEEPSEEK_MODEL)
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
            "user_prompt": user_content+("\n\n"+self.supplemental_context if self.supplemental_context else ""),
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
                reasoning_effort=(
                    self.limits.reasoning_effort
                    if self.limits.reasoning_effort is not None else "none"
                ),
                json_schema=fmt["schema"],
                schema_name=fmt["name"],
            )
        else:
            request_kwargs.update(json_schema=fmt["schema"], schema_name=fmt["name"])
            if self.limits.reasoning_effort is not None:
                request_kwargs["reasoning_effort"] = self.limits.reasoning_effort
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
            "reasoning_effort": request.reasoning_effort,
            "observation": None,
            "attempt_evidence": [],
            "source_evidence_context": context_hashes if source_evidence_packet is not None else None,
        }
        self.calls.append(entry)
        result = None
        try:
            request_payload = request.model_dump(mode="json")
            if self.execution_binding is not None:
                try:
                    self._persist_capture("pass_telemetry", {
                        "schema": "dmb_private_extraction_invocation_v1",
                        "execution_binding": self.execution_binding,
                        "capture_id": f"invocation:{len(self.calls)}",
                        "request_sha256": hashlib.sha256(_canonical_json_bytes(request_payload)).hexdigest(),
                        "call": dict(entry),
                    })
                except Exception:
                    entry["external_outcome"] = "not_started"
                    raise
            try:
                outcome = _execute_in_owned_process(
                    self._engine_factory, request_payload,
                    deadline=wall_started + request.deadline_ms / 1000,
                    attempt_evidence=(
                        {"binding": self.execution_binding,
                         "pass_ordinal": len(self.calls), "pass_name": pass_name,
                         "context_hashes": context_hashes}
                        if self.execution_binding is not None else None
                    ),
                )
            finally:
                # Database recovery also runs after malformed/missing IPC or a
                # real child kill. Receipt metadata never substitutes for bytes.
                if self.execution_binding is not None:
                    entry["attempt_evidence"] = self._attempt_index(len(self.calls), pass_name)
            entry["wall_clock_ms"] = int((time.monotonic() - wall_started) * 1000)
            entry["worker_cleanup"] = "terminated" if outcome.terminated else "reaped"
            if not outcome.cleanup_confirmed:
                entry["worker_cleanup"] = "unconfirmed"
                self._stopped = True
            if outcome.terminated:
                self._stopped = True
            receipt = outcome.receipt
            if receipt is None:
                entry["external_outcome"] = "unknown"
                raise CategoryGraphExtractionError(
                    "bounded inference outcome unknown: worker ended without receipt",
                    pass_name=pass_name,
                )
            if receipt["kind"] == "not_started":
                entry["external_outcome"] = "not_started"
                raise CategoryGraphExtractionError(
                    "inference budget expired before GE dispatch", pass_name=pass_name,
                )
            if receipt["kind"] == "provider_failure":
                entry["observation"] = _safe_observation_snapshot(receipt["observation"])
                entry["failure_code"] = receipt["failure_code"]
                entry["external_outcome"] = "known_failure"
                if receipt["failure_code"] == "STRUCTURED_OUTPUT_INVALID":
                    entry["consumer_outcome"] = "invalid_structured_output"
                elif receipt["failure_code"] == "ATTEMPT_EVIDENCE_PERSISTENCE_FAILED":
                    entry["consumer_failure"] = "AttemptEvidencePersistenceFailed"
                    self.retention_failed = True
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
                entry["response_component"] = {"kind": "raw_model_response", "sha256": final_attempt["sha256"]}
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
                or observation.get("provider") != self.limits.provider
                or observation.get("requested_model") != self.limits.model
                or observation.get("resolved_model") != self.limits.model
                or (deepseek and observation.get("response_model") != self.limits.model)
            ):
                raise CategoryGraphExtractionError(
                    "inference did not complete within the bounded structured attempt policy",
                    pass_name=pass_name,
                    raw_model_response=result.text,
                )
            entry["external_outcome"] = "completed"
            if not outcome.cleanup_confirmed:
                entry["consumer_failure"] = "CleanupUnconfirmed"
                raise CategoryGraphExtractionError(
                    "bounded inference worker cleanup unconfirmed", pass_name=pass_name,
                )
            if outcome.deadline_exceeded:
                entry["consumer_failure"] = "DeadlineExceeded"
                raise CategoryGraphExtractionError(
                    "inference result arrived after execution deadline", pass_name=pass_name,
                )
        except CategoryGraphExtractionError:
            self._stopped = True
            raise
        except Exception as exc:
            self._stopped = True
            entry["consumer_failure"] = type(exc).__name__
            if isinstance(exc, _WorkerStartFailure):
                entry["external_outcome"] = "not_started"
            else:
                entry.setdefault("external_outcome", "unknown")
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
            if deepseek or source_evidence_packet is not None or advertised_node_schema:
                validate_json_schema(parsed, fmt["schema"])
            if source_evidence_packet is not None:
                from src.graph_memory.extraction.source_sentence_evidence import materialize_node_evidence
                parsed = materialize_node_evidence(
                    source_evidence_packet, parsed,
                    expected_packet_id=context_hashes["node_source_packet"],
                )
                validate_json_schema(parsed, canonical_schema)
                if self.execution_binding is not None:
                    envelope = _private_response_envelope(
                        binding=self.execution_binding,
                        ordinal=len(self.calls), pass_name=pass_name + "-normalized",
                        request=request_payload, context_hashes=context_hashes,
                        raw_observation=observation,
                        response_text=json.dumps({
                            "parsed": parsed,
                            "source_units": [asdict(unit) for unit in source_evidence_packet.units],
                        }, ensure_ascii=False),
                    )
                    sha = self._persist_capture("raw_model_response", envelope)
                    entry["normalized_component"] = {"kind": "raw_model_response", "sha256": sha}
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
