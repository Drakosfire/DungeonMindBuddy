import json
from types import SimpleNamespace

import pytest
from generationengine.failures import FailureCode, InferenceFailure
from generationengine.observation import InferenceObservation, ObservationState
from generationengine.types import GenerationEngineError, TextResult

from src.graph_memory.extraction.bounded_recap_execution import (
    BoundedRecapPassClient,
    RecapExecutionLimits,
)
from src.graph_memory.extraction.category_candidate_graph_extractor import (
    CategoryGraphExtractionError,
)


def observation(**changes):
    return InferenceObservation(
        provider="openai",
        requested_model="gpt-6-luna",
        resolved_model="gpt-6-luna",
        response_model="gpt-6-luna-actual",
        provider_request_id="request",
        provider_response_id="response",
        latency_ms=12,
        retry_count=0,
        state=ObservationState.COMPLETED,
        **changes,
    )


class Engine:
    def __init__(self, response):
        self.response = response
        self.requests = []
        self.closed = 0

    async def generate_text(self, request):
        self.requests.append(request)
        if isinstance(self.response, Exception):
            raise self.response
        return self.response

    async def aclose(self):
        self.closed += 1


def invoke(client, model="gpt-6-luna"):
    return client.run_pass(
        "actor_pass",
        model_id=model,
        instructions="PRIVATE_PROMPT",
        user_content="PRIVATE_SOURCE",
    )


def test_owning_request_caps_and_unknown_receipt():
    engine = Engine(TextResult(text='{"nodes": []}', observation=observation()))
    client = BoundedRecapPassClient(
        RecapExecutionLimits(max_calls=1), engine_factory=lambda: engine
    )
    result = invoke(client)
    request = engine.requests[0]
    assert (request.provider, request.model, request.temperature) == (
        "openai",
        "gpt-6-luna",
        None,
    )
    assert (request.max_output_tokens, request.max_transport_retries) == (8192, 0)
    assert 0 < request.deadline_ms <= 60000
    assert request.json_schema and request.schema_name == "category_graph_actor_pass"
    assert result["usage"]["input_tokens"] is None and result["cost_usd"] is None
    assert client.calls[0]["observation"]["response_model"] == "gpt-6-luna-actual"
    assert client.calls[0]["observation"]["provider_request_id"] == "request"
    assert "PRIVATE" not in json.dumps(client.ledger())
    assert engine.closed == 1
    with pytest.raises(CategoryGraphExtractionError):
        invoke(client)
    assert len(engine.requests) == 1


@pytest.mark.parametrize(
    "code,state",
    [
        (FailureCode.PROVIDER_REFUSED, ObservationState.REFUSED),
        (FailureCode.PROVIDER_INCOMPLETE, ObservationState.INCOMPLETE),
    ],
)
def test_failure_metadata_preserved_and_no_next_call(code, state):
    obs = observation().model_copy(update={"state": state, "failure_code": code})
    error = GenerationEngineError(
        InferenceFailure.from_code(code, "Synthetic provider failure"), obs
    )
    engine = Engine(error)
    client = BoundedRecapPassClient(
        RecapExecutionLimits(), engine_factory=lambda: engine
    )
    with pytest.raises(CategoryGraphExtractionError):
        invoke(client)
    assert client.calls[0]["observation"]["state"] == state.value
    assert client.calls[0]["observation"]["provider_response_id"] == "response"
    with pytest.raises(CategoryGraphExtractionError):
        invoke(client)
    assert len(engine.requests) == 1


def test_expired_budget_and_wrong_model_never_call():
    engine = Engine(None)
    clock = [0.0]
    client = BoundedRecapPassClient(
        RecapExecutionLimits(run_deadline_ms=100),
        engine_factory=lambda: engine,
        clock=lambda: clock[0],
    )
    clock[0] = 0.11
    with pytest.raises(CategoryGraphExtractionError):
        invoke(client)
    other = BoundedRecapPassClient(
        RecapExecutionLimits(), engine_factory=lambda: engine
    )
    with pytest.raises(CategoryGraphExtractionError):
        invoke(other, "other")
    assert not engine.requests


