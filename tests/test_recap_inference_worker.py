"""Actual spawned GE boundary: no networking, including stuck executor cleanup."""

import asyncio
import json
import multiprocessing
import os
import time
import threading
from dataclasses import dataclass

import pytest

from src.graph_memory.extraction.bounded_recap_execution import (
    BoundedRecapPassClient, DEEPSEEK_MODEL, RecapExecutionLimits,
)
from src.graph_memory.extraction.category_candidate_graph_extractor import CategoryGraphExtractionError
from tests.test_bounded_recap_execution import private_capture


@dataclass
class FakeGEFactory:
    calls: object
    closed: object
    pid: object
    mode: str = "normal"
    raw: str = '{"observation_nodes": []}'

    def __call__(self):
        if self.mode == "real_ge_timeout":
            return TimedGEEngine(self)
        return self

    async def _produce_structured_result(self, request):
        from generationengine.failures import FailureCode, InferenceFailure
        from generationengine.observation import InferenceObservation, ObservationState
        from generationengine.types import GenerationEngineError, TextResult

        self.calls.value += 1
        self.pid.value = os.getpid()
        if self.mode == "exit_without_receipt":
            os._exit(1)
        if self.mode == "missing_receipt":
            await asyncio.Event().wait()
        if self.mode in {"executor_cleanup", "failed_executor_cleanup"}:
            asyncio.get_running_loop().run_in_executor(None, threading.Event().wait)
        if self.mode == "worker_failure":
            raise RuntimeError("PRIVATE_EXCEPTION_BODY")
        observation = InferenceObservation(
            provider="openrouter", requested_model=DEEPSEEK_MODEL,
            resolved_model=DEEPSEEK_MODEL, response_model=DEEPSEEK_MODEL,
            provider_attempt_count=1, provider_request_id="request",
            provider_response_id="response", latency_ms=12, retry_count=0,
            state=ObservationState.COMPLETED, input_tokens=None, output_tokens=3,
        )
        if self.mode in {"provider_failure", "failed_executor_cleanup"}:
            code = FailureCode.PROVIDER_TIMEOUT
            observation = observation.model_copy(update={
                "state": ObservationState.FAILED, "failure_code": code,
                "input_tokens": None, "output_tokens": None,
            })
            raise GenerationEngineError(InferenceFailure.from_code(code), observation)
        return TextResult(text=self.raw, observation=observation)

    async def generate_structured(self, request, *, on_attempt_completed=None):
        from generationengine.types import StructuredAttemptCompleted

        result = await self._produce_structured_result(request)
        if on_attempt_completed is not None:
            await on_attempt_completed(
                StructuredAttemptCompleted(
                    operation_id="fake-operation",
                    event_id="fake-operation:1",
                    ordinal=1,
                    kind="initial",
                    provider="openrouter",
                    requested_model=DEEPSEEK_MODEL,
                    resolved_model=DEEPSEEK_MODEL,
                    response_model=DEEPSEEK_MODEL,
                    provider_request_id="request",
                    provider_response_id="response",
                    text=result.text,
                    input_tokens=result.observation.input_tokens,
                    output_tokens=result.observation.output_tokens,
                )
            )
        return result

    async def aclose(self):
        self.closed.value += 1
        if self.mode == "blocked_close":
            await asyncio.Event().wait()


class BlockingProvider:
    def __init__(self, counters):
        self.counters = counters

    async def generate(self, call):
        self.counters.calls.value += 1
        self.counters.pid.value = os.getpid()
        asyncio.get_running_loop().run_in_executor(None, threading.Event().wait)
        await asyncio.Event().wait()

    async def aclose(self):
        self.counters.closed.value += 1


class TimedGEEngine:
    def __init__(self, counters):
        from generationengine import GenerationClient

        self.engine = GenerationClient(text_providers={"openrouter": BlockingProvider(counters)})

    async def generate_structured(self, request, *, on_attempt_completed=None):
        # Short GE timer leaves time to observe the real failure receipt before
        # the outer process timer. No SDK/client/network is constructed.
        return await self.engine.generate_structured(
            request.model_copy(update={"deadline_ms": 50}),
            on_attempt_completed=on_attempt_completed,
        )

    async def aclose(self):
        await self.engine.aclose()


