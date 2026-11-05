import json
from apps.live_control_server.services.source_artifact_registry import create_recap_source_artifact
import asyncio
from pathlib import Path
from types import SimpleNamespace

import pytest
from generationengine.failures import FailureCode, InferenceFailure
from generationengine.observation import InferenceObservation, ObservationState
from generationengine.types import (
    GenerationEngineError,
    StructuredAttemptCompleted,
    TextResult,
)

from src.graph_memory.extraction.bounded_recap_execution import (
    BoundedRecapPassClient,
    DEEPSEEK_MODEL,
    RecapExecutionLimits,
)


@pytest.mark.parametrize("response_status", ["returned", "refused", "incomplete"])
def test_returned_attempt_survives_unknown_worker_receipt(monkeypatch, response_status):
    from src.graph_memory.extraction import bounded_recap_execution as module
    from src.graph_memory.extraction._recap_inference_worker import _WorkerOutcome

    event = {"event_id": "operation:1", "ordinal": 1, "kind": "initial",
             "response_status": response_status, "provider_response_id": "response:1",
             "input_tokens": 12, "output_tokens": 9, "cost_usd": 0.02}
    record = {"pass_ordinal": 1, "pass_name": "actor_pass", "ge_attempt": event,
              "capture_id": "capture:1", "response": {"text": "PRIVATE_RESPONSE"}}
    client = BoundedRecapPassClient(RecapExecutionLimits())
    client.execution_binding = {"run_id": "synthetic"}
    monkeypatch.setattr(client, "_persist_capture", lambda *args: None)
    monkeypatch.setattr(client, "_execution_records", lambda: [{"record": record, "sha256": "digest"}])
    monkeypatch.setattr(module, "_execute_in_owned_process", lambda *args, **kwargs: _WorkerOutcome(None, True))
    with pytest.raises(CategoryGraphExtractionError, match="without receipt"):
        invoke(client)
    ledger = client.ledger()
    assert ledger["calls"][0]["observation"] is None
    assert ledger["calls"][0]["external_outcome"] == "unknown"
    assert ledger["calls"][0]["attempt_evidence"][0]["cost_usd"] == 0.02
    assert ledger["attempt_counts"]["provider_attempts"] == {
        "known_total": 1, "total": None, "complete": False,
    }
    assert ledger["attempt_counts"]["conformance_retries"]["total"] is None
    assert "PRIVATE_RESPONSE" not in json.dumps(ledger)


def test_acknowledged_attempts_deduplicate_and_reject_conflicts():
    from src.graph_memory.extraction.bounded_recap_execution import _acknowledged_attempts

    event = {"event_id": "e1", "response_status": "returned", "cost_usd": 0,
             "provider_response_id": "r1"}
    assert len(_acknowledged_attempts([event, dict(event)])) == 1
    assert _acknowledged_attempts([{**event, "provider_response_id": None}])[0]["cost_usd"] == 0
    with pytest.raises(ValueError, match="conflicting"):
        _acknowledged_attempts([event, {**event, "cost_usd": 1}])
    with pytest.raises(ValueError, match="multiple"):
        _acknowledged_attempts([event, {**event, "event_id": "e2"}])
    for cost in (True, -1, float("nan"), float("inf")):
        with pytest.raises(ValueError, match="cost"):
            _acknowledged_attempts([{**event, "cost_usd": cost}])
from src.graph_memory.extraction.category_candidate_graph_extractor import (
    CategoryGraphExtractionError,
)


def _fixture_ingest_context(campaign_id: str):
    from graph_memory.ingestion.native_recap_source import SourceScope

    return SourceScope(managed_world_id='managed-fixture-world', native_world_id='world:synthetic', binding_version=1, campaign_id=campaign_id)


@pytest.fixture(autouse=True)
def semantic_engine_seam(monkeypatch):
    """Use explicit structured fake engines; process tests live separately."""
    from src.graph_memory.extraction import bounded_recap_execution as module
    from src.graph_memory.extraction._recap_inference_worker import _WorkerOutcome

    def execute(factory, request, *, deadline, attempt_evidence=None):
        from generationengine.types import TextRequest
        from src.graph_memory.extraction.bounded_recap_execution import (
            _persist_attempt_response,
        )

        async def run():
            try:
                engine = factory()
            except Exception as exc:
                return {"kind": "worker_failure", "error_type": type(exc).__name__}
            try:
                typed_request = TextRequest.model_validate(request)
                callback = None
                if attempt_evidence is not None:
                    async def on_attempt_completed(event):
                        _persist_attempt_response(attempt_evidence, request, event)

                    callback = on_attempt_completed
                result = await engine.generate_structured(
                    typed_request, on_attempt_completed=callback
                )
                return {
                    "kind": "result",
                    "result": result.model_dump(mode="json"),
                }
            except GenerationEngineError as exc:
                return {
                    "kind": "provider_failure", "failure_code": exc.failure.code.value,
                    "observation": exc.observation.model_dump(mode="json"),
                }
            finally:
                await engine.aclose()

        return _WorkerOutcome(asyncio.run(run()), False)

    monkeypatch.setattr(module, "_execute_in_owned_process", execute)


async def _complete_fake_structured_result(result, request, callback):
    if isinstance(result, Exception):
        raise result
    if callback is not None:
        observation = result.observation
        event = StructuredAttemptCompleted(
            operation_id="test-structured-operation",
            event_id="test-structured-operation:1",
            ordinal=1,
            kind="initial",
            provider=observation.provider or request.provider,
            requested_model=observation.requested_model or request.model,
            resolved_model=observation.resolved_model or request.model,
            response_model=observation.response_model,
            provider_request_id=observation.provider_request_id,
            provider_response_id=observation.provider_response_id,
            text=result.text,
            input_tokens=observation.input_tokens,
            cached_input_tokens=observation.cached_input_tokens,
            output_tokens=observation.output_tokens,
            reasoning_tokens=observation.reasoning_tokens,
        )
        try:
            await callback(event)
        except Exception:
            failure = InferenceFailure.from_code(
                FailureCode.ATTEMPT_EVIDENCE_PERSISTENCE_FAILED,
                "Consumer attempt-evidence sink did not accept a returned provider response.",
            )
            failed_observation = observation.model_copy(
                update={
                    "state": ObservationState.FAILED,
                    "failure_code": failure.code,
                }
            )
            raise GenerationEngineError(failure, failed_observation) from None
    return result


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
        provider_attempt_count=1,
        state=ObservationState.COMPLETED,
        **changes,
    )


class Engine:
    def __init__(self, response):
        self.response = response
        self.requests = []
        self.closed = 0

    async def generate_structured(self, request, *, on_attempt_completed=None):
        self.requests.append(request)
        return await _complete_fake_structured_result(
            self.response, request, on_attempt_completed
        )

    async def aclose(self):
        self.closed += 1


def invoke(client, model="gpt-6-luna"):
    return client.run_pass(
        "actor_pass",
        model_id=model,
        instructions="PRIVATE_PROMPT",
        user_content="PRIVATE_SOURCE",
    )


def bind_private_client(client, *, source_sha256=None, run=None):
    from tests.application_state.test_ingest_components_postgres import prepared_execution
    if run is None:
        run, _ = prepared_execution(model_id=client.limits.model, source_sha256=source_sha256)
    client.bind_to_run(run)
    return client