def test_remaining_deadline_shrinks_and_zero_usage_is_known():
    engine = Engine(
        TextResult(text="{}", observation=observation(input_tokens=0, output_tokens=0))
    )
    clock = [0.0]
    client = BoundedRecapPassClient(
        RecapExecutionLimits(run_deadline_ms=1000),
        engine_factory=lambda: engine,
        clock=lambda: clock[0],
    )
    clock[0] = 0.25
    invoke(client)
    assert engine.requests[0].deadline_ms == 750
    assert client.calls[0]["observation"]["input_tokens"] == 0


def test_wrapper_persists_ledger_on_failed_result(tmp_path, monkeypatch):
    from apps.live_control_server.services import graph_preview_runner as wrapper

    engine = Engine(TextResult(text="{}", observation=observation()))
    client = BoundedRecapPassClient(
        RecapExecutionLimits(), engine_factory=lambda: engine
    )
    monkeypatch.setattr(wrapper, "BoundedRecapPassClient", lambda limits: client)
    monkeypatch.setattr(
        wrapper,
        "create_recap_source_artifact",
        lambda *a, **k: SimpleNamespace(source_artifact_id="source"),
    )
    monkeypatch.setattr(
        wrapper,
        "_normalized_from_registered",
        lambda *a: SimpleNamespace(
            source_artifact_id="source", source_sha256="hash", source_span_index={}
        ),
    )

    def run(request):
        invoke(request.category_client)
        return SimpleNamespace(run=SimpleNamespace(run_id="new-run"))

    monkeypatch.setattr(wrapper, "run_production_extraction", run)
    output = tmp_path / "new-output"
    result = wrapper.run_recap_production_extraction(
        repo_root=tmp_path,
        campaign_id="synthetic",
        session_id="session-1",
        recap_path=tmp_path / "source.md",
        model_id="gpt-6-luna",
        allow_llm=True,
        output_dir=output,
        execution_limits=RecapExecutionLimits(),
    )
    assert result.run.run_id == "new-run"
    ledger = json.loads((output / "inference_call_ledger.json").read_text())
    assert len(ledger["calls"]) == 1
    assert "PRIVATE" not in json.dumps(ledger)
    with pytest.raises(ValueError):
        wrapper.run_recap_production_extraction(
            repo_root=tmp_path,
            campaign_id="synthetic",
            session_id="session-1",
            recap_path=tmp_path / "source.md",
            model_id="gpt-6-luna",
            allow_llm=True,
            output_dir=output,
            execution_limits=RecapExecutionLimits(),
        )


