import json
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
from src.graph_memory.extraction.category_candidate_graph_extractor import (
    CategoryGraphExtractionError,
)


@pytest.fixture(autouse=True)
def semantic_engine_seam(monkeypatch):
    """Use explicit structured fake engines; process tests live separately."""
    from src.graph_memory.extraction import bounded_recap_execution as module
    from src.graph_memory.extraction._recap_inference_worker import _WorkerOutcome

    def execute(factory, request, *, deadline, attempt_evidence=None):
        from generationengine.types import TextRequest
        from src.graph_memory.extraction.bounded_recap_execution import (
            _write_private_response_evidence,
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
                        event_payload = event.model_dump(mode="json")
                        _write_private_response_evidence(
                            Path(attempt_evidence["directory"]),
                            ordinal=attempt_evidence["pass_ordinal"],
                            pass_name=attempt_evidence["pass_name"],
                            request=request,
                            context_hashes=attempt_evidence["context_hashes"],
                            raw_observation=event_payload,
                            response_text=event.text,
                            attempt_event=event_payload,
                        )

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


def private_response_client(engine_factory, run_dir, *, limits=None):
    run_dir.mkdir(parents=True, exist_ok=True)
    return BoundedRecapPassClient(
        limits or RecapExecutionLimits(),
        engine_factory=engine_factory,
        response_artifact_dir=run_dir / ".private" / "pass_responses",
        request_context_hashes={
            "normalized_source": "a" * 64,
            "settled_identity_context": "b" * 64,
        },
    )


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
    run_dir = tmp_path / "synthetic-run"
    client = private_response_client(
        lambda: engine,
        run_dir,
        limits=RecapExecutionLimits(provider="openrouter", model=DEEPSEEK_MODEL),
    )
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

    response_path = (
        run_dir / ".private" / "pass_responses" / "01-actor_pass-attempt-01.json"
    )
    envelope = json.loads(response_path.read_text(encoding="utf-8"))
    assert envelope["capture_state"] == "unvalidated_snapshot"
    assert envelope["schema"] == "dmb_private_recap_attempt_response_v1"
    assert envelope["ge_attempt"]["ordinal"] == 1
    assert envelope["ge_attempt"]["response_status"] == "returned"
    assert envelope["response"]["text"] == raw
    assert response_path.stat().st_mode & 0o777 == 0o600
    with pytest.raises(CategoryGraphExtractionError):
        invoke(client, DEEPSEEK_MODEL)
    assert len(engine.requests) == 1


@pytest.mark.parametrize(
    "text,changes",
    [
        ('{"observation_nodes": "wrong"}', {}),
        ('{"observation_nodes": []}', {"provider": "other"}),
        ('{"observation_nodes": []}', {"response_model": "other"}),
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


def test_private_response_evidence_captures_success_before_consumer_use(tmp_path):
    import hashlib
    import os
    import stat

    raw = '{"observation_nodes": []}'
    engine = Engine(TextResult(text=raw, observation=observation()))
    client = private_response_client(lambda: engine, tmp_path / "run")

    result = invoke(client)

    artifact_path = Path(client.calls[0]["response_artifact_path"])
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
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
    assert artifact["context_sha256"] == {
        "normalized_source": "a" * 64,
        "settled_identity_context": "b" * 64,
    }
    assert artifact["response"]["text"] == raw
    assert artifact["response"]["utf8_bytes"] == len(raw.encode())
    assert artifact["response"]["sha256"] == hashlib.sha256(raw.encode()).hexdigest()
    assert artifact["ge_observation"]["provider_response_id"] == "response"
    assert "provider_request_id" not in artifact["ge_observation"]
    assert "PRIVATE_PROMPT" not in json.dumps(artifact)
    assert "PRIVATE_SOURCE" not in json.dumps(artifact)
    assert "PRIVATE" not in json.dumps(client.ledger())
    assert client.calls[0]["response_artifact_sha256"] == hashlib.sha256(
        artifact_path.read_bytes()
    ).hexdigest()
    assert stat.S_IMODE(os.stat(tmp_path / "run" / ".private").st_mode) == 0o700
    assert stat.S_IMODE(
        os.stat(tmp_path / "run" / ".private" / "pass_responses").st_mode
    ) == 0o700
    assert stat.S_IMODE(os.stat(artifact_path).st_mode) == 0o600


@pytest.mark.parametrize(
    "raw,expected_kind",
    [
        ('{"observation_nodes":', "invalid_json"),
        ('{"observation_nodes": "wrong"}', "schema"),
    ],
)
def test_private_response_evidence_precedes_json_and_schema_validation(
    tmp_path, raw, expected_kind
):
    engine = Engine(TextResult(text=raw, observation=deepseek_observation()))
    client = private_response_client(
        lambda: engine,
        tmp_path / "run",
        limits=RecapExecutionLimits(provider="openrouter", model=DEEPSEEK_MODEL),
    )

    with pytest.raises(CategoryGraphExtractionError):
        invoke(client, DEEPSEEK_MODEL)

    artifact_path = Path(client.calls[0]["response_artifact_path"])
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert artifact["capture_state"] == "unvalidated_snapshot"
    assert artifact["response"]["text"] == raw
    assert client.calls[0]["validation_failure"]["kind"] == expected_kind
    assert client.calls[0]["response_artifact_sha256"]
    assert "PRIVATE_PROMPT" not in json.dumps(artifact)
    assert "PRIVATE_SOURCE" not in json.dumps(artifact)


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

    client = private_response_client(SequenceEngine, tmp_path / "run")
    client.run_pass(
        "actor_pass", model_id="gpt-6-luna", instructions="SYSTEM", user_content="USER"
    )
    with pytest.raises(CategoryGraphExtractionError):
        client.run_pass(
            "location_pass", model_id="gpt-6-luna", instructions="SYSTEM", user_content="USER"
        )

    evidence_dir = tmp_path / "run" / ".private" / "pass_responses"
    assert sorted(path.name for path in evidence_dir.glob("*.json")) == [
        "01-actor_pass-attempt-01.json",
        "02-location_pass-attempt-01.json",
    ]
    assert client.calls[0]["response_artifact_sha256"]
    assert client.calls[1]["response_artifact_sha256"]


def test_private_response_evidence_is_atomic_and_never_overwrites(tmp_path):
    engine = Engine(TextResult(text='{"observation_nodes": []}', observation=observation()))
    run_dir = tmp_path / "run"
    first = private_response_client(lambda: engine, run_dir)
    invoke(first)
    artifact_path = Path(first.calls[0]["response_artifact_path"])
    original = artifact_path.read_bytes()

    known_response = '{"observation_nodes": []}'
    second_engine = Engine(
        TextResult(
            text=known_response,
            observation=observation(input_tokens=7, output_tokens=3),
        )
    )
    second = private_response_client(lambda: second_engine, run_dir)
    with pytest.raises(
        CategoryGraphExtractionError,
        match="ATTEMPT_EVIDENCE_PERSISTENCE_FAILED",
    ) as caught:
        invoke(second)

    assert caught.value.raw_model_response is None
    assert artifact_path.read_bytes() == original
    assert not list((run_dir / ".private" / "pass_responses").glob("*.pending"))
    assert "response_artifact_path" not in second.calls[0]
    assert second.calls[0]["consumer_failure"] == "AttemptEvidencePersistenceFailed"
    assert second.calls[0]["failure_code"] == "ATTEMPT_EVIDENCE_PERSISTENCE_FAILED"
    assert second.calls[0]["observation"]["state"] == "failed"
    assert second.calls[0]["observation"]["input_tokens"] == 7
    assert second.calls[0]["observation"]["output_tokens"] == 3
    assert second.calls[0]["observation"]["provider_response_id"] == "response"
    assert known_response not in json.dumps(second.ledger())
    assert "PRIVATE_PROMPT" not in json.dumps(second.ledger())
    assert "PRIVATE_SOURCE" not in json.dumps(second.ledger())


def test_unknown_worker_receipt_does_not_create_private_response(tmp_path, monkeypatch):
    from src.graph_memory.extraction import bounded_recap_execution as module
    from src.graph_memory.extraction._recap_inference_worker import _WorkerOutcome

    monkeypatch.setattr(
        module, "_execute_in_owned_process", lambda *args, **kwargs: _WorkerOutcome(None, False)
    )
    client = private_response_client(lambda: None, tmp_path / "run")

    with pytest.raises(CategoryGraphExtractionError, match="outcome unknown"):
        invoke(client)

    assert client.calls[0]["external_outcome"] == "unknown"
    assert "response_artifact_path" not in client.calls[0]
    assert not (tmp_path / "run" / ".private").exists()


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
def test_provider_model_pair_is_fixed(provider, model):
    with pytest.raises(ValueError):
        RecapExecutionLimits(provider=provider, model=model)


@pytest.mark.parametrize(
    "edge_override,expected_edge_limit",
    [(None, 8192), (16384, 16384)],
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


@pytest.mark.parametrize("invalid", [0, 16385, True, 1.5, "16384"])
def test_edge_output_allowance_rejects_invalid_values(invalid):
    with pytest.raises(ValueError, match="edge_max_output_tokens"):
        RecapExecutionLimits(edge_max_output_tokens=invalid)


def test_general_output_allowance_remains_capped_at_8192():
    with pytest.raises(ValueError, match="max_output_tokens"):
        RecapExecutionLimits(max_output_tokens=8193)


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
    "run_deadline_ms,elapsed_ms,expected_ms",
    [(480_000, 0, 120_000), (480_000, 360_000, 120_000), (1000, 250, 750)],
)
def test_selected_logical_deadline_reaches_request_and_owned_worker(
    monkeypatch, run_deadline_ms, elapsed_ms, expected_ms
):
    from src.graph_memory.extraction import bounded_recap_execution as module

    engine = Engine(
        TextResult(text="{}", observation=observation(input_tokens=0, output_tokens=0))
    )
    clock = [0.0]
    client = BoundedRecapPassClient(
        RecapExecutionLimits(run_deadline_ms=run_deadline_ms),
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


def test_structured_parsed_object_preserves_fenced_raw_evidence(tmp_path):
    payload = {"observation_nodes": []}
    raw = "```json\n" + json.dumps(payload) + "\n```"
    engine = Engine(TextResult(text=raw, parsed=payload, observation=deepseek_observation()))
    client = BoundedRecapPassClient(
        RecapExecutionLimits(provider="openrouter", model=DEEPSEEK_MODEL),
        engine_factory=lambda: engine, response_artifact_dir=tmp_path,
        request_context_hashes={"synthetic_source": "a" * 64},
    )
    result = invoke(client, DEEPSEEK_MODEL)
    assert result["parsed"] == payload
    assert result["raw_text"] == raw
    evidence = json.loads(next(tmp_path.glob("*.json")).read_text())
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