def private_capture(client, digest):
    return next(row["record"] for row in client._execution_records() if row["sha256"] == digest)


def private_response_client(engine_factory, *, limits=None, run=None, clock=None):
    kwargs = {} if clock is None else {"clock": clock}
    return bind_private_client(BoundedRecapPassClient(
        limits or RecapExecutionLimits(), engine_factory=engine_factory,
        request_context_hashes={"normalized_source": "a" * 64, "settled_identity_context": "b" * 64},
        **kwargs,
    ), run=run)



def deepseek_observation(**changes):
    values = observation().model_dump()
    values.update(
        provider="openrouter",
        requested_model=DEEPSEEK_MODEL,
        resolved_model=DEEPSEEK_MODEL,
        response_model=DEEPSEEK_MODEL,
        provider_attempt_count=1,
        cost_usd=None,
    )
    values.update(changes)
    return InferenceObservation.model_validate(values)


def test_deepseek_route_caps_and_unknown_receipt():
    from src.graph_memory.extraction.category_candidate_graph_schema import (
        category_pass_text_format,
    )

    schema = category_pass_text_format("actor_pass")["format"]["schema"]
    # Empty arrays are legal for the actor pass; validate against the actual contract.
    from jsonschema import validate

    payload = {"observation_nodes": []}
    validate(payload, schema)
    engine = Engine(TextResult(text=json.dumps(payload), observation=deepseek_observation()))
    client = BoundedRecapPassClient(
        RecapExecutionLimits(provider="openrouter", model=DEEPSEEK_MODEL, max_calls=1),
        engine_factory=lambda: engine,
    )
    result = invoke(client, DEEPSEEK_MODEL)
    request = engine.requests[0]
    assert (request.provider, request.model) == ("openrouter", DEEPSEEK_MODEL)
    assert request.provider_route.order == ("DeepSeek",)
    assert request.provider_route.allow_fallbacks is False
    assert request.provider_route.require_parameters is True
    assert request.reasoning_effort == "none" and request.json_object is False
    assert request.json_schema and request.schema_name == "category_graph_actor_pass"
    assert request.max_transport_retries == 0
    assert (request.max_output_tokens, request.deadline_ms) == (8192, 120000)
    assert "PRIVATE_PROMPT" in request.system_prompt
    assert "PRIVATE_SOURCE" not in request.system_prompt
    assert "one complete JSON object" in request.system_prompt
    assert "without Markdown fences" in request.system_prompt
    assert "close every string and container" in request.system_prompt
    assert "Follow this schema" not in request.system_prompt
    assert "observation_nodes" not in request.system_prompt
    assert result["cost_usd"] is None
    assert client.calls[0]["requested_route"] == {
        "order": ["DeepSeek"],
        "allow_fallbacks": False,
        "require_parameters": True,
    }
    assert "PRIVATE" not in json.dumps(client.ledger())
    assert client.ledger()["pass_invocation_count"] == 1
    assert client.ledger()["attempt_counts"]["provider_attempts"] == {
        "total": 1,
        "known_total": 1,
        "complete": True,
    }
    assert engine.closed == 1
    with pytest.raises(CategoryGraphExtractionError):
        invoke(client, DEEPSEEK_MODEL)
    assert len(engine.requests) == 1


def test_deepseek_request_reaches_accepted_ge_openrouter_sdk_kwargs():
    from generationengine import GenerationClient
    from generationengine.providers.base import TextGenerationCall
    from generationengine.providers.openrouter_text import OpenRouterTextProvider
    from generationengine.types import ProviderRoute

    class Completions:
        def __init__(self):
            self.calls = []

        async def create(self, **kwargs):
            self.calls.append(kwargs)
            return SimpleNamespace(
                id="synthetic-response",
                _request_id="synthetic-request",
                model=DEEPSEEK_MODEL,
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(
                            content='{"observation_nodes": []}', refusal=None
                        ),
                        finish_reason="stop",
                    )
                ],
                usage=None,
            )

    completions = Completions()

    class Client:
        chat = SimpleNamespace(completions=completions)

        async def close(self):
            return None

    structured_calls = []

    class RecordingOpenRouterTextProvider(OpenRouterTextProvider):
        async def generate(self, call):
            structured_calls.append(call)
            return await super().generate(call)

    provider = RecordingOpenRouterTextProvider(client=Client())
    engine = GenerationClient(text_providers={"openrouter": provider})
    client = BoundedRecapPassClient(
        RecapExecutionLimits(provider="openrouter", model=DEEPSEEK_MODEL),
        engine_factory=lambda: engine,
    )

    result = invoke(client, DEEPSEEK_MODEL)

    assert result["parsed"] == {"observation_nodes": []}
    ge_call = structured_calls[0]
    assert ge_call.schema_name == "category_graph_actor_pass"
    assert ge_call.json_schema["properties"]["observation_nodes"]
    assert "one complete JSON object" in ge_call.system_prompt
    assert "observation_nodes" not in ge_call.system_prompt
    kwargs = completions.calls[0]
    assert "response_format" not in kwargs
    sdk_system = next(message["content"] for message in kwargs["messages"] if message["role"] == "system")
    assert sdk_system.count("one complete JSON object") == 1
    from generationengine.conformance import schema_instruction

    assert sdk_system.startswith(ge_call.system_prompt + "\n\n")
    assert sdk_system.count(schema_instruction(ge_call.json_schema)) == 1
    assert kwargs["extra_body"]["provider"] == {
        "order": ["DeepSeek"],
        "allow_fallbacks": False,
        "require_parameters": True,
    }

    default_route_kwargs = provider._request_kwargs(
        TextGenerationCall(
            model=DEEPSEEK_MODEL,
            user_prompt="synthetic",
            provider_route=ProviderRoute(order=("DeepSeek",), allow_fallbacks=False),
            json_object=True,
        )
    )
    assert default_route_kwargs["extra_body"]["provider"] == {
        "order": ["DeepSeek"],
        "allow_fallbacks": False,
    }


@pytest.mark.usefixtures("application_state_dsn")
def test_synthetic_invalid_json_is_preserved_and_classified_before_stop(tmp_path):
    import hashlib

    fixture_dir = Path(__file__).parent / "fixtures" / "graph_memory" / "recap_json_output"
    raw = (fixture_dir / "r6-object-invalid.txt").read_text(encoding="utf-8")
    labels = json.loads(
        (fixture_dir / "r6-response-classification-labels.json").read_text(
            encoding="utf-8"
        )
    )
    with pytest.raises(json.JSONDecodeError) as parse_error:
        json.loads(raw)

    engine = Engine(TextResult(text=raw, observation=deepseek_observation()))
    client = private_response_client(lambda: engine, limits=RecapExecutionLimits(provider='openrouter', model=DEEPSEEK_MODEL))
    with pytest.raises(CategoryGraphExtractionError):
        invoke(client, DEEPSEEK_MODEL)

    entry = client.ledger()["calls"][0]
    failure = entry["validation_failure"]
    assert entry["external_outcome"] == labels["external_outcome"] == "completed"
    assert entry["consumer_outcome"] == labels["consumer_outcome"] == "invalid_json"
    assert labels["candidate_promotion"] is False
    assert labels["automatic_salvage"] is False
    assert labels["replay_authorized"] is False
    assert failure["kind"] == "invalid_json"
    assert failure["position"] == parse_error.value.pos
    assert failure["line"] == parse_error.value.lineno
    assert failure["column"] == parse_error.value.colno
    assert failure["response_chars"] == len(raw)
    assert failure["response_utf8_bytes"] == len(raw.encode("utf-8"))
    assert failure["response_sha256"] == hashlib.sha256(raw.encode("utf-8")).hexdigest()
    assert raw not in json.dumps(client.ledger())

    envelope = private_capture(client, entry["response_component"]["sha256"])
    assert envelope["capture_state"] == "unvalidated_snapshot"
    assert envelope["schema"] == "dmb_private_recap_attempt_response_v1"
    assert envelope["ge_attempt"]["ordinal"] == 1
    assert envelope["ge_attempt"]["response_status"] == "returned"
    assert envelope["response"]["text"] == raw
    with pytest.raises(CategoryGraphExtractionError):
        invoke(client, DEEPSEEK_MODEL)
    assert len(engine.requests) == 1