class AttemptTextProvider:
    def __init__(self, calls, mode):
        self.calls = calls
        self.mode = mode

    async def generate(self, call):
        from generationengine.failures import FailureCode
        from generationengine.providers.errors import ProviderError
        from generationengine.providers.base import TextGenerationResult

        self.calls.value += 1
        ordinal = self.calls.value
        if self.mode == "invalid_then_wait" and ordinal == 2:
            await asyncio.Event().wait()
        if self.mode == "invalid_then_transport" and ordinal == 2:
            raise ProviderError.from_code(FailureCode.RATE_LIMITED)
        if self.mode in {"invalid_then_valid", "invalid_then_wait", "invalid_then_transport", "sink_failure"}:
            text = "not-json" if ordinal == 1 else '{"observation_nodes": []}'
        elif self.mode == "final_invalid":
            text = "not-json" if ordinal == 1 else '{"observation_nodes": "wrong"}'
        else:
            text = '{"observation_nodes": []}'
        return TextGenerationResult(
            text=text,
            provider_request_id=f"request-{ordinal}",
            provider_response_id=f"response-{ordinal}",
            response_model=DEEPSEEK_MODEL,
            input_tokens=ordinal if ordinal == 1 else None,
            cached_input_tokens=0,
            output_tokens=7 + ordinal,
            reasoning_tokens=None,
        )

    async def stream(self, call):
        if False:
            yield None


@dataclass
class AttemptGEFactory:
    calls: object
    mode: str

    def __call__(self):
        from generationengine import GenerationClient
        from application_state.ingest import components
        from application_state.errors import ApplicationStateUnavailableError

        if self.mode in {"sink_failure", "ambiguous_commit"}:
            persist = components.persist_execution_event
            def fail_callback(**kwargs):
                if kwargs["kind"] == "raw_model_response":
                    if self.mode == "ambiguous_commit":
                        persist(**kwargs)
                    raise ApplicationStateUnavailableError("synthetic callback commit uncertainty")
                return persist(**kwargs)
            components.persist_execution_event = fail_callback
        if self.mode == "kill_during_persist":
            insert = components._persist_payload
            def blocked_commit(conn, **kwargs):
                result = insert(conn, **kwargs)
                if kwargs["kind"].value == "raw_model_response":
                    threading.Event().wait()
                return result
            components._persist_payload = blocked_commit
        if self.mode == "malformed_receipt":
            from src.graph_memory.extraction import _recap_inference_worker as worker
            def malformed(path, receipt):
                path.write_text("not a receipt")
            worker._write_receipt = malformed
        return GenerationClient(
            text_providers={"openrouter": AttemptTextProvider(self.calls, self.mode)}
        )


def build_attempt_client(tmp_path, mode, *, run_deadline_ms=5000):
    context = multiprocessing.get_context("spawn")
    factory = AttemptGEFactory(context.Value("i", 0), mode)
    client = BoundedRecapPassClient(
        RecapExecutionLimits(
            provider="openrouter",
            model=DEEPSEEK_MODEL,
            max_calls=1,
            per_call_deadline_ms=60_000,
            run_deadline_ms=run_deadline_ms,
        ),
        engine_factory=factory,
        request_context_hashes={"normalized_source": "a" * 64},
    )
    from tests.test_bounded_recap_execution import bind_private_client
    bind_private_client(client)
    return client, factory, client.execution_binding


def build_client(mode="normal", raw='{"observation_nodes": []}', budget=2000):
    context = multiprocessing.get_context("spawn")
    factory = FakeGEFactory(
        context.Value("i", 0), context.Value("i", 0), context.Value("i", 0),
        mode, raw,
    )
    client = BoundedRecapPassClient(
        RecapExecutionLimits(provider="openrouter", model=DEEPSEEK_MODEL,
                            per_call_deadline_ms=budget, run_deadline_ms=budget),
        engine_factory=factory,
    )
    return client, factory


def invoke(client):
    return client.run_pass("actor_pass", model_id=DEEPSEEK_MODEL,
                           instructions="PRIVATE_PROMPT", user_content="PRIVATE_SOURCE")


def assert_reaped(factory):
    assert factory.pid.value > 0
    with pytest.raises(ProcessLookupError):
        os.kill(factory.pid.value, 0)
    assert not any(p.name == "dmb-recap-inference" for p in multiprocessing.active_children())


