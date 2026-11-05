"""Ordinary recap GE route retains required evidence through real APP owners."""

import json
from pathlib import Path

import pytest
from generationengine.types import TextResult

from apps.live_control_server.services import graph_preview_runner as service
from graph_memory.ingestion.native_recap_source import SourceScope
from graph_memory.ingestion.extraction_run import ExtractionRunStatus
from tests.test_bounded_recap_execution import (
    _complete_fake_structured_result,
    deepseek_observation,
    semantic_engine_seam,  # noqa: F401
)


class SchemaEngine:
    def __init__(self):
        self.requests = []
        self.invalid = False

    async def generate_structured(self, request, *, on_attempt_completed=None):
        self.requests.append(request)
        payload = {name: [] for name in request.json_schema["required"]}
        result = TextResult(
            text="not-json" if self.invalid else json.dumps(payload),
            parsed=None if self.invalid else payload,
            observation=deepseek_observation(input_tokens=10, output_tokens=3),
        )
        return await _complete_fake_structured_result(result, request, on_attempt_completed)

    async def aclose(self):
        pass


@pytest.fixture
def ordinary(monkeypatch, tmp_path, application_state_dsn):
    from tests.test_recap_managed_standing_context import seed_binding
    from apps.live_control_server.services.source_artifact_registry import create_recap_source_artifact
    from src.graph_memory.extraction import bounded_recap_execution as adapter
    import httpx

    monkeypatch.setenv("DMB_ARTIFACT_DATA_ROOT", str(tmp_path))
    seed_binding(tmp_path, "managed-fixture-world", "world:synthetic")
    artifact = create_recap_source_artifact(
        tmp_path, world_id="world:synthetic", campaign_id="synthetic",
        session_id="session-1", recap_text="Ari guarded the gate.\n",
    )
    monkeypatch.setattr(
        "apps.live_control_server.services.known_character_context.read_known_character_catalog",
        lambda *args: {"status": "no_native_head", "entities": [],
                       "native_pin": {"native_world_id": "world:synthetic", "binding_version": 1}},
    )
    engine = SchemaEngine()
    monkeypatch.setattr(adapter, "_default_engine_for", lambda provider: engine)
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", lambda *_: pytest.fail("Provider HTTP forbidden"))
    return tmp_path, engine, artifact


def invoke(ordinary, **kwargs):
    root, _, artifact = ordinary
    return service.run_recap_production_extraction(
        repo_root=root, campaign_id="synthetic", session_id="session-1",
        source_artifact_id=artifact.source_artifact_id, allow_llm=True,
        ingest_context=SourceScope(
            managed_world_id="managed-fixture-world", native_world_id="world:synthetic",
            binding_version=1, campaign_id="synthetic",
        ), **kwargs,
    )


def component(result, kind):
    from application_state.ingest.components import get_component_bytes
    ref = result.run.components[kind]
    return json.loads(get_component_bytes(
        run_id=result.run.run_id, kind=kind, content_sha256=ref.sha256,
    ))


def test_default_ge_route_and_private_evidence(ordinary, monkeypatch):
    root, engine, artifact = ordinary
    original_open = Path.open

    def deny_persistent_output(path, mode="r", *args, **kwargs):
        if any(flag in mode for flag in "wax+") and path.is_relative_to(root):
            raise OSError("persistent extraction output unavailable")
        return original_open(path, mode, *args, **kwargs)

    with monkeypatch.context() as guard:
        guard.setattr(Path, "open", deny_persistent_output)
        result = invoke(ordinary)
    assert result.run.status == ExtractionRunStatus.REVIEWABLE, result.diagnostics
    assert len(engine.requests) == 7
    for request in engine.requests:
        assert (request.provider, request.model) == ("openrouter", service.DEEPSEEK_MODEL)
        assert request.provider_route.order == ("DeepSeek",)
        assert request.provider_route.allow_fallbacks is False
        assert request.max_transport_retries == 0
        assert request.reasoning_effort == "low"
    ledger = component(result, "pass_telemetry")
    assert ledger["run_id"] == result.run.run_id
    assert ledger["source_sha256"] == artifact.content_sha256
    assert ledger["attempt_counts"]["provider_attempts"]["total"] == 7
    assert ledger["acknowledged_response_count"] == 7
    assert all(call["reasoning_effort"] == "low" for call in ledger["calls"])
    bundle = component(result, "raw_model_response")
    events = bundle["execution_evidence"]["records"]
    wire = [row["envelope"] for row in events if "ge_attempt" in row["envelope"]]
    assert len(wire) == 7
    assert all(row["execution_binding"] == ledger["binding"] for row in wire)
    assert all(row["context_sha256"]["source_content"] == artifact.content_sha256 for row in wire)
    assert any(row["envelope"]["capture_id"].startswith("normalized:") for row in events)
    assert not (root / "out").exists()


def test_direct_process_without_model_override_uses_default_ge(ordinary):
    from apps.live_control_server.services.recap_graph_preview_ingest import extract_recap
    root, engine, _ = ordinary
    context = SourceScope(managed_world_id="managed-fixture-world", native_world_id="world:synthetic", binding_version=1, campaign_id="synthetic")
    result = extract_recap(repo_root=root, campaign_id="synthetic", session=1,
                          recap_text="Ari guarded the gate.\n", ingest_context=context)
    assert result["status"] == "candidate_validation_ready"
    assert len(engine.requests) == 7
    assert all(request.model == service.DEEPSEEK_MODEL for request in engine.requests)
    assert all(request.reasoning_effort == "low" for request in engine.requests)