@pytest.mark.parametrize(
    "text,changes",
    [
        ('{"observation_nodes": "wrong"}', {}),
        ('{"observation_nodes": []}', {"provider": "other"}),
        ('{"observation_nodes": []}', {"response_model": "other"}),
        ('{"observation_nodes": []}', {"response_model": "deepseek/deepseek-v4.1-flash"}),
        ('{"observation_nodes": []}', {"provider_attempt_count": 2}),
        ('{"observation_nodes": []}', {"retry_count": 1}),
    ],
)
def test_deepseek_fail_closed_without_next_call(text, changes):
    engine = Engine(TextResult(text=text, observation=deepseek_observation(**changes)))
    client = BoundedRecapPassClient(
        RecapExecutionLimits(provider="openrouter", model=DEEPSEEK_MODEL),
        engine_factory=lambda: engine,
    )
    with pytest.raises(CategoryGraphExtractionError):
        invoke(client, DEEPSEEK_MODEL)
    assert client.ledger()["stopped"]
    with pytest.raises(CategoryGraphExtractionError):
        invoke(client, DEEPSEEK_MODEL)
    assert len(engine.requests) == 1 and engine.closed == 1


@pytest.mark.parametrize(
    "raw,kind,validator,instance_path",
    [
        ('{"observation_nodes": "PRIVATE_RESPONSE"}', "schema", "type", ["observation_nodes"]),
        ('{"observation_nodes":', "invalid_json", None, []),
        ('["PRIVATE_RESPONSE"]', "non_object", None, []),
    ],
)
def test_local_response_failure_retains_private_raw_outside_safe_ledger(
    raw, kind, validator, instance_path
):
    engine = Engine(TextResult(text=raw, observation=deepseek_observation()))
    client = BoundedRecapPassClient(
        RecapExecutionLimits(provider="openrouter", model=DEEPSEEK_MODEL),
        engine_factory=lambda: engine,
    )
    with pytest.raises(CategoryGraphExtractionError) as caught:
        invoke(client, DEEPSEEK_MODEL)
    assert caught.value.raw_model_response == raw
    assert caught.value.pass_name == "actor_pass"
    failure = client.calls[0]["validation_failure"]
    assert (failure["kind"], failure["validator"], failure["instance_path"]) == (
        kind, validator, instance_path
    )
    assert "PRIVATE_RESPONSE" not in json.dumps(client.ledger())
    assert client.ledger()["stopped"]
    with pytest.raises(CategoryGraphExtractionError):
        invoke(client, DEEPSEEK_MODEL)
    assert len(engine.requests) == 1 and engine.closed == 1