@pytest.mark.parametrize("mode", ["missing_receipt", "worker_failure", "exit_without_receipt"])
def test_missing_ge_receipt_is_unknown_and_never_redispatches(mode):
    client, factory = build_client(mode)
    started = time.monotonic()
    with pytest.raises(CategoryGraphExtractionError, match="outcome unknown"):
        invoke(client)
    assert time.monotonic() - started < 2.5
    assert client.calls[0]["external_outcome"] == "unknown"
    assert client.calls[0]["observation"] is None
    assert client.ledger()["pass_invocation_count"] == 1
    assert client.ledger()["attempt_counts"]["provider_attempts"] == {
        "total": None,
        "known_total": 0,
        "complete": False,
    }
    with pytest.raises(CategoryGraphExtractionError):
        invoke(client)
    assert factory.calls.value == 1
    assert "PRIVATE" not in json.dumps(client.ledger())
    assert_reaped(factory)


@pytest.mark.parametrize("mode", ["executor_cleanup", "blocked_close"])
def test_completed_receipt_survives_blocked_background_cleanup(mode):
    client, factory = build_client(mode)
    started = time.monotonic()
    try:
        result = invoke(client)
        assert time.monotonic() - started < 2.5
        assert result["raw_text"] == factory.raw
        assert result["usage"] == {"input_tokens": None, "output_tokens": 3, "cached_tokens": None}
        assert result["response_id"] == "response" and result["cost_usd"] is None
        assert client.calls[0]["worker_cleanup"] == "terminated"
        assert client.calls[0]["external_outcome"] == "completed"
        assert factory.calls.value == factory.closed.value == 1
        assert_reaped(factory)
        with pytest.raises(CategoryGraphExtractionError):
            invoke(client)
        assert factory.calls.value == 1
    finally:
        assert_reaped(factory)


@pytest.mark.usefixtures("application_state_dsn")
def test_real_ge_attempt_hook_persists_invalid_then_valid_before_single_correction(tmp_path):
    client, factory, _ = build_attempt_client(tmp_path, "invalid_then_valid")

    result = invoke(client)

    entry = client.calls[0]
    assert result["parsed"] == {"observation_nodes": []}
    assert factory.calls.value == 2
    assert entry["observation"]["provider_attempt_count"] == 2
    assert entry["observation"]["transport_retry_count"] == 0
    assert entry["observation"]["conformance_retry_count"] == 1
    assert client.ledger()["pass_invocation_count"] == 1
    assert client.ledger()["attempt_counts"]["provider_attempts"] == {
        "total": 2,
        "known_total": 2,
        "complete": True,
    }
    assert [item["ordinal"] for item in entry["attempt_evidence"]] == [1, 2]
    assert [item["kind"] for item in entry["attempt_evidence"]] == [
        "initial",
        "conformance",
    ]
    evidence = [
        private_capture(client, item["sha256"])
        for item in entry["attempt_evidence"]
    ]
    assert [item["response"]["text"] for item in evidence] == [
        "not-json",
        '{"observation_nodes": []}',
    ]
    assert evidence[0]["ge_attempt"]["operation_id"] == evidence[1]["ge_attempt"]["operation_id"]
    assert evidence[0]["ge_attempt"]["event_id"] != evidence[1]["ge_attempt"]["event_id"]
    assert evidence[0]["request"]["system_prompt_sha256"]
    assert evidence[0]["context_sha256"]["normalized_source"] == "a" * 64
    assert evidence[0]["context_sha256"]["source_content"] == client.execution_binding["source_sha256"]
    assert evidence[0]["response"]["sha256"]
    assert "not-json" not in json.dumps(client.ledger())
    assert evidence[0]["execution_binding"] == client.execution_binding


@pytest.mark.usefixtures("application_state_dsn")
def test_real_ge_final_invalid_response_keeps_both_attempts_and_failure_observation(tmp_path):
    client, factory, _ = build_attempt_client(tmp_path, "final_invalid")

    with pytest.raises(CategoryGraphExtractionError):
        invoke(client)

    entry = client.calls[0]
    assert factory.calls.value == 2
    assert entry["failure_code"] == "STRUCTURED_OUTPUT_INVALID"
    assert entry["consumer_outcome"] == "invalid_structured_output"
    assert entry["observation"]["failure_code"] == "STRUCTURED_OUTPUT_INVALID"
    assert entry["observation"]["provider_attempt_count"] == 2
    assert entry["observation"]["transport_retry_count"] == 0
    assert entry["observation"]["conformance_retry_count"] == 1
    assert [item["ordinal"] for item in entry["attempt_evidence"]] == [1, 2]
    assert "not-json" not in json.dumps(client.ledger())
    assert all(private_capture(client, item["sha256"]) for item in entry["attempt_evidence"])


