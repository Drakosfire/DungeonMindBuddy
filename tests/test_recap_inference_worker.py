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

    async def generate_text(self, request):
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

    async def generate_text(self, request):
        # Short GE timer leaves time to observe the real failure receipt before
        # the outer process timer. No SDK/client/network is constructed.
        return await self.engine.generate_text(request.model_copy(update={"deadline_ms": 50}))

    async def aclose(self):
        await self.engine.aclose()


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
        assert "external_outcome" not in client.calls[0]
        assert factory.calls.value == factory.closed.value == 1
        assert_reaped(factory)
        with pytest.raises(CategoryGraphExtractionError):
            invoke(client)
        assert factory.calls.value == 1
    finally:
        assert_reaped(factory)


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
        assert "external_outcome" not in client.calls[0]
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
    assert obs["cost_usd"] is None and obs["provider_request_id"] is None
    assert client.calls[0]["worker_cleanup"] == "terminated"
    assert "external_outcome" not in client.calls[0]
    assert factory.calls.value == factory.closed.value == 1
    assert_reaped(factory)
    with pytest.raises(CategoryGraphExtractionError):
        invoke(client)
    assert factory.calls.value == 1
