"""DungeonBuddy-owned Agent Turn Trace v1.

Hermes (and later adapters) contribute observations. This module owns identity,
span/model-call vocabulary, usage/cost aggregation, and the baseline log.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from collections.abc import Iterable, Mapping, Sequence
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Iterator, Literal

from src.agent.planner_pricing import usage_cost_usd

SCHEMA = "dmb_agent_turn_trace_v1"
LOGGER = logging.getLogger("dmb.agent.turn_trace")
LOG_EVENT = "dmb_agent_turn_trace"
MODEL_CALLS_TRUNCATED_WARNING = "model_calls_truncated"

UsageStatus = Literal["reported", "partial", "unavailable"]
CostStatus = Literal["estimated", "partial", "reported", "no_provider_fee", "unavailable"]
CallStatus = Literal["ok", "error"]
SpanStatus = Literal["ok", "error", "unavailable"]

_PRIVACY_KEY_DENY = frozenset(
    {
        "request",
        "response",
        "question",
        "prompt",
        "system_prompt",
        "user_message",
        "assistant_response",
        "conversation_history",
        "messages",
        "content",
        "body",
        "args",
        "arguments",
        "result",
        "raw_result",
        "tool_result",
        "assistant_message",
    }
)


def utc_now_z() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def new_trace_id() -> str:
    return f"agent-trace-{uuid.uuid4().hex[:12]}"


def new_span_id() -> str:
    return f"span-{uuid.uuid4().hex[:12]}"


def new_call_id() -> str:
    return f"model-call-{uuid.uuid4().hex[:12]}"


def _nonnegative_ms(value: Any) -> int | float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number < 0:
        return 0
    if number == int(number):
        return int(number)
    return number


def _optional_int(value: Any) -> int | None:
    if value is None or value is False:
        return None
    if isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _unix_to_iso(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        return text or None
    if isinstance(value, (int, float)) and value > 0:
        return datetime.fromtimestamp(float(value), tz=timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%S.%fZ"
        )
    return None


def _duration_ms_from_observer(payload: Mapping[str, Any]) -> int | float | None:
    api_duration = payload.get("api_duration")
    if api_duration is not None:
        try:
            return _nonnegative_ms(float(api_duration) * 1000.0)
        except (TypeError, ValueError):
            pass
    started = payload.get("started_at")
    ended = payload.get("ended_at")
    if isinstance(started, (int, float)) and isinstance(ended, (int, float)):
        return _nonnegative_ms((float(ended) - float(started)) * 1000.0)
    return None


def normalize_model_call_usage(raw: Any) -> dict[str, Any]:
    """Normalize a Hermes observer usage payload into product token fields.

    Hermes CanonicalUsage (as emitted on ``post_api_request``):
    ``input_tokens`` is the uncached bucket; ``prompt_tokens`` is the full
    prompt including cache read/write; ``reasoning_tokens`` is informational
    and is already excluded from ``output_tokens`` / ``total_tokens``.
    """
    if not isinstance(raw, Mapping) or not raw:
        return {"status": "unavailable"}

    cache_read = _optional_int(
        raw.get("cached_input_tokens")
        if raw.get("cached_input_tokens") is not None
        else raw.get("cache_read_tokens", raw.get("cached_tokens"))
    )
    cache_write = _optional_int(
        raw.get("cache_write_input_tokens", raw.get("cache_write_tokens"))
    )
    reasoning = _optional_int(raw.get("reasoning_tokens"))
    output_tokens = _optional_int(raw.get("output_tokens", raw.get("completion_tokens")))

    prompt_tokens = _optional_int(raw.get("prompt_tokens"))
    uncached = _optional_int(raw.get("uncached_input_tokens"))
    raw_input = _optional_int(raw.get("input_tokens"))

    if prompt_tokens is not None:
        input_tokens = prompt_tokens
        if uncached is None and raw_input is not None and cache_read is not None:
            uncached = raw_input
        elif uncached is None and cache_read is not None:
            uncached = max(0, input_tokens - cache_read - (cache_write or 0))
    elif raw_input is not None and (
        cache_read is not None or cache_write is not None or "cache_read_tokens" in raw
    ):
        # Hermes canonical: input_tokens is already uncached.
        uncached = raw_input if uncached is None else uncached
        input_tokens = raw_input + (cache_read or 0) + (cache_write or 0)
    elif raw_input is not None:
        # OpenAI-style: input_tokens includes the cached subset when present.
        input_tokens = raw_input
        if uncached is None and cache_read is not None:
            uncached = max(0, input_tokens - cache_read)
    else:
        return {"status": "unavailable"}

    total = _optional_int(raw.get("total_tokens"))
    if total is None and output_tokens is not None:
        total = input_tokens + output_tokens

    usage: dict[str, Any] = {
        "status": "reported",
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total,
    }
    if cache_read is not None:
        usage["cached_input_tokens"] = cache_read
    if cache_write is not None:
        usage["cache_write_input_tokens"] = cache_write
    if uncached is not None:
        usage["uncached_input_tokens"] = uncached
    if reasoning is not None:
        usage["reasoning_tokens"] = reasoning
    return usage


def estimate_model_call_cost(*, model: str | None, usage: Mapping[str, Any]) -> dict[str, Any]:
    if str(usage.get("status") or "") != "reported":
        return {"status": "unavailable"}
    model_id = (model or "").strip()
    input_tokens = _optional_int(usage.get("input_tokens"))
    output_tokens = _optional_int(usage.get("output_tokens"))
    if not model_id or input_tokens is None or output_tokens is None:
        return {"status": "unavailable"}
    cached = _optional_int(usage.get("cached_input_tokens")) or 0
    priced = usage_cost_usd(
        model_id=model_id,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cached_tokens=cached,
    )
    if not priced.get("pricing_table_matched"):
        return {
            "status": "unavailable",
            "pricing_table_matched": False,
            "rates_per_1m_usd": priced.get("rates_per_1m_usd"),
        }
    return {
        "status": "estimated",
        "usd": float(priced["total_usd"]),
        "currency": "USD",
        "pricing_table_matched": True,
        "rates_per_1m_usd": priced.get("rates_per_1m_usd"),
    }


def map_hermes_observer_to_model_call(
    payload: Mapping[str, Any],
    *,
    status: CallStatus,
    sequence: int,
    call_id: str | None = None,
) -> dict[str, Any]:
    usage_raw = payload.get("usage") if status == "ok" else None
    usage = normalize_model_call_usage(usage_raw)
    requested_model = _optional_str(payload.get("model"))
    response_model = _optional_str(payload.get("response_model"))
    cost = estimate_model_call_cost(
        model=response_model or requested_model,
        usage=usage,
    )
    error = payload.get("error") if isinstance(payload.get("error"), Mapping) else {}
    request_summary = {
        key: payload.get(key)
        for key in (
            "api_call_count",
            "message_count",
            "tool_count",
            "approx_input_tokens",
            "request_char_count",
            "max_tokens",
        )
        if payload.get(key) is not None
    }
    if payload.get("assistant_content_chars") is not None:
        request_summary["assistant_content_chars"] = payload.get("assistant_content_chars")
    if payload.get("assistant_tool_call_count") is not None:
        request_summary["assistant_tool_call_count"] = payload.get(
            "assistant_tool_call_count"
        )
    call: dict[str, Any] = {
        "call_id": call_id or new_call_id(),
        "runtime_api_request_id": _optional_str(payload.get("api_request_id")),
        "runtime_turn_id": _optional_str(payload.get("turn_id")),
        "sequence": sequence,
        "status": status,
        "provider": _optional_str(payload.get("provider")),
        "requested_model": requested_model,
        "response_model": response_model,
        "api_mode": _optional_str(payload.get("api_mode")),
        "started_at": _unix_to_iso(payload.get("started_at")),
        "completed_at": _unix_to_iso(payload.get("ended_at")),
        "duration_ms": _duration_ms_from_observer(payload),
        "request_summary": request_summary,
        "usage": usage,
        "cost": cost,
    }
    finish_reason = _optional_str(payload.get("finish_reason"))
    if finish_reason:
        call["finish_reason"] = finish_reason
    retry_count = _optional_int(payload.get("retry_count"))
    if retry_count is not None:
        call["retry_count"] = retry_count
    if payload.get("retryable") is not None:
        call["retryable"] = bool(payload.get("retryable"))
    status_code = _optional_int(payload.get("status_code"))
    if status_code is not None:
        call["status_code"] = status_code
    error_type = _optional_str(error.get("type") if error else payload.get("error_type"))
    if error_type:
        call["error_type"] = error_type
    return call


def aggregate_usage(
    model_calls: Sequence[Mapping[str, Any]],
    *,
    truncated: bool = False,
    observed_model_call_count: int | None = None,
) -> dict[str, Any]:
    call_count = len(model_calls)
    reported = [
        call
        for call in model_calls
        if isinstance(call.get("usage"), Mapping)
        and call["usage"].get("status") == "reported"
    ]
    if call_count == 0:
        usage: dict[str, Any] = {
            "available": False,
            "status": "unavailable",
            "input_tokens": None,
            "output_tokens": None,
            "total_tokens": None,
            "model_call_count": 0,
            "usage_reported_call_count": 0,
        }
        return _with_observed_model_call_count(
            usage,
            truncated=truncated,
            retained_count=0,
            observed_model_call_count=observed_model_call_count,
        )
    if not reported:
        usage = {
            "available": False,
            "status": "unavailable",
            "input_tokens": None,
            "output_tokens": None,
            "total_tokens": None,
            "model_call_count": call_count,
            "usage_reported_call_count": 0,
        }
        return _with_observed_model_call_count(
            usage,
            truncated=truncated,
            retained_count=call_count,
            observed_model_call_count=observed_model_call_count,
        )

    def _sum(field: str) -> int:
        return sum(int(call["usage"].get(field) or 0) for call in reported)

    complete = len(reported) == call_count and not truncated
    usage = {
        "available": True,
        "status": "reported" if complete else "partial",
        "input_tokens": _sum("input_tokens"),
        "output_tokens": _sum("output_tokens"),
        "total_tokens": _sum("total_tokens"),
        "cached_input_tokens": _sum("cached_input_tokens"),
        "cache_write_input_tokens": _sum("cache_write_input_tokens"),
        "uncached_input_tokens": _sum("uncached_input_tokens"),
        "reasoning_tokens": _sum("reasoning_tokens"),
        "model_call_count": call_count,
        "usage_reported_call_count": len(reported),
    }
    return _with_observed_model_call_count(
        usage,
        truncated=truncated,
        retained_count=call_count,
        observed_model_call_count=observed_model_call_count,
    )


def aggregate_cost(
    model_calls: Sequence[Mapping[str, Any]],
    *,
    truncated: bool = False,
) -> dict[str, Any]:
    if not model_calls:
        return {
            "status": "unavailable",
            "usd": None,
            "priced_call_count": 0,
            "unpriced_call_count": 0,
        }
    priced: list[Mapping[str, Any]] = []
    unpriced = 0
    for call in model_calls:
        cost = call.get("cost") if isinstance(call.get("cost"), Mapping) else {}
        if cost.get("status") == "estimated" and cost.get("usd") is not None:
            priced.append(cost)
        else:
            unpriced += 1
    if not priced:
        return {
            "status": "unavailable",
            "usd": None,
            "priced_call_count": 0,
            "unpriced_call_count": unpriced,
        }
    total = sum(float(item["usd"]) for item in priced)
    status: CostStatus = "estimated" if unpriced == 0 and not truncated else "partial"
    result: dict[str, Any] = {
        "status": status,
        "usd": total,
        "currency": "USD",
        "priced_call_count": len(priced),
        "unpriced_call_count": unpriced,
    }
    rates = priced[0].get("rates_per_1m_usd") if len(priced) == 1 else None
    if isinstance(rates, Mapping):
        result["rates_per_1m_usd"] = dict(rates)
    return result


def _with_observed_model_call_count(
    usage: dict[str, Any],
    *,
    truncated: bool,
    retained_count: int,
    observed_model_call_count: int | None,
) -> dict[str, Any]:
    if observed_model_call_count is None:
        return usage
    observed = max(0, int(observed_model_call_count))
    if truncated:
        observed = max(observed, retained_count)
    if observed <= retained_count:
        return usage
    usage["observed_model_call_count"] = observed
    return usage


def unambiguous_identity(model_calls: Sequence[Mapping[str, Any]]) -> tuple[str | None, str | None]:
    providers = {
        str(call.get("provider"))
        for call in model_calls
        if _optional_str(call.get("provider"))
    }
    models = {
        str(call.get("response_model") or call.get("requested_model"))
        for call in model_calls
        if _optional_str(call.get("response_model") or call.get("requested_model"))
    }
    provider = next(iter(providers)) if len(providers) == 1 else None
    model = next(iter(models)) if len(models) == 1 else None
    return provider, model


def strip_privacy_fields(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): strip_privacy_fields(item)
            for key, item in value.items()
            if str(key) not in _PRIVACY_KEY_DENY
        }
    if isinstance(value, list):
        return [strip_privacy_fields(item) for item in value]
    return value


def trace_json_bytes(trace: Mapping[str, Any]) -> str:
    safe = strip_privacy_fields(dict(trace))
    return json.dumps(safe, sort_keys=True, default=str, ensure_ascii=False)


def emit_baseline_trace_log(trace: Mapping[str, Any]) -> None:
    LOGGER.info("%s %s", LOG_EVENT, trace_json_bytes(trace))


class AgentTurnTraceBuilder:
    """Accumulate one DungeonBuddy-owned turn trace."""

    def __init__(
        self,
        *,
        agent_thread_id: str | None,
        turn_id: str | None,
        runtime: str,
        backend: str,
        mode: str,
        trace_id: str | None = None,
    ) -> None:
        self.trace_id = trace_id or new_trace_id()
        self.agent_thread_id = agent_thread_id
        self.turn_id = turn_id
        self.runtime = runtime
        self.backend = backend
        self.mode = mode
        self.started_at = utc_now_z()
        self._started_mono = time.monotonic()
        self.spans: list[dict[str, Any]] = []
        self.warnings: list[str] = []
        self.logged = False
        self.context_summary: dict[str, Any] = {}
        self._open_phases: dict[str, dict[str, Any]] = {}

    def elapsed_ms(self) -> int:
        return max(0, int((time.monotonic() - self._started_mono) * 1000))

    def add_warning(self, warning: str) -> None:
        text = str(warning or "").strip()
        if text and text not in self.warnings:
            self.warnings.append(text)

    def start_phase(
        self,
        name: str,
        *,
        kind: str = "phase",
        parent_span_id: str | None = None,
        attributes: Mapping[str, Any] | None = None,
    ) -> str:
        span_id = new_span_id()
        self._open_phases[span_id] = {
            "name": name,
            "kind": kind,
            "parent_span_id": parent_span_id,
            "attributes": dict(attributes or {}),
            "started_at": utc_now_z(),
            "started_mono": time.monotonic(),
        }
        return span_id

    def complete_phase(
        self,
        span_id: str,
        *,
        status: SpanStatus = "ok",
        attributes: Mapping[str, Any] | None = None,
    ) -> None:
        open_span = self._open_phases.pop(span_id, None)
        if open_span is None:
            return
        merged_attributes = dict(open_span["attributes"])
        if attributes:
            merged_attributes.update(dict(attributes))
        self.spans.append(
            {
                "span_id": span_id,
                "parent_span_id": open_span["parent_span_id"],
                "kind": open_span["kind"],
                "name": open_span["name"],
                "status": status,
                "started_at": open_span["started_at"],
                "completed_at": utc_now_z(),
                "duration_ms": max(
                    0, int((time.monotonic() - open_span["started_mono"]) * 1000)
                ),
                "attributes": merged_attributes,
            }
        )

    @contextmanager
    def phase(
        self,
        name: str,
        *,
        kind: str = "phase",
        parent_span_id: str | None = None,
        status: SpanStatus | None = None,
        attributes: Mapping[str, Any] | None = None,
    ) -> Iterator[str]:
        span_id = self.start_phase(
            name,
            kind=kind,
            parent_span_id=parent_span_id,
            attributes=attributes,
        )
        observed_status: SpanStatus = "ok"
        try:
            yield span_id
        except Exception:
            observed_status = "error"
            raise
        finally:
            self.complete_phase(span_id, status=status or observed_status)

    def add_unavailable_phase(
        self,
        name: str,
        *,
        kind: str = "phase",
        attributes: Mapping[str, Any] | None = None,
    ) -> None:
        self.spans.append(
            {
                "span_id": new_span_id(),
                "parent_span_id": None,
                "kind": kind,
                "name": name,
                "status": "unavailable",
                "started_at": utc_now_z(),
                "completed_at": utc_now_z(),
                "duration_ms": None,
                "attributes": dict(attributes or {}),
            }
        )

    def finalize(
        self,
        *,
        status: str,
        model_calls: Sequence[Mapping[str, Any]] | None = None,
        extra_warnings: Iterable[str] = (),
        hermes_fields: Mapping[str, Any] | None = None,
        completed_at: str | None = None,
        elapsed_ms: int | None = None,
        observed_model_call_count: int | None = None,
    ) -> dict[str, Any]:
        leftover_status: SpanStatus = "error" if status == "error" else "ok"
        for span_id in list(self._open_phases):
            self.complete_phase(span_id, status=leftover_status)
        calls = [dict(call) for call in (model_calls or [])]
        for warning in extra_warnings:
            self.add_warning(warning)
        truncated = MODEL_CALLS_TRUNCATED_WARNING in self.warnings
        usage = aggregate_usage(
            calls,
            truncated=truncated,
            observed_model_call_count=observed_model_call_count,
        )
        cost = aggregate_cost(calls, truncated=truncated)
        provider, model = unambiguous_identity(calls)
        finished = completed_at or utc_now_z()
        measured = self.elapsed_ms() if elapsed_ms is None else max(0, int(elapsed_ms))
        trace: dict[str, Any] = {
            "schema": SCHEMA,
            "trace_id": self.trace_id,
            "agent_thread_id": self.agent_thread_id,
            "turn_id": self.turn_id,
            "runtime": self.runtime,
            "backend": self.backend,
            "mode": self.mode,
            "status": status,
            "started_at": self.started_at,
            "completed_at": finished,
            "elapsed_ms": measured,
            "usage": usage,
            "cost": cost,
            "model_calls": calls,
            "spans": list(self.spans),
            "steps": [],
            "context_summary": dict(self.context_summary),
            "artifact_refs": [],
            "warnings": list(self.warnings),
        }
        if provider:
            trace["provider"] = provider
        if model:
            trace["model"] = model
        if hermes_fields:
            for key, value in hermes_fields.items():
                if value is not None or key in {
                    "tool_events",
                    "hermes_session_id",
                    "process_isolation",
                    "conversation_context",
                }:
                    trace[key] = value
        return trace

    def finalize_and_log(self, **kwargs: Any) -> dict[str, Any]:
        trace = self.finalize(**kwargs)
        if not self.logged:
            emit_baseline_trace_log(trace)
            self.logged = True
        return trace
