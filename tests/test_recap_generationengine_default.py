"""Ordinary recap route selects GE and retains evidence without publishing."""

import hashlib
import json
import stat
from types import SimpleNamespace

import pytest
from generationengine.types import TextResult
from tests.test_bounded_recap_execution import (
    Engine,
    deepseek_observation,
    semantic_engine_seam,  # noqa: F401
)
from apps.live_control_server.services import graph_preview_runner as service
from apps.live_control_server.services.recap_ingest_context import RecapContextSnapshot
from src.graph_memory.extraction.bounded_recap_execution import DEEPSEEK_MODEL
from src.graph_memory.ingestion.extraction_run import ExtractionRunStatus


@pytest.fixture
def ordinary(monkeypatch, tmp_path):
    monkeypatch.setenv("DMB_ARTIFACT_DATA_ROOT", str(tmp_path))
    from tests.test_recap_managed_standing_context import seed_binding
    seed_binding(tmp_path,"managed-fixture-world","world:synthetic")
    source = SimpleNamespace(
        source_artifact_id="artifact:synthetic",
        source_sha256="a" * 64,
        source_span_index={},
    )
    monkeypatch.setattr(service, "create_recap_source_artifact", lambda *a, **k: source)
    monkeypatch.setattr(service, "_normalized_from_registered", lambda *a: source)
    monkeypatch.setattr(
        service, "_recap_identity_snapshot", lambda *a, **k: {"roster": ["Ari"]}
    )
    engine = Engine(
        TextResult(
            text=json.dumps({"observation_nodes": []}),
            observation=deepseek_observation(),
        )
    )
    from src.graph_memory.extraction import bounded_recap_execution as adapter

    monkeypatch.setattr(adapter, "_default_engine_for", lambda provider: engine)
    diagnostics = SimpleNamespace(model_copy=lambda **k: SimpleNamespace(errors=[]))
    result = SimpleNamespace(
        run=SimpleNamespace(
            run_id="new-run",
            components={},
            status=ExtractionRunStatus.REVIEWABLE,
            revision=3,
            diagnostics=diagnostics,
            lineage={},
        )
    )

    def run(request):
        assert request.model_id == DEEPSEEK_MODEL
        request.category_client.run_pass(
            "actor_pass",
            model_id=request.model_id,
            instructions="Extract actors",
            user_content="Ari held the gate.",
        )
        return result

    monkeypatch.setattr(service, "run_production_extraction", run)
    return tmp_path, engine, result


def invoke(root, **kwargs):
    return service.run_recap_production_extraction(
        repo_root=root,
        campaign_id="synthetic",
        session_id="session-1",
        recap_path=root / "source.md",
        allow_llm=True,
        output_dir=root / "new-run",
        ingest_context=RecapContextSnapshot(
            schema="dm_world_campaign_ingest_context_v1",
            managed_world_id="managed-fixture-world",
            native_world_id="world:synthetic",
            binding_version=1,
            campaign_id="synthetic",
            head_revision_id="revision:fixture",
            graph_schema="dm_graph_v1",
            graph_payload_sha256="a" * 64,
        ),
        **kwargs,
    )


def test_default_ge_route_and_private_evidence(ordinary):
    root, engine, result = ordinary
    assert invoke(root) is result
    assert len(engine.requests) == 1
    request = engine.requests[0]
    assert (request.provider, request.model) == ("openrouter", DEEPSEEK_MODEL)
    assert request.provider_route.order == ("DeepSeek",)
    assert request.provider_route.allow_fallbacks is False
    assert request.max_transport_retries == 0
    assert request.max_output_tokens == 8192
    output = root / "new-run"
    ledger = json.loads((output / "inference_call_ledger.json").read_text())
    assert ledger["run_id"] == "new-run"
    assert len(ledger["calls"]) == 1
    assert "Ari" not in json.dumps(ledger)
    responses = list((output / ".private" / "generationengine_attempts").glob("*.json"))
    assert responses
    for path in responses:
        response = json.loads(path.read_text())
        assert response["context_sha256"]["source_content"] == "a" * 64
        assert (
            response["context_sha256"]["settled_identity_context"]
            == hashlib.sha256(b'{"roster":["Ari"]}').hexdigest()
        )
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert stat.S_IMODE((output / "inference_call_ledger.json").stat().st_mode) == 0o600


