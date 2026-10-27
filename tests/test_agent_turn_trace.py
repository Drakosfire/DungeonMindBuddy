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


def test_complete_phase_merges_completion_attributes() -> None:
    builder = AgentTurnTraceBuilder(
        agent_thread_id="agent-thread-1",
        turn_id="agent-turn-1",
        runtime="process_isolated",
        backend="hermes",
        mode="hermes_graph_agent",
        trace_id="agent-trace-attrs",
    )
    span_id = builder.start_phase(
        "context_assembly",
        attributes={"start_only": "keep", "overlap": "start"},
    )
    builder.complete_phase(
        span_id,
        attributes={"overlap": "complete", "complete_only": 3},
    )
    span = builder.spans[0]
    assert span["name"] == "context_assembly"
    assert span["status"] == "ok"
    assert span["duration_ms"] is not None
    assert span["duration_ms"] >= 0
    assert span["attributes"] == {
        "start_only": "keep",
        "overlap": "complete",
        "complete_only": 3,
    }
    # Callers without completion attributes remain unchanged.
    with builder.phase("harness_turn", attributes={"phase_attr": True}):
        pass
    assert builder.spans[1]["attributes"] == {"phase_attr": True}


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


def test_truncated_complete_calls_mark_usage_and_cost_partial() -> None:
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
    usage = aggregate_usage(
        [first, second],
        truncated=True,
        observed_model_call_count=65,
    )
    cost = aggregate_cost([first, second], truncated=True)
    assert usage["status"] == "partial"
    assert usage["available"] is True
    assert usage["input_tokens"] == 120
    assert usage["output_tokens"] == 15
    assert usage["model_call_count"] == 2
    assert usage["observed_model_call_count"] == 65
    assert cost["status"] == "partial"
    assert cost["usd"] == first["cost"]["usd"] + second["cost"]["usd"]
    assert cost["priced_call_count"] == 2
    assert cost["unpriced_call_count"] == 0

    complete_usage = aggregate_usage([first, second])
    complete_cost = aggregate_cost([first, second])
    assert complete_usage["status"] == "reported"
    assert complete_cost["status"] == "estimated"
    assert "observed_model_call_count" not in complete_usage

    builder = AgentTurnTraceBuilder(
        agent_thread_id="agent-thread-truncated",
        turn_id="agent-turn-truncated",
        runtime="process_isolated",
        backend="hermes",
        mode="hermes_graph_agent",
        trace_id="agent-trace-truncated",
    )
    trace = builder.finalize(
        status="ok",
        model_calls=[first, second],
        extra_warnings=["model_calls_truncated"],
        observed_model_call_count=65,
    )
    assert "model_calls_truncated" in trace["warnings"]
    assert trace["usage"]["status"] == "partial"
    assert trace["cost"]["status"] == "partial"
    assert trace["usage"]["observed_model_call_count"] == 65
    assert trace["usage"]["model_call_count"] == 2


def test_retained_trace_allowlist_size_and_unknown_accounting():
    from apps.live_control_server.services.agent_turn_trace import MAX_LOG_BYTES, retained_trace_payload
    trace = AgentTurnTraceBuilder(agent_thread_id='thread', turn_id='client', runtime='test', backend='test', mode='test').finalize(status='error')
    trace['unexpected'] = {'secret': PRIVACY_SENTINEL}
    trace['spans'] = [{'name': 'work', 'duration_ms': 12, 'attributes': {'unexpected': PRIVACY_SENTINEL, 'count': 2}}] * 1000
    trace['context_summary'] = {'unexpected': PRIVACY_SENTINEL, 'count': 3}
    saved = retained_trace_payload(trace)
    blob = 'dmb_agent_turn_trace ' + trace_json_bytes(saved)
    assert PRIVACY_SENTINEL not in blob
    assert len(blob.encode('utf-8')) <= MAX_LOG_BYTES
    assert saved['retention']['complete'] is False
    assert saved['retention']['original_spans'] == 1000
    assert saved['usage']['model_call_count'] is None
    assert saved['retention']['provider_accounting'] == 'unknown'
    assert saved['spans'][0]['attributes'] == {'count': 2}