@pytest.mark.usefixtures("application_state_dsn")
def test_real_ge_transport_failure_after_initial_response_is_counted_without_event_or_retry(
    tmp_path,
):
    client, factory, _ = build_attempt_client(tmp_path, "invalid_then_transport")

    with pytest.raises(CategoryGraphExtractionError):
        invoke(client)

    entry = client.calls[0]
    assert factory.calls.value == 2
    assert entry["failure_code"] == "RATE_LIMITED"
    assert entry["observation"]["provider_attempt_count"] == 2
    assert entry["observation"]["transport_retry_count"] == 0
    assert entry["observation"]["conformance_retry_count"] == 1
    assert [item["ordinal"] for item in entry["attempt_evidence"]] == [1]


@pytest.mark.usefixtures("application_state_dsn")
def test_real_ge_sink_failure_stops_without_correction_or_replay(tmp_path):
    client, factory, _ = build_attempt_client(tmp_path, "sink_failure")
    with pytest.raises(CategoryGraphExtractionError):
        invoke(client)
    entry = client.calls[0]
    assert factory.calls.value == 1
    assert entry["failure_code"] == "ATTEMPT_EVIDENCE_PERSISTENCE_FAILED"
    assert entry["consumer_failure"] == "AttemptEvidencePersistenceFailed"
    assert entry["observation"]["provider_attempt_count"] == 1
    assert entry["observation"]["conformance_retry_count"] == 0
    assert entry["attempt_evidence"] == []
    assert client.retention_failed
    assert not [r for r in client._execution_records() if r["kind"] == "raw_model_response"]


@pytest.mark.usefixtures("application_state_dsn")
def test_first_attempt_artifact_survives_worker_termination_during_correction(tmp_path):
    client, factory, _ = build_attempt_client(
        tmp_path, "invalid_then_wait", run_deadline_ms=5000
    )

    with pytest.raises(CategoryGraphExtractionError, match="outcome unknown"):
        invoke(client)

    entry = client.calls[0]
    assert entry["external_outcome"] == "unknown"
    assert entry["worker_cleanup"] == "terminated"
    assert factory.calls.value == 2
    assert len(entry["attempt_evidence"]) == 1
    artifact = private_capture(client, entry["attempt_evidence"][0]["sha256"])
    assert artifact["response"]["text"] == "not-json"
    assert artifact["ge_attempt"]["ordinal"] == 1
    assert artifact["execution_binding"] == client.execution_binding
    assert "not-json" not in json.dumps(client.ledger())

    with pytest.raises(CategoryGraphExtractionError):
        invoke(client)
    assert factory.calls.value == 2


@pytest.mark.parametrize("mode", ["provider_failure", "failed_executor_cleanup"])
def test_known_failure_receipt_and_null_usage_survive_cleanup(mode):
    client, factory = build_client(mode)
    try:
        with pytest.raises(CategoryGraphExtractionError, match="PROVIDER_TIMEOUT"):
            invoke(client)
        obs = client.calls[0]["observation"]
        assert obs["provider_response_id"] == "response"
        assert obs["input_tokens"] is None and obs["output_tokens"] is None
        assert obs["cost_usd"] is None and obs["provider_attempt_count"] == 1
        assert obs["retry_count"] == 0
        assert client.calls[0]["external_outcome"] == "known_failure"
        with pytest.raises(CategoryGraphExtractionError):
            invoke(client)
        assert factory.calls.value == 1
        assert_reaped(factory)
    finally:
        assert_reaped(factory)


@pytest.mark.parametrize("raw", ['{"observation_nodes": []}', '{"observation_nodes": "PRIVATE_RESPONSE"}'])
def test_actual_process_preserves_normal_and_schema_failure_text_and_accounting(raw):
    client, factory = build_client(raw=raw)
    if "PRIVATE_RESPONSE" in raw:
        with pytest.raises(CategoryGraphExtractionError) as caught:
            invoke(client)
        assert caught.value.raw_model_response == raw
        assert client.calls[0]["validation_failure"]["kind"] == "schema"
    else:
        result = invoke(client)
        assert result["parsed"] == {"observation_nodes": []}
        assert result["raw_text"] == raw
    assert client.calls[0]["observation"]["input_tokens"] is None
    assert client.calls[0]["observation"]["output_tokens"] == 3
    assert "PRIVATE" not in json.dumps(client.ledger())
    assert factory.closed.value == factory.calls.value == 1
    assert_reaped(factory)