@pytest.mark.parametrize("model", ["gpt-5.4-mini", "gpt-6-luna", "unknown"])
def test_model_override_fails_before_output_or_inference(ordinary, model):
    root, engine, _ = ordinary
    with pytest.raises(ValueError, match="configured DeepSeek"):
        invoke(ordinary, model_id=model)
    assert not engine.requests and not (root / "out").exists()


def test_failed_returned_response_is_retained_without_retry(ordinary):
    _, engine, _ = ordinary
    engine.invalid = True
    result = invoke(ordinary)
    assert result.run.status == ExtractionRunStatus.FAILED
    assert "candidate_graph" not in result.run.components
    assert len(engine.requests) == 1
    ledger = component(result, "pass_telemetry")
    assert ledger["pass_invocation_count"] == 1 and ledger["stopped"]
    bundle = component(result, "raw_model_response")
    assert any(row["envelope"].get("response", {}).get("text") == "not-json"
               for row in bundle["execution_evidence"]["records"])


def test_retention_failure_remains_incomplete_before_candidate_or_review(ordinary, monkeypatch):
    from application_state.ingest import components
    from application_state.errors import ApplicationStateConflictError
    persist = components.persist_component_payload

    def fail_final_telemetry(**kwargs):
        if kwargs["kind"].value == "pass_telemetry":
            raise OSError("synthetic final telemetry failure")
        return persist(**kwargs)

    monkeypatch.setattr(components, "persist_component_payload", fail_final_telemetry)
    result = invoke(ordinary)
    assert result.run.status == ExtractionRunStatus.INCOMPLETE
    assert result.failure_kind == "evidence_retention"
    assert "candidate_graph" not in result.run.components
    assert "raw_model_response" not in result.run.components
    binding = result.run.lineage["execution_evidence_binding"]
    rows = components.list_private_execution_events(binding=binding, expected_revision=result.run.revision)
    assert sum("ge_attempt" in row["record"] for row in rows) == 7
    assert any(row["record"]["capture_id"] == "execution-outcome" for row in rows)
    with pytest.raises(ApplicationStateConflictError, match="run binding"):
        components.get_component_bytes(run_id=result.run.run_id, kind="raw_model_response",
                                       content_sha256=next(row["sha256"] for row in rows if "ge_attempt" in row["record"]))


def test_injected_client_does_not_construct_default_ge(ordinary, monkeypatch):
    from src.graph_memory.extraction.category_candidate_graph_extractor import FixtureCategoryGraphPassClient
    _, engine, _ = ordinary
    monkeypatch.setattr(service, "BoundedRecapPassClient", lambda *a, **k: pytest.fail("default GE constructed"))
    result = invoke(ordinary, category_client=FixtureCategoryGraphPassClient({}))
    assert result.run.status == ExtractionRunStatus.REVIEWABLE
    assert not engine.requests


def test_encounter_profile_budget_finishes_eight_source_invocations(ordinary):
    _, engine, _ = ordinary
    result = invoke(ordinary, profile="category_encounter_job_preview")
    assert result.run.status == ExtractionRunStatus.REVIEWABLE, result.diagnostics
    assert len(engine.requests) == 8
    ledger = component(result, "pass_telemetry")
    assert ledger["pass_invocation_limit"] == ledger["pass_invocation_count"] == 8


def test_ordinary_reasoning_passes_use_explicit_edge_headroom_and_deadlines(ordinary):
    _, engine, _ = ordinary
    result = invoke(ordinary)
    assert len(engine.requests) == 7
    assert [request.max_output_tokens for request in engine.requests] == [16384] * 6 + [32768]
    assert all(120000 < request.deadline_ms <= 240000 for request in engine.requests)
    ledger = component(result, "pass_telemetry")
    assert ledger["limits"]["max_output_tokens"] == 16384
    assert ledger["limits"]["edge_max_output_tokens"] == 32768
    assert ledger["limits"]["per_call_deadline_ms"] == 240000
    assert ledger["limits"]["run_deadline_ms"] == 900000
    assert [call["max_output_tokens"] for call in ledger["calls"]] == [16384] * 6 + [32768]
    assert all(120000 < call["deadline_ms"] <= 240000 for call in ledger["calls"])


def test_ordinary_production_keeps_name_only_known_actor_when_model_omits_it(ordinary):
    result=invoke(ordinary,reviewed_character_catalog={
        'status':'available','native_pin':{'native_world_id':'world:synthetic','binding_version':1,'revision_id':'r1'},
        'entities':[{'entity_id':'native:ari','label':'Ari','names':['Ari']}],
    })
    assert result.run.status==ExtractionRunStatus.REVIEWABLE, result.diagnostics
    graph=component(result,'candidate_graph')
    assert len(graph['nodes'])==1 and graph['nodes'][0]['label']=='Ari'
    assert graph['nodes'][0]['description'] is None
    assert graph['nodes'][0]['evidence_refs'][0]['anchor_quotes']==['Ari']
    assert result.run.lineage['known_character_bindings']['mentions'][0]['surface']=='Ari'