def test_failed_log_attempt_does_not_change_response_or_repeat(monkeypatch):
    import apps.live_control_server.services.agent_turn_trace as module
    calls = []
    def fail(trace):
        calls.append(trace)
        raise OSError('private sink unavailable')
    monkeypatch.setattr(module, 'emit_baseline_trace_log', fail)
    builder = AgentTurnTraceBuilder(agent_thread_id=None, turn_id='client', runtime='test', backend='test', mode='test')
    assert builder.finalize_and_log(status='error')['status'] == 'error'
    assert builder.finalize_and_log(status='error')['status'] == 'error'
    assert builder.logged and len(calls) == 1


def test_uvicorn_launch_enables_only_trace_logger_and_is_idempotent(monkeypatch):
    import io
    from logging.config import dictConfig
    from uvicorn.config import LOGGING_CONFIG
    from apps.live_control_server.services.agent_turn_trace import LOGGER, configure_turn_trace_logging
    # Restore process logging after reproducing the real launch configuration.
    handlers, level, propagate, disabled = list(LOGGER.handlers), LOGGER.level, LOGGER.propagate, LOGGER.disabled
    stream = io.StringIO()
    try:
        dictConfig(LOGGING_CONFIG)
        monkeypatch.setattr('sys.stdout', stream)
        configure_turn_trace_logging()
        configure_turn_trace_logging()
        import asyncio
        from types import SimpleNamespace
        from apps.live_control_server import main
        monkeypatch.setattr("apps.live_control_server.services.build_jev_runtime.prepare_default_build_runtime", lambda: None)
        monkeypatch.setattr(main, "get_hermes_graph_agent_host", lambda: None)
        monkeypatch.setattr(main, "shutdown_hermes_graph_agent_host", lambda: None)
        async def startup():
            async with main.lifespan(SimpleNamespace(state=SimpleNamespace())):
                pass
        asyncio.run(startup())
        assert sum(bool(getattr(h, 'dmb_turn_trace', False)) for h in LOGGER.handlers) == 1
        builder = AgentTurnTraceBuilder(agent_thread_id=None, turn_id='client', runtime='test', backend='test', mode='test')
        builder.finalize_and_log(status='ok', observed_model_call_count=0)
        builder.finalize_and_log(status='ok', observed_model_call_count=0)
        lines = stream.getvalue().splitlines()
        assert len(lines) == 1
        assert json.loads(lines[0].removeprefix('dmb_agent_turn_trace '))['turn_id'] == 'client'
        assert LOGGER.propagate is False
    finally:
        for handler in list(LOGGER.handlers):
            if handler not in handlers:
                handler.close()
        LOGGER.handlers = handlers
        LOGGER.setLevel(level)
        LOGGER.propagate = propagate
        LOGGER.disabled = disabled


def test_durable_binding_is_log_only_and_preserves_client_identity(monkeypatch):
    from types import SimpleNamespace
    from uuid import uuid4
    import apps.live_control_server.services.agent_turn_trace as module
    emitted = []
    monkeypatch.setattr(module, 'emit_baseline_trace_log', lambda trace: emitted.append(trace))
    turn = SimpleNamespace(turn_id=uuid4(), conversation_id=uuid4(), attempt=2)
    builder = AgentTurnTraceBuilder(agent_thread_id=None, turn_id='client', runtime='test', backend='test', mode='test')
    builder.bind_durable_turn(turn)
    response = builder.finalize_and_log(status='ok')
    assert response['turn_id'] == 'client'
    assert 'correlation' not in response
    assert emitted[0]['correlation'] == {'durable_turn_id': str(turn.turn_id), 'conversation_id': str(turn.conversation_id), 'attempt': 2}


