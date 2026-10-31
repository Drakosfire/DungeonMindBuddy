"""The retired preview-store command cannot launch work; Process extracts once."""
from copy import deepcopy

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from apps.live_control_server.routes import recap_ingest as route


@pytest.mark.parametrize("retired", [
    {"operation": "materialize_preview_supergraph"},
    {"operation": "generate_recap_memory", "materialize_after_extract": True},
    {"operation": "generate_recap_memory", "materialize_after_extract": False},
])
def test_retired_command_and_flag_are_rejected_before_execution(monkeypatch, retired):
    payload = {"campaign_id": "test-campaign", "session": 8, **retired}
    with pytest.raises(ValidationError):
        route.RecapIngestRequest.model_validate(payload)
    def forbidden(*args, **kwargs):
        pytest.fail("retired command reached execution")
    monkeypatch.setattr(route, "_pipeline_corpus_root", forbidden)
    monkeypatch.setattr(route, "build_recap_graph_preview_bundle", forbidden)
    app = FastAPI()
    app.include_router(route.router)
    response = TestClient(app).post("/api/live/recap-ingest", json=payload)
    assert response.status_code == 422


@pytest.mark.parametrize("failed", [False, True])
def test_process_uses_extraction_without_materialization_or_planning_adoption(monkeypatch, failed):
    status = {"schema": "dmb_raw_recap_ingest_status_v1", "campaign_id": "test-campaign",
        "session": 8, "status": "recap_applied", "states": ["recap_applied", "normalized_current"],
        "paths": {}, "authority": {}, "warnings": [], "errors": [], "next_actions": [],
        "ingest_report": {}, "entity_spelling_audit": []}
    context = object()
    calls = []
    graph = {"status": "source_span_bundle_ready" if failed else "candidate_validation_ready",
        "extraction_run_id": "run:exact", "source_artifact_id": "source:exact",
        "extraction_mode": "llm_blocked" if failed else "category_decomposed",
        "blocked_reason": "Extraction did not produce a reviewable candidate." if failed else None,
        "next_actions": [] if failed else ["review_candidate"]}
    monkeypatch.setattr(route, "_pipeline_corpus_root", lambda: None)
    monkeypatch.setattr(route, "_request_recap_context", lambda body: context)
    monkeypatch.setattr(route, "inspect_recap_ingest_status", lambda **kwargs: deepcopy(status))
    monkeypatch.setattr(route, "_normalized_recap_graph_path", lambda *args: "import.md")
    def extract(**kwargs):
        calls.append(kwargs)
        return deepcopy(graph)
    monkeypatch.setattr(route, "build_recap_graph_preview_bundle", extract)
    app = FastAPI()
    app.include_router(route.router)
    response = TestClient(app).post("/api/live/recap-ingest", json={
        "operation": "generate_recap_memory", "campaign_id": "test-campaign", "session": 8,
        "managed_world_id": "world:test", "include_graph_extraction": True})
    assert response.status_code == 200, response.text
    body = response.json()
    assert len(calls) == 1
    assert calls[0]["extract_graph"] is True
    assert calls[0]["ingest_context"] is context
    assert body["ingest_report"]["graph_preview"] == graph
    assert body["status"] != "ready_for_planning_activation"
    assert not any("preview_union_store_ready" == state for state in body["states"])
    assert bool(body["warnings"]) == failed
