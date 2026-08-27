"""Owning tests for DungeonBuddy Agent Turn Trace v1 normalization and logging."""

from __future__ import annotations

import json
import logging
from typing import Any

from apps.live_control_server.services.agent_turn_trace import (
    SCHEMA,
    AgentTurnTraceBuilder,
    aggregate_cost,
    aggregate_usage,
    emit_baseline_trace_log,
    estimate_model_call_cost,
    map_hermes_observer_to_model_call,
    normalize_model_call_usage,
    trace_json_bytes,
)

PRIVACY_SENTINEL = "TRACE-PRIVACY-SENTINEL-QUESTION-BODY-9f3c"


def _hermes_usage(
    *,
    uncached: int = 100,
    cache_read: int = 0,
    cache_write: int = 0,
    output: int = 20,
    reasoning: int = 0,
) -> dict[str, Any]:
    prompt = uncached + cache_read + cache_write
    return {
        "input_tokens": uncached,
        "output_tokens": output,
        "cache_read_tokens": cache_read,
        "cache_write_tokens": cache_write,
        "reasoning_tokens": reasoning,
        "request_count": 1,
        "prompt_tokens": prompt,
        "total_tokens": prompt + output,
    }


def _observer_payload(
    *,
    api_request_id: str,
    turn_id: str = "hermes-turn-1",
    status: str = "ok",
    usage: dict[str, Any] | None = None,
    model: str = "gpt-5.4-mini",
    response_model: str | None = "gpt-5.4-mini",
    api_duration: float = 0.250,
    retry_count: int | None = None,
    retryable: bool | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "telemetry_schema_version": "hermes.observer.v1",
        "session_id": "hermes-session-1",
        "task_id": "hermes-task-1",
        "turn_id": turn_id,
        "api_request_id": api_request_id,
        "platform": "cli",
        "model": model,
        "provider": "openai-api",
        "base_url": "https://api.openai.com/v1",
        "api_mode": "chat_completions",
        "api_call_count": 1,
        "message_count": 4,
        "tool_count": 2,
        "approx_input_tokens": 2048,
        "request_char_count": 8192,
        "max_tokens": 4096,
        "started_at": 1_700_000_000.0,
        "ended_at": 1_700_000_000.250,
        "api_duration": api_duration,
        "request": {"method": "POST", "body": {"messages": [PRIVACY_SENTINEL]}},
        "response": {"assistant_message": {"content": PRIVACY_SENTINEL}},
    }
    if status == "ok":
        payload["finish_reason"] = "stop"
        payload["response_model"] = response_model
        payload["usage"] = usage if usage is not None else _hermes_usage()
        payload["assistant_content_chars"] = 120
        payload["assistant_tool_call_count"] = 1
    else:
        payload["status_code"] = 429
        payload["retry_count"] = 0 if retry_count is None else retry_count
        payload["max_retries"] = 3
        payload["retryable"] = True if retryable is None else retryable
        payload["reason"] = "rate_limit"
        payload["error"] = {"type": "RateLimitError", "message": PRIVACY_SENTINEL}
    if extra:
        payload.update(extra)
    return payload


def test_one_successful_model_call_normalizes_hermes_usage_and_cost() -> None:
    call = map_hermes_observer_to_model_call(
        _observer_payload(api_request_id="api-req-1"),
        status="ok",
        sequence=1,
        call_id="model-call-1",
    )
    assert call["runtime_api_request_id"] == "api-req-1"
    assert call["runtime_turn_id"] == "hermes-turn-1"
    assert call["status"] == "ok"
    assert call["provider"] == "openai-api"
    assert call["requested_model"] == "gpt-5.4-mini"
    assert call["duration_ms"] == 250
    assert call["usage"]["status"] == "reported"
    assert call["usage"]["input_tokens"] == 100
    assert call["usage"]["output_tokens"] == 20
    assert call["usage"]["total_tokens"] == 120
    assert call["cost"]["status"] == "estimated"
    assert call["cost"]["usd"] > 0
    assert call["cost"]["pricing_table_matched"] is True
    assert "request" not in call
    assert "response" not in call