@pytest.mark.usefixtures("application_state_dsn")
def test_private_response_evidence_captures_success_before_consumer_use(tmp_path):
    import hashlib

    raw = '{"observation_nodes": []}'
    engine = Engine(TextResult(text=raw, observation=observation()))
    client = private_response_client(lambda: engine)

    result = invoke(client)

    artifact = private_capture(client, client.calls[0]["response_component"]["sha256"])
    request = engine.requests[0].model_dump(mode="json")
    canonical_request = json.dumps(
        request, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    assert result["parsed"] == {"observation_nodes": []}
    assert artifact["capture_state"] == "unvalidated_snapshot"
    assert artifact["pass_name"] == "actor_pass" and artifact["pass_ordinal"] == 1
    assert artifact["request"]["sha256"] == hashlib.sha256(canonical_request).hexdigest()
    assert artifact["request"]["system_prompt_sha256"] == hashlib.sha256(
        request["system_prompt"].encode()
    ).hexdigest()
    assert artifact["request"]["user_prompt_sha256"] == hashlib.sha256(
        request["user_prompt"].encode()
    ).hexdigest()
    assert artifact["context_sha256"]["normalized_source"] == "a" * 64
    assert artifact["context_sha256"]["settled_identity_context"] == "b" * 64
    assert artifact["context_sha256"]["source_content"] == client.execution_binding["source_sha256"]
    assert artifact["response"]["text"] == raw
    assert artifact["response"]["utf8_bytes"] == len(raw.encode())
    assert artifact["response"]["sha256"] == hashlib.sha256(raw.encode()).hexdigest()
    assert artifact["ge_observation"]["provider_response_id"] == "response"
    assert "provider_request_id" not in artifact["ge_observation"]
    assert "PRIVATE_PROMPT" not in json.dumps(artifact)
    assert "PRIVATE_SOURCE" not in json.dumps(artifact)
    assert "PRIVATE" not in json.dumps(client.ledger())
    assert client.calls[0]["response_component"]["sha256"]



@pytest.mark.parametrize(
    "raw,expected_kind",
    [
        ('{"observation_nodes":', "invalid_json"),
        ('{"observation_nodes": "wrong"}', "schema"),
    ],
)
@pytest.mark.usefixtures("application_state_dsn")
def test_private_response_evidence_precedes_json_and_schema_validation(
    tmp_path, raw, expected_kind
):
    engine = Engine(TextResult(text=raw, observation=deepseek_observation()))
    client = private_response_client(lambda: engine, limits=RecapExecutionLimits(provider='openrouter', model=DEEPSEEK_MODEL))

    with pytest.raises(CategoryGraphExtractionError):
        invoke(client, DEEPSEEK_MODEL)

    artifact = private_capture(client, client.calls[0]["response_component"]["sha256"])
    assert artifact["capture_state"] == "unvalidated_snapshot"
    assert artifact["response"]["text"] == raw
    assert client.calls[0]["validation_failure"]["kind"] == expected_kind
    assert client.calls[0]["response_component"]["sha256"]
    assert "PRIVATE_PROMPT" not in json.dumps(artifact)
    assert "PRIVATE_SOURCE" not in json.dumps(artifact)


@pytest.mark.usefixtures("application_state_dsn")
def test_private_response_evidence_keeps_earlier_pass_when_later_pass_fails(tmp_path):
    responses = [
        TextResult(text='{"observation_nodes": []}', observation=observation()),
        TextResult(text='{"observation_nodes":', observation=observation()),
    ]

    class SequenceEngine:
        async def generate_structured(self, request, *, on_attempt_completed=None):
            return await _complete_fake_structured_result(
                responses.pop(0), request, on_attempt_completed
            )

        async def aclose(self):
            pass

    client = private_response_client(SequenceEngine)
    client.run_pass(
        "actor_pass", model_id="gpt-6-luna", instructions="SYSTEM", user_content="USER"
    )
    with pytest.raises(CategoryGraphExtractionError):
        client.run_pass(
            "location_pass", model_id="gpt-6-luna", instructions="SYSTEM", user_content="USER"
        )

    captures = [row["record"] for row in client._execution_records() if row["kind"] == "raw_model_response"]
    assert sorted((row["pass_ordinal"], row["pass_name"]) for row in captures) == [
        (1, "actor_pass"), (2, "location_pass"),
    ]
    assert client.calls[0]["response_component"]["sha256"]
    assert client.calls[1]["response_component"]["sha256"]


@pytest.mark.usefixtures("application_state_dsn")
def test_private_response_evidence_is_atomic_and_never_overwrites(tmp_path):
    from application_state.ingest.service import get_extraction_run
    engine = Engine(TextResult(text='{"observation_nodes": []}', observation=observation()))
    first = private_response_client(lambda: engine, clock=lambda: 0)
    invoke(first)
    digest = first.calls[0]["response_component"]["sha256"]
    original = private_capture(first, digest)
    second_engine = Engine(TextResult(text='{"observation_nodes": []}', observation=observation(input_tokens=7, output_tokens=3)))
    second = private_response_client(lambda: second_engine, clock=lambda: 0,
                                    run=get_extraction_run(first.execution_binding["run_id"]))
    with pytest.raises(CategoryGraphExtractionError, match="ATTEMPT_EVIDENCE_PERSISTENCE_FAILED"):
        invoke(second)
    assert private_capture(first, digest) == original
    assert "response_component" not in second.calls[0]
    assert second.calls[0]["consumer_failure"] == "AttemptEvidencePersistenceFailed"
    assert second.calls[0]["observation"]["input_tokens"] == 7
    assert second.calls[0]["observation"]["output_tokens"] == 3
    assert second.retention_failed
    assert "PRIVATE" not in json.dumps(second.ledger())


@pytest.mark.usefixtures("application_state_dsn")
def test_unknown_worker_receipt_does_not_create_private_response(tmp_path, monkeypatch):
    from src.graph_memory.extraction import bounded_recap_execution as module
    from src.graph_memory.extraction._recap_inference_worker import _WorkerOutcome

    monkeypatch.setattr(
        module, "_execute_in_owned_process", lambda *args, **kwargs: _WorkerOutcome(None, False)
    )
    client = private_response_client(lambda: None)

    with pytest.raises(CategoryGraphExtractionError, match="outcome unknown"):
        invoke(client)

    assert client.calls[0]["external_outcome"] == "unknown"
    assert "response_component" not in client.calls[0]
    assert not [row for row in client._execution_records() if row["kind"] == "raw_model_response"]


def test_validation_paths_redact_unknown_response_field_names():
    from src.graph_memory.extraction.bounded_recap_execution import _safe_validation_path

    schema = {"properties": {"observation_nodes": {"type": "array"}}}
    assert _safe_validation_path(
        ["observation_nodes", 0, "PRIVATE_RESPONSE"], schema
    ) == ["observation_nodes", 0, "<unknown>"]


@pytest.mark.parametrize("error_type", ["schema_error", "runtime_error"])
def test_unexpected_local_validator_fault_stops_without_leaking_or_next_call(
    monkeypatch, error_type
):
    from jsonschema.exceptions import SchemaError

    from src.graph_memory.extraction import bounded_recap_execution as module

    raw = '{"observation_nodes": [], "private": "PRIVATE_RESPONSE"}'
    engine = Engine(TextResult(text=raw, observation=deepseek_observation()))
    client = BoundedRecapPassClient(
        RecapExecutionLimits(provider="openrouter", model=DEEPSEEK_MODEL),
        engine_factory=lambda: engine,
    )
    error = (
        SchemaError("synthetic invalid configured schema")
        if error_type == "schema_error"
        else RuntimeError("synthetic validator fault")
    )

    def fail_validator(*args, **kwargs):
        raise error

    monkeypatch.setattr(module, "validate_json_schema", fail_validator)
    with pytest.raises(CategoryGraphExtractionError) as caught:
        invoke(client, DEEPSEEK_MODEL)
    assert caught.value.raw_model_response == raw
    assert client.ledger()["stopped"] is True
    assert client.calls[0]["consumer_failure"] == type(error).__name__
    assert "validation_failure" not in client.calls[0]
    assert "PRIVATE_RESPONSE" not in json.dumps(client.ledger())
    with pytest.raises(CategoryGraphExtractionError):
        invoke(client, DEEPSEEK_MODEL)
    assert len(engine.requests) == 1 and engine.closed == 1


def test_deepseek_requires_credential_without_provider_call(monkeypatch):
    from src.graph_memory.extraction import bounded_recap_execution as module

    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("DUNGEONBUDDY_OPENROUTER", raising=False)
    monkeypatch.setattr(module, "load_dungeonmindbuddy_dotenv", lambda **kwargs: None)
    client = BoundedRecapPassClient(
        RecapExecutionLimits(provider="openrouter", model=DEEPSEEK_MODEL)
    )
    with pytest.raises(CategoryGraphExtractionError):
        invoke(client, DEEPSEEK_MODEL)
    assert client.ledger()["stopped"]
    assert client.calls[0]["consumer_failure"] == "CategoryGraphExtractionError"


@pytest.mark.parametrize(
    "provider,model", [("openrouter", "gpt-6-luna"), ("openai", DEEPSEEK_MODEL)]
)
def test_provider_model_pair_is_caller_selected(provider, model):
    limits = RecapExecutionLimits(provider=provider, model=model)
    assert (limits.provider, limits.model) == (provider, model)


@pytest.mark.parametrize(
    "edge_override,expected_edge_limit",
    [(None, 8192), (16384, 16384), (32768, 32768)],
)
def test_edge_output_allowance_applies_only_to_actual_edge_spec(
    edge_override, expected_edge_limit
):
    from src.graph_memory.extraction.extraction_profile import ExtractionPassSpec

    responses = [
        TextResult(text='{"observation_nodes": []}', observation=deepseek_observation()),
        TextResult(text='{"observation_edges": []}', observation=deepseek_observation()),
        TextResult(text='{"observation_edges": []}', observation=deepseek_observation()),
    ]

    class SequenceEngine:
        def __init__(self):
            self.requests = []

        async def generate_structured(self, request, *, on_attempt_completed=None):
            self.requests.append(request)
            return await _complete_fake_structured_result(
                responses.pop(0), request, on_attempt_completed
            )

        async def aclose(self):
            pass

    engine = SequenceEngine()
    limits = RecapExecutionLimits(
        provider="openrouter",
        model=DEEPSEEK_MODEL,
        edge_max_output_tokens=edge_override,
    )
    client = BoundedRecapPassClient(limits, engine_factory=lambda: engine)
    edge_spec = ExtractionPassSpec(
        pass_id="edge_pass",
        default_node_type=None,
        instruction="Extract relationships",
        progress_label="Extracting relationships",
        kind="edge",
    )

    client.run_pass(
        "actor_pass",
        model_id=DEEPSEEK_MODEL,
        instructions="SYSTEM",
        user_content="ACTORS",
    )
    client.run_pass(
        "edge_pass",
        model_id=DEEPSEEK_MODEL,
        instructions="SYSTEM",
        user_content="EDGES",
    )
    client.run_pass(
        "edge_pass",
        model_id=DEEPSEEK_MODEL,
        instructions="SYSTEM",
        user_content="TYPED_EDGES",
        pass_spec=edge_spec,
    )

    actor_request, untyped_edge_request, edge_request = engine.requests
    assert actor_request.max_output_tokens == 8192
    assert untyped_edge_request.max_output_tokens == 8192
    assert edge_request.max_output_tokens == expected_edge_limit
    for request in engine.requests:
        assert 0 < request.deadline_ms <= 120_000
        assert request.max_transport_retries == 0
        assert request.provider_route.order == ("DeepSeek",)
        assert request.provider_route.allow_fallbacks is False
    assert limits.max_calls == 8
    assert limits.run_deadline_ms == 480_000
    ledger = client.ledger()
    assert ledger["pass_invocation_count"] == 3
    assert ledger["pass_invocation_limit"] == 8
    assert ledger["attempt_counts"]["provider_attempts"] == {
        "total": 3,
        "known_total": 3,
        "complete": True,
    }
    assert "authorization ceiling" in ledger["attempt_counts"]["semantics"]


@pytest.mark.parametrize("invalid", [0, 32769, True, 1.5, "32768"])
def test_edge_output_allowance_rejects_invalid_values(invalid):
    with pytest.raises(ValueError, match="edge_max_output_tokens"):
        RecapExecutionLimits(edge_max_output_tokens=invalid)


def test_general_output_allowance_supports_reasoning_headroom_without_changing_default():
    assert RecapExecutionLimits().max_output_tokens == 8192
    assert RecapExecutionLimits(max_output_tokens=16384).max_output_tokens == 16384
    assert RecapExecutionLimits(max_output_tokens=32768).max_output_tokens == 32768


@pytest.mark.parametrize("invalid", [0, 32769, True, 1.5, "32768"])
def test_general_output_allowance_rejects_invalid_values(invalid):
    with pytest.raises(ValueError, match="max_output_tokens"):
        RecapExecutionLimits(max_output_tokens=invalid)


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
    assert 0 < request.deadline_ms <= 120000
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


@pytest.mark.parametrize(
    "run_deadline_ms,per_call_deadline_ms,elapsed_ms,expected_ms",
    [(480_000, 120_000, 0, 120_000), (480_000, 120_000, 360_000, 120_000),
     (1000, 120_000, 250, 750), (900_000, 240_000, 0, 240_000),
     (900_000, 240_000, 800_000, 100_000)],
)
def test_selected_logical_deadline_reaches_request_and_owned_worker(
    monkeypatch, run_deadline_ms, per_call_deadline_ms, elapsed_ms, expected_ms
):
    from src.graph_memory.extraction import bounded_recap_execution as module

    engine = Engine(
        TextResult(text="{}", observation=observation(input_tokens=0, output_tokens=0))
    )
    clock = [0.0]
    client = BoundedRecapPassClient(
        RecapExecutionLimits(run_deadline_ms=run_deadline_ms, per_call_deadline_ms=per_call_deadline_ms),
        engine_factory=lambda: engine,
        clock=lambda: clock[0],
    )
    worker_deadlines = []
    execute = module._execute_in_owned_process

    def capture_worker_deadline(factory, request, *, deadline, attempt_evidence=None):
        worker_deadlines.append((request["deadline_ms"], deadline))
        return execute(
            factory, request, deadline=deadline, attempt_evidence=attempt_evidence
        )

    monkeypatch.setattr(module, "_execute_in_owned_process", capture_worker_deadline)
    clock[0] = elapsed_ms / 1000
    started = module.time.monotonic()
    invoke(client)

    request = engine.requests[0]
    assert request.deadline_ms == expected_ms
    assert client.limits.run_deadline_ms == run_deadline_ms
    assert len(worker_deadlines) == 1
    worker_request_ms, worker_deadline = worker_deadlines[0]
    assert worker_request_ms == request.deadline_ms
    assert started + expected_ms / 1000 <= worker_deadline + 0.01
    assert worker_deadline <= started + expected_ms / 1000 + 0.01


def test_ge_incomplete_through_one_recap_never_appends_candidate(
    tmp_path, monkeypatch, application_state_dsn,
):
    from tests.test_recap_managed_standing_context import seed_binding
    from apps.live_control_server.services import graph_preview_runner as wrapper
    from apps.live_control_server.services import graph_run_registry as registry
    from graph_memory.ingestion.extraction_run import ExtractionRunStatus

    seed_binding(tmp_path, "managed-fixture-world", "world:synthetic")
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
    source_path = tmp_path / "source.md"
    source_path.write_text("A keeper guards a gate.\n")
    output = tmp_path / "new-output"
    result = wrapper.run_recap_production_extraction(
        repo_root=tmp_path,
        campaign_id="synthetic",
        session_id="session-1",
        source_artifact_id=create_recap_source_artifact(tmp_path,world_id="world:synthetic",campaign_id="synthetic",session_id="session-1",recap_path=source_path).source_artifact_id,
        profile="category_baseline",
        model_id="gpt-6-luna",
        allow_llm=True,
        execution_limits=RecapExecutionLimits(),
        ingest_context=_fixture_ingest_context("synthetic"),
    )
    assert result.failure_kind == "incomplete", result.diagnostics
    stored = registry.get_extraction_run(tmp_path, result.run.run_id)
    assert result.candidate_graph is None and stored.status == ExtractionRunStatus.FAILED
    assert "candidate_graph" not in stored.components
    assert not list(output.rglob("candidate_graph.json"))
    assert len(engine.requests) == 1
    from application_state.ingest.components import get_component_bytes
    ref = stored.components["pass_telemetry"]
    ledger = json.loads(get_component_bytes(run_id=stored.run_id, kind=ref.kind, content_sha256=ref.sha256))
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


@pytest.mark.usefixtures("application_state_dsn")
def test_structured_parsed_object_preserves_fenced_raw_evidence(tmp_path):
    payload = {"observation_nodes": []}
    raw = "```json\n" + json.dumps(payload) + "\n```"
    engine = Engine(TextResult(text=raw, parsed=payload, observation=deepseek_observation()))
    client = BoundedRecapPassClient(
        RecapExecutionLimits(provider="openrouter", model=DEEPSEEK_MODEL),
        engine_factory=lambda: engine,
        request_context_hashes={"synthetic_source": "a" * 64},
    )
    bind_private_client(client)
    result = invoke(client, DEEPSEEK_MODEL)
    assert result["parsed"] == payload
    assert result["raw_text"] == raw
    evidence = private_capture(client, client.calls[0]["response_component"]["sha256"])
    assert evidence["response"]["text"] == raw
    assert client.ledger()["calls"][0]["external_outcome"] == "completed"


def test_structured_parsed_object_is_revalidated_at_buddy_boundary():
    engine = Engine(TextResult(
        text='{"observation_nodes": []}', parsed={"observation_nodes": "invalid"},
        observation=deepseek_observation(),
    ))
    client = BoundedRecapPassClient(
        RecapExecutionLimits(provider="openrouter", model=DEEPSEEK_MODEL),
        engine_factory=lambda: engine,
    )
    with pytest.raises(CategoryGraphExtractionError):
        invoke(client, DEEPSEEK_MODEL)
    assert client.ledger()["calls"][0]["validation_failure"]["kind"] == "schema"


@pytest.mark.parametrize("invalid", [0, -1, True, 1.5, "9"])
def test_profile_budget_requires_positive_integer(invalid):
    with pytest.raises(ValueError, match="max_calls"):
        RecapExecutionLimits(max_calls=invalid)


def test_profile_budget_supports_nine_pass_recap_without_changing_deadlines():
    limits = RecapExecutionLimits(max_calls=9)
    assert limits.max_calls == 9
    assert limits.per_call_deadline_ms == 120000
    assert limits.run_deadline_ms == 480000


def actor_handle_packet(source='Dr. Ari did not enter.\n\nShe waited unless Bea returned.'):
    from src.graph_memory.extraction.source_sentence_evidence import compile_source_sentence_packet
    return compile_source_sentence_packet(source, [
        {'source_span_ref_id': 'span:a', 'text': source.split('\n\n')[0], 'line_start': 1},
        {'source_span_ref_id': 'span:b', 'text': source.split('\n\n')[1], 'line_start': 3},
    ])


def actor_handle_response(ids=None):
    return {'observation_nodes': [{
        'node_id': 'actor:ari', 'label': 'Ari', 'node_type': 'character',
        'description': 'Ari stayed outside unless Bea returned.', 'importance': 'medium',
        'evidence_refs': [{'source_quote_ids': ids or ['Q001', 'Q002']}],
    }]}


@pytest.mark.usefixtures("application_state_dsn")
@pytest.mark.parametrize("pass_name", ["actor_pass", "location_pass", "collective_pass", "object_pass", "thread_pass"])
def test_node_handle_wire_materializes_canonical_evidence_and_retains_both(tmp_path, pass_name):
    from src.graph_memory.extraction.category_candidate_graph_schema import category_pass_text_format_for_spec
    from src.graph_memory.extraction.recap_extraction_profile import RECAP_EXTRACTION_PROFILE
    spec = next(p for p in RECAP_EXTRACTION_PROFILE.node_passes if p.pass_id == pass_name)
    from jsonschema import validate
    packet = actor_handle_packet()
    raw = actor_handle_response()
    raw["observation_nodes"][0]["node_type"] = spec.default_node_type
    if pass_name in {"object_pass", "thread_pass"}:
        raw.update(ignored_items=[], deferred_items=[])
    engine = Engine(TextResult(text=json.dumps(raw), parsed=raw, observation=deepseek_observation()))
    client = BoundedRecapPassClient(
        RecapExecutionLimits(provider='openrouter', model=DEEPSEEK_MODEL),
        engine_factory=lambda: engine,
        request_context_hashes={'source_content': packet.source_sha256},
    )
    bind_private_client(client, source_sha256=packet.source_sha256)
    result = client.run_pass(pass_name, model_id=DEEPSEEK_MODEL,
                             instructions='Extract nodes', user_content='host rendered source', pass_spec=spec,
                             source_evidence_packet=packet)
    schema = engine.requests[0].json_schema
    ref_schema = schema['properties']['observation_nodes']['items']['properties']['evidence_refs']['items']
    assert ref_schema['properties']['source_quote_ids']['items']['enum'] == ['Q001', 'Q002']
    assert 'source_span_ref_id' not in ref_schema['properties']
    validate(result['parsed'], category_pass_text_format_for_spec(spec)['format']['schema'])
    assert result['parsed']['observation_nodes'][0]['evidence_refs'] == [
        {'source_span_ref_id': 'span:a', 'anchor_quotes': ['Dr. Ari did not enter.']},
        {'source_span_ref_id': 'span:b', 'anchor_quotes': ['She waited unless Bea returned.']},
    ]
    assert result['raw_text'] == json.dumps(raw)
    call = client.calls[0]
    raw_evidence = private_capture(client, call['response_component']['sha256'])
    normalized = private_capture(client, call['normalized_component']['sha256'])
    assert json.loads(raw_evidence['response']['text']) == raw
    normalized_payload = json.loads(normalized['response']['text'])
    assert normalized_payload['parsed'] == result['parsed']
    assert len(normalized_payload['source_units']) == 2
    assert raw_evidence['context_sha256']['node_source_packet'] == packet.packet_id
    assert normalized['context_sha256'] == raw_evidence['context_sha256']


@pytest.mark.parametrize('ids', [['Q999'], ['Q001', 'Q001']])
def test_actor_invalid_handles_reject_whole_pass(ids):
    packet = actor_handle_packet()
    raw = actor_handle_response(ids)
    engine = Engine(TextResult(text=json.dumps(raw), parsed=raw, observation=deepseek_observation()))
    client = BoundedRecapPassClient(
        RecapExecutionLimits(provider='openrouter', model=DEEPSEEK_MODEL), engine_factory=lambda: engine,
    )
    with pytest.raises(CategoryGraphExtractionError):
        client.run_pass('actor_pass', model_id=DEEPSEEK_MODEL, instructions='Extract',
                        user_content='source', source_evidence_packet=packet)
    assert client.ledger()['stopped'] is True


def test_actor_packet_swap_rejected_before_provider_call():
    packet = actor_handle_packet()
    engine = Engine(None)
    client = BoundedRecapPassClient(
        RecapExecutionLimits(provider='openrouter', model=DEEPSEEK_MODEL), engine_factory=lambda: engine,
        request_context_hashes={'source_content': 'f' * 64},
    )
    with pytest.raises(CategoryGraphExtractionError, match='does not match run source'):
        client.run_pass('actor_pass', model_id=DEEPSEEK_MODEL, instructions='Extract',
                        user_content='source', source_evidence_packet=packet)
    assert engine.requests == [] and client.calls == []


def test_real_recap_producer_supplies_packet_to_ge_and_receives_canonical_result():
    from src.graph_memory.extraction.category_candidate_graph_extractor import (
        CategoryGraphExtractionOptions, extract_category_candidate_graph,
    )
    from src.graph_memory.extraction.recap_extraction_profile import RECAP_EXTRACTION_PROFILE
    packet = actor_handle_packet()

    class PipelineEngine(Engine):
        async def generate_structured(self, request, *, on_attempt_completed=None):
            self.requests.append(request)
            payload = (
                actor_handle_response() if request.schema_name == 'category_graph_actor_pass'
                else {key: [] for key in request.json_schema['required']}
            )
            return await _complete_fake_structured_result(
                TextResult(text=json.dumps(payload), parsed=payload, observation=deepseek_observation()),
                request, on_attempt_completed,
            )
    engine = PipelineEngine(None)
    client = BoundedRecapPassClient(
        RecapExecutionLimits(provider='openrouter', model=DEEPSEEK_MODEL, max_calls=16),
        engine_factory=lambda: engine,
    )
    result = extract_category_candidate_graph(CategoryGraphExtractionOptions(
        campaign_id='longmont-c2', session_id='session-1', session_number=1,
        source_text=packet.source, model_id=DEEPSEEK_MODEL,
        source_artifact_id='artifact:synthetic', source_ref_id='artifact:synthetic:text',
        source_span_index={'spans': [
            {'kind': 'paragraph', 'source_span_ref_id': 'span:a', 'line_start': 1, 'line_end': 1},
            {'kind': 'paragraph', 'source_span_ref_id': 'span:b', 'line_start': 3, 'line_end': 3},
        ]}, profile=RECAP_EXTRACTION_PROFILE,
    ), client=client)
    actor = engine.requests[0]
    assert '### Q001\nDr. Ari did not enter.' in actor.user_prompt
    assert '### Q002\nShe waited unless Bea returned.' in actor.user_prompt
    assert 'source_quote_ids' in actor.user_prompt
    for request in engine.requests[:5]:
        refs_schema = request.json_schema['properties']['observation_nodes']['items']['properties']['evidence_refs']['items']
        assert refs_schema['properties']['source_quote_ids']['items']['enum'] == ['Q001', 'Q002']
        assert '### Q001\nDr. Ari did not enter.' in request.user_prompt
    for request in engine.requests[5:]:
        assert 'source_quote_ids' not in json.dumps(request.json_schema)
    refs = result.pass_outputs['actor_pass']['observation_nodes'][0]['evidence_refs']
    assert refs[0]['anchor_quotes'] == ['Dr. Ari did not enter.']
    assert refs[1]['source_span_ref_id'] == 'span:b'
    assert client.calls[0]['source_evidence_context']['node_source_packet'] == packet.packet_id
    assert result.candidate_graph['nodes']


@pytest.mark.usefixtures("application_state_dsn")
def test_failed_normalized_evidence_persistence_preserves_wire_and_stops(tmp_path, monkeypatch):
    packet = actor_handle_packet()
    raw = actor_handle_response()
    engine = Engine(TextResult(text=json.dumps(raw), parsed=raw, observation=deepseek_observation()))
    client = BoundedRecapPassClient(
        RecapExecutionLimits(provider='openrouter', model=DEEPSEEK_MODEL), engine_factory=lambda: engine,
        request_context_hashes={'source_content': packet.source_sha256},
    )
    from application_state.ingest import components
    bind_private_client(client, source_sha256=packet.source_sha256)
    writer = components.persist_execution_event

    def fail_normalized(**kwargs):
        if json.loads(kwargs["payload"])["capture_id"].startswith("normalized:"):
            raise OSError("synthetic retention failure")
        return writer(**kwargs)

    monkeypatch.setattr(components, "persist_execution_event", fail_normalized)
    with pytest.raises(CategoryGraphExtractionError):
        client.run_pass('actor_pass', model_id=DEEPSEEK_MODEL, instructions='Extract',
                        user_content='source', source_evidence_packet=packet)
    call = client.calls[0]
    assert private_capture(client, call['response_component']['sha256'])['response']['text'] == json.dumps(raw)
    assert 'normalized_component' not in call
    assert client.retention_failed
    assert client.ledger()['stopped'] is True


def test_supplemental_context_reaches_provider_without_changing_recap_source():
    engine=Engine(TextResult(text='{"observation_nodes": []}',observation=observation()))
    client=BoundedRecapPassClient(RecapExecutionLimits(),engine_factory=lambda:engine,supplemental_context='Separately attributed closing reflections: players want combat.')
    invoke(client)
    assert engine.requests[0].user_prompt.startswith('PRIVATE_SOURCE\n\n')
    assert 'Separately attributed closing reflections' in engine.requests[0].user_prompt


@pytest.mark.parametrize('provider,model', [
    ('openai', 'gpt-6.1-sol'), ('openai', 'gpt-6-luna'),
    ('vercel', 'moonshotai/kimi-k3.1-pro'), ('vercel', 'anthropic/claude-haiku-5.5'),
    ('vercel', 'google/gemini-3.8-flash'), ('vercel', 'anthropic/claude-sonnet-5.5'),
    ('openrouter', 'vendor/not-a-catalog-entry'),
])
def test_explicit_targets_reach_ge_without_deepseek_settings(provider, model):
    payload = {'observation_nodes': []}
    obs = observation().model_copy(update={'provider': provider, 'requested_model': model,
                              'resolved_model': model, 'response_model': 'actual/model-alias'})
    engine = Engine(TextResult(text=json.dumps(payload), observation=obs))
    client = BoundedRecapPassClient(RecapExecutionLimits(provider=provider, model=model,
                                      reasoning_effort='low'), engine_factory=lambda: engine)
    invoke(client, model)
    request = engine.requests[0]
    assert (request.provider, request.model, request.reasoning_effort) == (provider, model, 'low')
    assert request.provider_route is None
    assert request.system_prompt == 'PRIVATE_PROMPT'
    assert request.user_prompt == 'PRIVATE_SOURCE'
    assert request.json_schema and request.schema_name == 'category_graph_actor_pass'
    assert request.max_transport_retries == 0
    assert client.calls[0]['reasoning_effort'] == 'low'
    assert client.calls[0]['observation']['response_model'] == 'actual/model-alias'
    assert engine.closed == 1


@pytest.mark.parametrize('provider,model,effort', [
    ('unknown', 'model', None), ('openai', '', None), ('vercel', '   ', None),
    ('openrouter', None, None), ('openai', 'model', ''), ('openai', 'model', 1),
])
def test_invalid_explicit_target_fails_before_engine(provider, model, effort):
    with pytest.raises(ValueError):
        RecapExecutionLimits(provider=provider, model=model, reasoning_effort=effort)


@pytest.mark.parametrize('field,value', [('provider','vercel'), ('requested_model','other'),
                                       ('resolved_model','other')])
def test_completed_receipt_must_match_selected_execution_target(field, value):
    obs = observation().model_copy(update={field: value})
    engine = Engine(TextResult(text='{"observation_nodes":[]}', observation=obs))
    client = BoundedRecapPassClient(RecapExecutionLimits(), engine_factory=lambda: engine)
    with pytest.raises(CategoryGraphExtractionError, match='bounded structured'):
        invoke(client)
    assert client.ledger()['stopped']
    assert engine.closed == 1


def test_reasoning_deadline_headroom_preserves_generic_defaults():
    defaults = RecapExecutionLimits()
    assert defaults.per_call_deadline_ms == 120000
    assert defaults.run_deadline_ms == 480000
    expanded = RecapExecutionLimits(per_call_deadline_ms=240000, run_deadline_ms=900000)
    assert expanded.per_call_deadline_ms == 240000
    assert expanded.run_deadline_ms == 900000


@pytest.mark.parametrize("field,value", [
    ("per_call_deadline_ms", 240001), ("run_deadline_ms", 900001),
    ("per_call_deadline_ms", True), ("run_deadline_ms", 0),
])
def test_reasoning_deadline_headroom_rejects_invalid_limits(field, value):
    with pytest.raises(ValueError, match=field):
        RecapExecutionLimits(**{field: value})


def test_advertised_node_ids_require_retention_and_are_local_to_each_client(monkeypatch):
    from src.graph_memory.extraction.compact_evidence_context import CompactEvidenceContext
    context = CompactEvidenceContext([
        {'source_span_ref_id': 'paragraph:45-45', 'text': 'A ferry arrived.', 'line_start': 45, 'line_end': 45},
    ], source_sha256='a' * 64).record()
    first = BoundedRecapPassClient(RecapExecutionLimits())
    first.execution_binding = {'source_sha256': 'a' * 64}
    captures = []
    monkeypatch.setattr(first, '_persist_capture', lambda kind, record: captures.append(record))
    first.retain_compact_evidence_context(context)
    assert first._advertised_node_span_ids == ('paragraph:45-45',)
    assert captures[0]['context'] == context
    second = BoundedRecapPassClient(RecapExecutionLimits())
    assert second._advertised_node_span_ids is None
    second.execution_binding = first.execution_binding.copy()
    def fail(*args):
        raise OSError('synthetic capture failure')
    monkeypatch.setattr(second, '_persist_capture', fail)
    with pytest.raises(OSError):
        second.retain_compact_evidence_context(context)
    assert second._advertised_node_span_ids is None
    with pytest.raises(ValueError):
        first.retain_compact_evidence_context(context)


def test_empty_advertised_node_source_is_retained_and_refused_before_dispatch(monkeypatch):
    engine = Engine(None)
    client = BoundedRecapPassClient(RecapExecutionLimits(), engine_factory=lambda: engine)
    client.execution_binding = {'source_sha256': 'a' * 64}
    captures = []
    monkeypatch.setattr(client, '_persist_capture', lambda kind, record: captures.append(record))
    empty = {'schema': 'dmb_compact_recap_evidence_context_v1', 'source_sha256': 'a' * 64, 'entries': []}
    with pytest.raises(ValueError, match='advertised source paragraphs'):
        client.retain_compact_evidence_context(empty)
    assert captures[0]['node_evidence_status'] == 'no_advertised_paragraphs'
    assert client.calls == [] and engine.requests == []
    assert client._advertised_node_span_ids is None
    with pytest.raises(CategoryGraphExtractionError):
        invoke(client)
    assert engine.requests == []


@pytest.mark.usefixtures('application_state_dsn')
def test_advertised_node_ids_reach_real_ge_conformance_and_retain_invalid_attempt():
    from generationengine import GenerationClient
    from generationengine.providers.openrouter_text import OpenRouterTextProvider
    from src.graph_memory.extraction.compact_evidence_context import CompactEvidenceContext
    from src.graph_memory.extraction.recap_extraction_profile import RECAP_EXTRACTION_PROFILE
    source = 'A ferry arrived.'
    import hashlib
    context = CompactEvidenceContext([
        {'source_span_ref_id': 'paragraph:45-45', 'text': source, 'line_start': 45, 'line_end': 45},
    ], source_sha256=hashlib.sha256(source.encode()).hexdigest())
    def payload(ref):
        return {'observation_nodes': [{
            'node_id': 'ferry', 'label': 'Ferry', 'node_type': 'location',
            'description': source, 'importance': 'low',
            'evidence_refs': [{'source_span_ref_id': ref, 'anchor_quotes': [source]}],
        }]}
    responses = [payload('paragraph:45'), payload('paragraph:45-45')]
    class Completions:
        def __init__(self):
            self.calls = []
        async def create(self, **kwargs):
            self.calls.append(kwargs)
            return SimpleNamespace(
                id=f'synthetic-{len(self.calls)}', _request_id='synthetic', model=DEEPSEEK_MODEL,
                choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(responses.pop(0)), refusal=None), finish_reason='stop')],
                usage=None,
            )
    completions = Completions()
    class Client:
        chat = SimpleNamespace(completions=completions)
        async def close(self):
            pass
    wire_requests = []
    class RecordingProvider(OpenRouterTextProvider):
        async def generate(self, call):
            wire_requests.append(call)
            return await super().generate(call)
    engine = GenerationClient(text_providers={'openrouter': RecordingProvider(client=Client())})
    client = BoundedRecapPassClient(
        RecapExecutionLimits(provider='openrouter', model=DEEPSEEK_MODEL), engine_factory=lambda: engine,
    )
    bind_private_client(client, source_sha256=context.source_sha256)
    client.retain_compact_evidence_context(context.record())
    spec = next(p for p in RECAP_EXTRACTION_PROFILE.node_passes if p.pass_id == 'location_pass')
    result = client.run_pass('location_pass', model_id=DEEPSEEK_MODEL, instructions='Extract', user_content=source, pass_spec=spec)
    assert result['parsed'] == payload('paragraph:45-45')
    assert len(completions.calls) == 2
    ledger = client.ledger()
    assert ledger['attempt_counts']['provider_attempts']['total'] == 2
    assert ledger['attempt_counts']['conformance_retries']['total'] == 1
    records = client._execution_records()
    attempts = sorted((row['record'] for row in records if row['record']['schema'] == 'dmb_private_recap_attempt_response_v1'), key=lambda r: r['ge_attempt']['ordinal'])
    assert [json.loads(r['response']['text']) for r in attempts] == [payload('paragraph:45'), payload('paragraph:45-45')]
    wire = wire_requests[0].json_schema
    assert wire['properties']['observation_nodes']['items']['properties']['evidence_refs']['items']['properties']['source_span_ref_id']['enum'] == ['paragraph:45-45']