def test_spawn_failure_stops_before_dispatch_without_surviving_child():
    client = BoundedRecapPassClient(
        RecapExecutionLimits(provider="openrouter", model=DEEPSEEK_MODEL),
        engine_factory=lambda: None,
    )
    with pytest.raises(CategoryGraphExtractionError):
        invoke(client)
    assert client.ledger()["stopped"]
    assert client.calls[0]["observation"] is None
    assert client.calls[0]["external_outcome"] == "not_started"
    assert not any(p.name == "dmb-recap-inference" for p in multiprocessing.active_children())


def test_remaining_run_budget_bounds_child_cleanup_too():
    client, factory = build_client("missing_receipt", budget=2500)
    client._started -= 0.5
    started = time.monotonic()
    with pytest.raises(CategoryGraphExtractionError, match="outcome unknown"):
        invoke(client)
    assert 1900 <= client.calls[0]["deadline_ms"] <= 2000
    assert time.monotonic() - started < 2.25
    assert_reaped(factory)


def test_real_ge_deadline_receipt_survives_blocked_executor_shutdown():
    client, factory = build_client("real_ge_timeout")
    started = time.monotonic()
    with pytest.raises(CategoryGraphExtractionError, match="PROVIDER_TIMEOUT"):
        invoke(client)
    assert time.monotonic() - started < 2.25
    obs = client.calls[0]["observation"]
    assert 40 <= obs["latency_ms"] < 1000
    assert obs["provider_attempt_count"] == 1 and obs["retry_count"] == 0
    assert obs["input_tokens"] is None and obs["output_tokens"] is None
    assert obs["cost_usd"] is None and obs.get("provider_request_id") is None
    assert client.calls[0]["worker_cleanup"] == "terminated"
    assert client.calls[0]["external_outcome"] == "known_failure"
    assert factory.calls.value == factory.closed.value == 1
    assert_reaped(factory)
    with pytest.raises(CategoryGraphExtractionError):
        invoke(client)
    assert factory.calls.value == 1


@pytest.mark.usefixtures("application_state_dsn")
def test_committed_response_survives_malformed_temporary_receipt(tmp_path):
    client, factory, _ = build_attempt_client(tmp_path, "malformed_receipt")
    with pytest.raises(CategoryGraphExtractionError):
        invoke(client)
    assert factory.calls.value == 1
    entry = client.calls[0]
    assert entry["external_outcome"] == "unknown"
    assert len(entry["attempt_evidence"]) == 1
    assert private_capture(client, entry["attempt_evidence"][0]["sha256"])["response"]["text"] == '{"observation_nodes": []}'
    assert not any(p.name == "dmb-recap-inference" for p in multiprocessing.active_children())


@pytest.mark.usefixtures("application_state_dsn")
def test_commit_uncertainty_preserves_bytes_without_ack_or_redispatch(tmp_path):
    client, factory, _ = build_attempt_client(tmp_path, "ambiguous_commit")
    with pytest.raises(CategoryGraphExtractionError):
        invoke(client)
    assert factory.calls.value == 1
    assert client.retention_failed
    assert client.calls[0]["failure_code"] == "ATTEMPT_EVIDENCE_PERSISTENCE_FAILED"
    assert len(client.calls[0]["attempt_evidence"]) == 1
    with pytest.raises(CategoryGraphExtractionError):
        invoke(client)
    assert factory.calls.value == 1


@pytest.mark.usefixtures("application_state_dsn")
def test_kill_during_unacknowledged_commit_reports_unknown(tmp_path):
    client, factory, _ = build_attempt_client(tmp_path, "kill_during_persist", run_deadline_ms=5000)
    with pytest.raises(CategoryGraphExtractionError, match="outcome unknown"):
        invoke(client)
    assert factory.calls.value == 1
    assert client.calls[0]["worker_cleanup"] == "terminated"
    assert client.calls[0]["attempt_evidence"] == []
    assert client.ledger()["attempt_counts"]["provider_attempts"]["complete"] is False
    assert not any(p.name == "dmb-recap-inference" for p in multiprocessing.active_children())


@pytest.mark.usefixtures("application_state_dsn")
def test_acknowledged_capture_survives_blocked_worker_cleanup():
    from tests.test_bounded_recap_execution import bind_private_client
    client, factory = build_client("blocked_close", budget=5000)
    bind_private_client(client)
    assert invoke(client)["raw_text"] == factory.raw
    assert client.calls[0]["worker_cleanup"] == "terminated"
    assert len(client.calls[0]["attempt_evidence"]) == 1
    assert private_capture(client, client.calls[0]["attempt_evidence"][0]["sha256"])["response"]["text"] == factory.raw
    assert_reaped(factory)