def test_ordinary_request_helper_reaches_service_without_openai_default(
    ordinary, monkeypatch
):
    from apps.live_control_server.routes import recap_ingest as route

    root, engine, _ = ordinary
    monkeypatch.setattr(
        route,
        "_request_recap_context",
        lambda body: RecapContextSnapshot(
            schema="dm_world_campaign_ingest_context_v1",
            managed_world_id="managed-fixture-world",
            native_world_id="world:synthetic",
            binding_version=1,
            campaign_id="synthetic",
            head_revision_id="revision:fixture",
            graph_schema="dm_graph_v1",
            graph_payload_sha256="a" * 64,
        ),
    )
    monkeypatch.setattr(
        route,
        "inspect_recap_ingest_status",
        lambda **k: {
            "status": "ok",
            "states": ["normalized_reused", "normalized_current"],
            "warnings": [],
            "paths": {},
        },
    )
    monkeypatch.setattr(
        route, "_normalized_recap_graph_path", lambda *a: root / "source.md"
    )
    monkeypatch.setattr(route, "repo_root", lambda: root)

    def materialize(**kwargs):
        assert kwargs["graph_model_id"] is None
        invoke(root, model_id=kwargs["graph_model_id"])
        return {"status": "candidate_validation_ready"}

    monkeypatch.setattr(route, "materialize_recap_preview_supergraph", materialize)
    route._generate_recap_memory_from_request(
        route.RecapIngestRequest(
            operation="generate_recap_memory", campaign_id="synthetic", session=1
        ),
        root,
    )
    assert engine.requests[0].model == DEEPSEEK_MODEL


@pytest.mark.parametrize("model", ["gpt-5.4-mini", "gpt-6-luna", "unknown"])
def test_model_override_fails_before_source_or_inference(ordinary, model):
    root, engine, _ = ordinary
    with pytest.raises(ValueError, match="configured DeepSeek"):
        invoke(root, model_id=model)
    assert not engine.requests
    assert not (root / "new-run").exists()


def test_failed_returned_response_is_retained_without_retry(ordinary):
    root, engine, _ = ordinary
    engine.response = TextResult(text="not json", observation=deepseek_observation())
    from src.graph_memory.extraction.category_candidate_graph_extractor import (
        CategoryGraphExtractionError,
    )

    with pytest.raises(CategoryGraphExtractionError):
        invoke(root)
    assert len(engine.requests) == 1
    ledger = json.loads((root / "new-run" / "inference_call_ledger.json").read_text())
    assert ledger["run_id"] is None
    assert len(ledger["calls"]) == 1
    assert list(
        (root / "new-run" / ".private" / "generationengine_attempts").glob("*.json")
    )


def test_ledger_failure_revokes_reviewable_status(ordinary, monkeypatch):
    from apps.live_control_server.services import graph_run_registry as registry

    root, _, _ = ordinary
    write = service._write_recap_private_json

    def failing(path, payload):
        if path.name == "inference_call_ledger.json":
            raise OSError("synthetic disk failure")
        return write(path, payload)

    monkeypatch.setattr(service, "_write_recap_private_json", failing)
    transitions = []
    monkeypatch.setattr(
        registry, "update_extraction_run_status", lambda *a, **k: transitions.append(k)
    )
    with pytest.raises(service.RecapExecutionEvidenceError):
        invoke(root)
    assert transitions[0]["status"] == ExtractionRunStatus.FAILED
    assert transitions[0]["expected_revision"] == 3
    assert transitions[0]["lineage"]["reviewable"] is False


def test_injected_client_does_not_construct_default_ge(ordinary, monkeypatch):
    root, engine, result = ordinary
    sentinel = object()

    def run(request):
        assert request.category_client is sentinel
        return result

    monkeypatch.setattr(service, "run_production_extraction", run)
    invoke(root, category_client=sentinel, model_id="synthetic-model")
    assert not engine.requests
    assert not (root / "new-run" / "inference_call_ledger.json").exists()


def test_encounter_profile_budget_finishes_nine_planned_invocations(
    ordinary, monkeypatch
):
    root, engine, result = ordinary

    def run(request):
        assert request.profile_id == "recap_category_encounter_job_preview"
        assert request.category_client.limits.max_calls == 9
        for _ in range(9):
            request.category_client.run_pass(
                "actor_pass",
                model_id=request.model_id,
                instructions="synthetic pass",
                user_content="Ari",
            )
        return result

    monkeypatch.setattr(service, "run_production_extraction", run)
    invoke(root, profile="category_encounter_job_preview")
    assert len(engine.requests) == 9
    ledger = json.loads((root / "new-run" / "inference_call_ledger.json").read_text())
    assert ledger["pass_invocation_limit"] == 9
    assert ledger["pass_invocation_count"] == 9


def test_ordinary_edge_pass_uses_larger_response_capacity(ordinary, monkeypatch):
    from src.graph_memory.extraction.recap_extraction_profile import RECAP_EXTRACTION_PROFILE
    root, engine, result = ordinary
    engine.response = TextResult(text=json.dumps({"observation_edges": []}), observation=deepseek_observation())
    def run(request):
        request.category_client.run_pass("edge_pass", model_id=request.model_id,
            instructions="Extract source-backed relationships", user_content="Ari guards the gate.",
            pass_spec=RECAP_EXTRACTION_PROFILE.edge_pass)
        return result
    monkeypatch.setattr(service, "run_production_extraction", run)
    invoke(root)
    assert len(engine.requests) == 1
    assert engine.requests[0].max_output_tokens == 16384
    assert engine.requests[0].deadline_ms <= 120000
    ledger = json.loads((root / "new-run" / "inference_call_ledger.json").read_text())
    assert ledger["calls"][0]["max_output_tokens"] == 16384