def test_emitted_line_drops_unknown_metric_names_and_values(caplog):
    builder = AgentTurnTraceBuilder(agent_thread_id="thread", turn_id="client", runtime="test", backend="test", mode="test")
    trace = builder.finalize(status="ok", model_calls=[map_hermes_observer_to_model_call(
        _observer_payload(api_request_id="request-1"), status="ok", sequence=1)])
    trace["spans"] = [{"name": "read", "duration_ms": 17, "attributes": {"count": 3}}]
    trace["context_summary"] = {"history_message_count": 4}
    bags = [trace["usage"], trace["cost"], trace["context_summary"], trace["spans"][0]["attributes"],
            trace["model_calls"][0]["usage"], trace["model_calls"][0]["cost"], trace["model_calls"][0]["request_summary"]]
    for bag in bags:
        bag["PRIVATE_PROMPT_SENTINEL_123"] = 1
        bag["PRIVATE_CREDENTIAL_SENTINEL_456"] = True
        bag["PRIVATE_NULL_SENTINEL_789"] = None
        bag["unexpected"] = PRIVACY_SENTINEL
    with caplog.at_level(logging.INFO, logger="dmb.agent.turn_trace"):
        emit_baseline_trace_log(trace)
    line = next(r.getMessage() for r in caplog.records if r.name == "dmb.agent.turn_trace")
    assert "SENTINEL" not in line
    saved = json.loads(line.removeprefix("dmb_agent_turn_trace "))
    assert saved["usage"]["input_tokens"] == 100
    assert saved["usage"]["cached_input_tokens"] == 0
    assert saved["context_summary"] == {"history_message_count": 4}
    assert saved["spans"][0]["duration_ms"] == 17
    assert saved["spans"][0]["attributes"] == {"count": 3}
    assert saved["model_calls"][0]["request_summary"]["message_count"] == 4
    assert saved["retention"]["scope"] == "allowlisted_metadata"



def test_unknown_optional_buckets_do_not_become_zero():
    from apps.live_control_server.services.agent_turn_trace import retained_trace_payload

    # Synthetic 11-controller + 1-writer fixture with the observed totals;
    # it contains no source text or copied private request payloads.
    calls = [{"usage": {"status": "reported", "input_tokens": input_count,
        "output_tokens": output_count, "total_tokens": input_count + output_count,
        "cached_input_tokens": None}} for input_count, output_count in
        zip([8000] * 10 + [10241], [900] * 10 + [1441])]
    calls.append({"usage": {"status": "reported", "input_tokens": 11766,
        "output_tokens": 532, "total_tokens": 12298, "cached_input_tokens": 0,
        "reasoning_tokens": 173}})
    usage = aggregate_usage(calls)
    assert usage["status"] == "reported"
    assert (usage["input_tokens"], usage["output_tokens"], usage["total_tokens"]) == (102007, 10973, 112980)
    for field in ("cached_input_tokens", "cache_write_input_tokens", "uncached_input_tokens", "reasoning_tokens"):
        assert usage[field] is None
    trace = retained_trace_payload({"schema": SCHEMA, "usage": usage, "model_calls": calls})
    assert trace["usage"]["cached_input_tokens"] is None
    assert trace["usage"]["reasoning_tokens"] is None
    assert calls[-1]["usage"]["reasoning_tokens"] == 173
    assert usage["model_call_count"] == 12


def test_optional_buckets_sum_independently_and_preserve_explicit_zero():
    calls = [{"usage": {"status": "reported", "input_tokens": 10, "output_tokens": 2,
        "total_tokens": 12, "cached_input_tokens": 0, "reasoning_tokens": 1}},
        {"usage": {"status": "reported", "input_tokens": 20, "output_tokens": 3,
        "total_tokens": 23, "cached_input_tokens": 0, "reasoning_tokens": 4}}]
    usage = aggregate_usage(calls)
    assert usage["cached_input_tokens"] == 0
    assert usage["reasoning_tokens"] == 5
    assert usage["cache_write_input_tokens"] is None
    assert usage["total_tokens"] == 35  # reasoning is informational
    partial = aggregate_usage([*calls, {"usage": {"status": "unavailable"}}])
    assert partial["status"] == "partial"
    assert partial["cached_input_tokens"] == 0  # reported retained subset only
    assert partial["usage_reported_call_count"] == 2
    assert partial["model_call_count"] == 3
    truncated = aggregate_usage(calls, truncated=True, observed_model_call_count=65)
    assert truncated["status"] == "partial"
    assert truncated["observed_model_call_count"] == 65
    assert truncated["model_call_count"] == 2
    assert truncated["cached_input_tokens"] == 0


def test_invalid_aggregate_counts_are_unknown_and_never_crash():
    for value in (None, True, False, -1, 1.2, float("nan"), float("inf"), "3", "garbage"):
        usage = aggregate_usage([{"usage": {"status": "reported", "input_tokens": 10,
            "output_tokens": value, "total_tokens": 12, "cached_input_tokens": value}}])
        assert usage["output_tokens"] is None
        assert usage["cached_input_tokens"] is None
        assert usage["input_tokens"] == 10
        assert usage["status"] == "partial"
    assert aggregate_usage([])["status"] == "unavailable"
    assert (
        aggregate_usage([{"usage": {"status": "unavailable"}}])["input_tokens"] is None
    )