def test_multiple_successful_model_calls_aggregate_exactly() -> None:
    first = map_hermes_observer_to_model_call(
        _observer_payload(api_request_id="api-req-1", usage=_hermes_usage(uncached=80, output=10)),
        status="ok",
        sequence=1,
    )
    second = map_hermes_observer_to_model_call(
        _observer_payload(
            api_request_id="api-req-2",
            usage=_hermes_usage(uncached=40, output=5),
            extra={"api_call_count": 2},
        ),
        status="ok",
        sequence=2,
    )
    usage = aggregate_usage([first, second])
    assert usage["status"] == "reported"
    assert usage["available"] is True
    assert usage["input_tokens"] == 120
    assert usage["output_tokens"] == 15
    assert usage["total_tokens"] == 135
    assert usage["model_call_count"] == 2
    assert usage["usage_reported_call_count"] == 2
    cost = aggregate_cost([first, second])
    assert cost["status"] == "estimated"
    assert cost["usd"] == first["cost"]["usd"] + second["cost"]["usd"]


def test_cached_input_accounting_and_openai_estimate() -> None:
    usage = normalize_model_call_usage(
        _hermes_usage(uncached=2000, cache_read=8000, output=500)
    )
    assert usage["input_tokens"] == 10_000
    assert usage["cached_input_tokens"] == 8000
    assert usage["uncached_input_tokens"] == 2000
    assert usage["total_tokens"] == 10_500
    cost = estimate_model_call_cost(model="gpt-5.3-chat-latest", usage=usage)
    assert cost["status"] == "estimated"
    expected = (2000 / 1e6) * 1.75 + (8000 / 1e6) * 0.175 + (500 / 1e6) * 14.00
    assert abs(cost["usd"] - expected) < 1e-12
    assert cost["rates_per_1m_usd"]["cached_input"] == 0.175


def test_reasoning_tokens_are_not_added_to_output_or_total() -> None:
    usage = normalize_model_call_usage(
        _hermes_usage(uncached=100, output=50, reasoning=400)
    )
    assert usage["output_tokens"] == 50
    assert usage["reasoning_tokens"] == 400
    assert usage["total_tokens"] == 150
    assert usage["total_tokens"] != 50 + 400
    assert usage["total_tokens"] != 150 + 400


def test_failed_attempt_with_no_usage_is_unavailable_not_zero() -> None:
    call = map_hermes_observer_to_model_call(
        _observer_payload(api_request_id="api-req-err", status="error"),
        status="error",
        sequence=1,
    )
    assert call["status"] == "error"
    assert call["usage"]["status"] == "unavailable"
    assert call["cost"]["status"] == "unavailable"
    assert "usd" not in call["cost"] or call["cost"].get("usd") is None
    assert call["retryable"] is True
    assert call["error_type"] == "RateLimitError"


def test_failed_attempt_followed_by_successful_retry_stays_two_calls() -> None:
    error = map_hermes_observer_to_model_call(
        _observer_payload(api_request_id="api-req-a", status="error", retryable=True),
        status="error",
        sequence=1,
    )
    success = map_hermes_observer_to_model_call(
        _observer_payload(
            api_request_id="api-req-b",
            extra={"api_call_count": 2, "retry_count": 1},
        ),
        status="ok",
        sequence=2,
    )
    usage = aggregate_usage([error, success])
    cost = aggregate_cost([error, success])
    assert usage["status"] == "partial"
    assert usage["model_call_count"] == 2
    assert usage["usage_reported_call_count"] == 1
    assert usage["input_tokens"] == success["usage"]["input_tokens"]
    assert cost["status"] == "partial"
    assert cost["priced_call_count"] == 1
    assert cost["unpriced_call_count"] == 1
    assert cost["usd"] == success["cost"]["usd"]