@pytest.mark.parametrize("cleanup_confirmed", [True, False])
def test_explicit_worker_no_dispatch_and_cleanup_unknown_are_distinct(monkeypatch, cleanup_confirmed):
    from src.graph_memory.extraction import bounded_recap_execution as module
    from src.graph_memory.extraction._recap_inference_worker import _WorkerOutcome
    monkeypatch.setattr(module, "_execute_in_owned_process", lambda *a, **kw:
                        _WorkerOutcome({"kind": "not_started"}, False, cleanup_confirmed))
    client = BoundedRecapPassClient(RecapExecutionLimits())
    with pytest.raises(CategoryGraphExtractionError):
        invoke(client)
    entry = client.calls[0]
    assert entry["external_outcome"] == "not_started"
    assert entry["observation"] is None
    assert client.ledger()["stopped"]
    if not cleanup_confirmed:
        assert entry["worker_cleanup"] == "unconfirmed"


@pytest.mark.parametrize("cleanup_confirmed, late, message", [
    (True, True, "after execution deadline"),
    (False, False, "cleanup unconfirmed"),
])
def test_authentic_result_is_retained_but_unsafe_candidate_is_rejected(
    monkeypatch, cleanup_confirmed, late, message,
):
    from src.graph_memory.extraction import bounded_recap_execution as module
    from src.graph_memory.extraction._recap_inference_worker import _WorkerOutcome
    result = TextResult(text='{"observation_nodes": []}', observation=InferenceObservation(
        provider="openai", requested_model="gpt-6-luna", resolved_model="gpt-6-luna",
        response_model="gpt-6-luna", provider_attempt_count=1, latency_ms=12,
        retry_count=0, state=ObservationState.COMPLETED,
    ))
    monkeypatch.setattr(module, "_execute_in_owned_process", lambda *a, **kw:
                        _WorkerOutcome({"kind": "result", "result": result.model_dump(mode="json")},
                                       False, cleanup_confirmed, late))
    client = BoundedRecapPassClient(RecapExecutionLimits())
    with pytest.raises(CategoryGraphExtractionError, match=message):
        invoke(client)
    entry = client.calls[0]
    assert entry["external_outcome"] == "completed"
    assert entry["observation"]["provider_attempt_count"] == 1
    assert entry["consumer_failure"] == ("DeadlineExceeded" if late else "CleanupUnconfirmed")
    assert client.ledger()["stopped"]


@pytest.mark.parametrize("pass_name", ["beat_pass", "edge_pass", "encounter_pass"])
def test_source_handle_wire_rejects_non_node_pass_before_provider_dispatch(pass_name):
    packet = actor_handle_packet()
    engine = Engine(None)
    client = BoundedRecapPassClient(
        RecapExecutionLimits(provider='openrouter', model=DEEPSEEK_MODEL),
        engine_factory=lambda: engine,
    )
    with pytest.raises((CategoryGraphExtractionError, ValueError)):
        client.run_pass(pass_name, model_id=DEEPSEEK_MODEL, instructions='Extract',
                        user_content='source', source_evidence_packet=packet)
    assert engine.requests == []