def test_captured_error_accounting_is_immutable_private_and_explicitly_overridable():
    from apps.live_control_server.services.agent_turn_trace import (
        retained_trace_payload,
    )

    known = map_hermes_observer_to_model_call(
        _observer_payload(api_request_id="prior"), status="ok", sequence=1
    )
    unknown = map_hermes_observer_to_model_call(
        _observer_payload(api_request_id="tail", usage={}), status="error", sequence=2
    )
    unknown["usage"] = {"status": "unavailable"}
    unknown["cost"] = {"status": "unavailable", "usd": None}
    known["headers"] = {"authorization": PRIVACY_SENTINEL}
    builder = AgentTurnTraceBuilder(
        agent_thread_id=None,
        turn_id="client",
        runtime="test",
        backend="test",
        mode="test",
    )
    builder.capture_accounting(
        model_calls=[known, unknown],
        extra_warnings=["observed_warning", PRIVACY_SENTINEL + " private prompt"],
        observed_model_call_count=2,
    )
    known["usage"]["input_tokens"] = 999999
    assert PRIVACY_SENTINEL not in repr(builder._captured_accounting)
    trace = retained_trace_payload(builder.finalize(status="error"))
    assert len(trace["model_calls"]) == 2
    assert trace["usage"]["input_tokens"] == 100
    assert trace["usage"]["status"] == "partial"
    assert trace["cost"]["status"] == "partial"
    builder = AgentTurnTraceBuilder(
        agent_thread_id=None,
        turn_id="client",
        runtime="test",
        backend="test",
        mode="test",
    )
    builder.capture_accounting(
        model_calls=[unknown],
        extra_warnings=["observed_warning"],
        observed_model_call_count=1,
    )
    empty = builder.finalize(status="ok", model_calls=[], observed_model_call_count=0)
    assert empty["model_calls"] == []
    assert empty["usage"]["model_call_count"] == 0
    assert "observed_warning" not in empty["warnings"]


def test_captured_accounting_retains_count_when_details_are_capped():
    known = map_hermes_observer_to_model_call(
        _observer_payload(api_request_id="synthetic"), status="ok", sequence=1
    )
    builder = AgentTurnTraceBuilder(
        agent_thread_id=None, turn_id="client", runtime="test", backend="test", mode="test"
    )
    builder.capture_accounting(model_calls=[known] * 500, observed_model_call_count=500)
    saved = builder.finalize(status="error")
    assert len(saved["model_calls"]) < 500
    assert saved["usage"]["model_call_count"] == len(saved["model_calls"])
    assert saved["usage"]["observed_model_call_count"] == 500
    assert saved["usage"]["status"] == "partial"
    assert saved["cost"]["status"] == "partial"
    assert "model_calls_truncated" in saved["warnings"]


def test_known_unpriced_cache_writes_are_retained_without_a_misleading_cost():
    usage = normalize_model_call_usage(_hermes_usage(uncached=700,cache_read=100,cache_write=200,output=10))
    assert usage["input_tokens"] == 1000
    assert usage["cache_write_input_tokens"] == 200
    assert usage["uncached_input_tokens"] == 700
    cost = estimate_model_call_cost(model="gpt-6-luna",usage=usage)
    assert cost["status"] == "unavailable"
    assert cost["pricing_table_matched"] is True
    assert "usd" not in cost


def test_unpriced_write_call_makes_aggregate_cost_partial_not_zero_complete():
    first = map_hermes_observer_to_model_call(
        _observer_payload(api_request_id="writes",usage=_hermes_usage(cache_write=200)),
        status="ok",sequence=1,
    )
    second = map_hermes_observer_to_model_call(
        _observer_payload(api_request_id="no-writes",usage=_hermes_usage(cache_write=0)),
        status="ok",sequence=2,
    )
    usage = aggregate_usage([first,second])
    assert usage["cache_write_input_tokens"] == 200
    cost = aggregate_cost([first,second])
    assert cost["status"] == "partial"