def test_unknown_pricing_is_unavailable_not_zero() -> None:
    call = map_hermes_observer_to_model_call(
        _observer_payload(
            api_request_id="api-req-unknown",
            model="unknown-model-xyz",
            response_model="unknown-model-xyz",
        ),
        status="ok",
        sequence=1,
    )
    assert call["usage"]["status"] == "reported"
    assert call["usage"]["input_tokens"] == 100
    assert call["cost"]["status"] == "unavailable"
    assert call["cost"].get("usd") is None
    aggregate = aggregate_cost([call])
    assert aggregate["status"] == "unavailable"
    assert aggregate["usd"] is None


def test_zero_model_call_turn_is_unavailable_not_measured_zero() -> None:
    usage = aggregate_usage([])
    cost = aggregate_cost([])
    assert usage["available"] is False
    assert usage["status"] == "unavailable"
    assert usage["model_call_count"] == 0
    assert usage["input_tokens"] is None
    assert cost["status"] == "unavailable"
    assert cost["usd"] is None


def test_partial_aggregate_usage_and_cost() -> None:
    reported = map_hermes_observer_to_model_call(
        _observer_payload(api_request_id="api-ok"),
        status="ok",
        sequence=1,
    )
    missing = {
        "call_id": "model-call-missing",
        "runtime_api_request_id": "api-missing",
        "sequence": 2,
        "status": "ok",
        "usage": {"status": "unavailable"},
        "cost": {"status": "unavailable"},
    }
    usage = aggregate_usage([reported, missing])
    cost = aggregate_cost([reported, missing])
    assert usage["status"] == "partial"
    assert usage["available"] is True
    assert cost["status"] == "partial"


def test_span_ordering_and_nonnegative_duration() -> None:
    builder = AgentTurnTraceBuilder(
        agent_thread_id="agent-thread-1",
        turn_id="agent-turn-1",
        runtime="process_isolated",
        backend="hermes",
        mode="hermes_graph_agent",
        trace_id="agent-trace-fixed",
    )
    with builder.phase("session_load"):
        pass
    with builder.phase("harness_turn"):
        pass
    names = [span["name"] for span in builder.spans]
    assert names == ["session_load", "harness_turn"]
    for span in builder.spans:
        assert span["duration_ms"] is not None
        assert span["duration_ms"] >= 0


def test_json_serialization_is_safe_and_includes_schema() -> None:
    builder = AgentTurnTraceBuilder(
        agent_thread_id="agent-thread-1",
        turn_id="agent-turn-1",
        runtime="process_isolated",
        backend="hermes",
        mode="hermes_graph_agent",
        trace_id="agent-trace-json",
    )
    call = map_hermes_observer_to_model_call(
        _observer_payload(api_request_id="api-req-1"),
        status="ok",
        sequence=1,
    )
    with builder.phase("harness_turn"):
        pass
    trace = builder.finalize(status="ok", model_calls=[call])
    payload = json.loads(trace_json_bytes(trace))
    assert payload["schema"] == SCHEMA
    assert payload["trace_id"] == "agent-trace-json"
    assert payload["usage"]["input_tokens"] == 100
    json.dumps(payload)


def test_baseline_log_privacy_excludes_sentinel(caplog) -> None:
    builder = AgentTurnTraceBuilder(
        agent_thread_id="agent-thread-secret",
        turn_id="agent-turn-secret",
        runtime="process_isolated",
        backend="hermes",
        mode="hermes_graph_agent",
        trace_id="agent-trace-secret",
    )
    call = map_hermes_observer_to_model_call(
        _observer_payload(api_request_id="api-req-secret"),
        status="ok",
        sequence=1,
    )
    trace = builder.finalize(
        status="ok",
        model_calls=[call],
        hermes_fields={"conversation_context": {"message_count": 2, "history_present": True}},
    )
    with caplog.at_level(logging.INFO, logger="dmb.agent.turn_trace"):
        emit_baseline_trace_log(trace)
    blob = " ".join(record.getMessage() for record in caplog.records)
    assert "dmb_agent_turn_trace" in blob
    assert "agent-trace-secret" in blob
    assert PRIVACY_SENTINEL not in blob
    assert "request" not in json.loads(trace_json_bytes(trace)).get("model_calls", [{}])[0]