def test_ge_incomplete_through_one_recap_never_appends_candidate(tmp_path, monkeypatch):
    import hashlib
    from apps.live_control_server.services import graph_preview_runner as wrapper
    from apps.live_control_server.services import graph_run_registry as registry
    from src.graph_memory.extraction import graph_preview_runner as controller
    from graph_memory.ingestion.extraction_run import ExtractionRunStatus
    from graph_memory.source_span import (
        build_source_span_index_for_text,
        source_span_index_to_dict,
    )
    from src.graph_memory.extraction.source_adapter import NormalizedExtractionSource

    code = FailureCode.PROVIDER_INCOMPLETE
    obs = observation().model_copy(
        update={"state": ObservationState.INCOMPLETE, "failure_code": code}
    )
    engine = Engine(
        GenerationEngineError(
            InferenceFailure.from_code(code, "Synthetic provider failure"), obs
        )
    )
    client = BoundedRecapPassClient(
        RecapExecutionLimits(), engine_factory=lambda: engine
    )
    monkeypatch.setattr(wrapper, "BoundedRecapPassClient", lambda limits: client)
    text = "A keeper guards a gate.\n"
    digest = hashlib.sha256(text.encode()).hexdigest()
    source_path = tmp_path / "source.md"
    source_path.write_text(text)
    index = build_source_span_index_for_text(
        source_artifact_id="synthetic-source", content_sha256=digest, text=text
    )
    source = NormalizedExtractionSource(
        source_artifact_id="synthetic-source",
        source_domain="recap",
        source_text=text,
        source_sha256=digest,
        source_uri="repo://source.md",
        campaign_id="synthetic",
        session_id="session-1",
        document_class="recap",
        source_span_index=source_span_index_to_dict(index),
    )
    monkeypatch.setattr(
        wrapper,
        "create_recap_source_artifact",
        lambda *a, **k: SimpleNamespace(source_artifact_id="synthetic-source"),
    )
    monkeypatch.setattr(wrapper, "_normalized_from_registered", lambda *a: source)
    current = SimpleNamespace(
        run_id="synthetic-run", revision=1, status=ExtractionRunStatus.DRAFT, lineage={}
    )
    states = []
    monkeypatch.setattr(controller, "_create_draft_run", lambda *a, **k: current)

    def advance(root, run, *, status, **kwargs):
        current.status = status
        current.revision += 1
        current.lineage = kwargs.get("lineage") or current.lineage
        states.append(status)
        return current

    monkeypatch.setattr(controller, "_advance_run", advance)
    monkeypatch.setattr(registry, "get_extraction_run", lambda *a: current)
    from src.graph_memory.extraction import (
        category_candidate_graph_extractor as extractor,
    )

    monkeypatch.setattr(
        extractor,
        "build_party_context_for_campaign",
        lambda *a: extractor._empty_party_context("synthetic"),
    )
    monkeypatch.setattr(
        extractor,
        "build_known_entity_registry",
        lambda *a, **k: extractor._empty_known_entity_registry("synthetic"),
    )
    output = tmp_path / "new-output"
    result = wrapper.run_recap_production_extraction(
        repo_root=tmp_path,
        campaign_id="synthetic",
        session_id="session-1",
        recap_path=source_path,
        profile="recap_category_v1@1.0",
        model_id="gpt-6-luna",
        allow_llm=True,
        output_dir=output,
        execution_limits=RecapExecutionLimits(),
    )
    assert result.failure_kind == "incomplete", result.diagnostics
    assert (
        result.candidate_graph is None and current.status == ExtractionRunStatus.FAILED
    )
    assert ExtractionRunStatus.REVIEWABLE not in states
    assert not list(output.rglob("candidate_graph.json"))
    assert len(engine.requests) == 1
    ledger = json.loads((output / "inference_call_ledger.json").read_text())
    assert (
        ledger["stopped"] and ledger["calls"][0]["observation"]["state"] == "incomplete"
    )
    assert "A keeper" not in json.dumps(ledger)


def test_public_ge_boundary_preserves_incomplete_metadata_without_retry():
    from generationengine import GenerationClient
    from generationengine.providers.errors import ProviderError

    calls = []

    class Provider:
        async def generate(self, call):
            calls.append(call)
            raise ProviderError.from_code(
                FailureCode.PROVIDER_INCOMPLETE,
                provider_request_id="request",
                provider_response_id="response",
                response_model="actual-model",
                input_tokens=3,
                output_tokens=2,
            )

    client = BoundedRecapPassClient(
        RecapExecutionLimits(),
        engine_factory=lambda: GenerationClient(text_provider=Provider()),
    )
    with pytest.raises(CategoryGraphExtractionError):
        invoke(client)
    obs = client.calls[0]["observation"]
    assert obs["state"] == "incomplete" and obs["provider_attempt_count"] == 1
    assert obs["input_tokens"] == 3 and obs["output_tokens"] == 2
    assert (
        obs["response_model"] == "actual-model"
        and obs["provider_response_id"] == "response"
    )
    assert len(calls) == 1 and client.ledger()["stopped"]


def test_public_ge_deadline_stops_slow_provider():
    import asyncio
    from generationengine import GenerationClient

    class Provider:
        async def generate(self, call):
            await asyncio.sleep(1)
            raise AssertionError("deadline must cancel provider")

    client = BoundedRecapPassClient(
        RecapExecutionLimits(per_call_deadline_ms=10),
        engine_factory=lambda: GenerationClient(text_provider=Provider()),
    )
    with pytest.raises(CategoryGraphExtractionError):
        invoke(client)
    assert client.calls[0]["observation"]["failure_code"] == "PROVIDER_TIMEOUT"
    assert client.ledger()["stopped"]
