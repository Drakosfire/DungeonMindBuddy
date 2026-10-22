"""Statblock HTTP lifecycle remains durable across code checkout replacement."""
from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from apps.live_control_server.main import create_app
from apps.live_control_server.routes import statblock_candidates as candidates, threat_drafts as drafts
from apps.live_control_server.services import statblock_candidate_generation as generation
from apps.live_control_server.services import statblock_mechanics_acceptance as acceptance
from apps.live_control_server.services.world_container_registry import create_world_container
from apps.live_control_server.integrations.dungeonmind_statblocks.models import GeneratedStatblockCandidateV1
from apps.live_control_server.integrations.dungeonmind_statblocks.client import ValidationResponseV1
from apps.live_control_server.integrations.dungeonmind_statblocks.generated import CreateStatblockResponseV1
from apps.live_control_server.integrations.dungeonmind_statblocks.mechanics_locator import CreateStatblockResult, locator_from_create_response

FIXTURES = Path(__file__).parent / "fixtures/statblocks/v1"


def fixture(name):
    return json.loads((FIXTURES / name).read_text())


def test_http_generation_acceptance_survives_code_root_switch(monkeypatch, tmp_path):
    code_a, code_b, data, worlds = [tmp_path / name for name in ("code-a", "code-b", "data", "worlds")]
    for directory in (code_a, code_b, data, worlds):
        directory.mkdir()
    world = create_world_container(worlds, name="Durable mechanics")
    monkeypatch.setenv("DMB_ARTIFACT_DATA_ROOT", str(data))
    monkeypatch.setenv("DMB_MANAGED_WORLD_DATA_ROOT", str(worlds))
    monkeypatch.setattr(drafts, "repo_root", lambda: code_a)
    monkeypatch.setattr(candidates, "repo_root", lambda: code_a)
    class DMS:
        generate_calls = 0
        create_calls = 0
        def generate_candidate(self, body):
            self.generate_calls += 1
            payload = fixture("candidate-response.json")
            payload.update(candidate_id="cand_durable1", expires_at="2099-01-01T00:00:00Z")
            payload["generation_receipt"]["request_id"] = body["request_id"]
            return GeneratedStatblockCandidateV1.model_validate(payload)
        def get_candidate(self, candidate_id):
            payload = fixture("candidate-response.json")
            payload.update(candidate_id=candidate_id, expires_at="2099-01-01T00:00:00Z")
            return GeneratedStatblockCandidateV1.model_validate(payload)
        def validate_definition(self, body):
            return ValidationResponseV1.model_validate(fixture("validate-response.json"))
        def create_statblock(self, body):
            self.create_calls += 1
            response = CreateStatblockResponseV1.model_validate(fixture("create-response.json"))
            return CreateStatblockResult(locator=locator_from_create_response(response), server_metadata={})
    dms = DMS()
    generate = generation.generate_candidate_from_draft
    accept = acceptance.begin_or_resume_acceptance
    monkeypatch.setattr(candidates, "generate_candidate_from_draft", lambda root, **kwargs: generate(root, client=dms, **kwargs))
    monkeypatch.setattr(candidates, "begin_or_resume_acceptance", lambda root, **kwargs: accept(root, client=dms, **kwargs))
    client = TestClient(create_app())
    response = client.post("/api/live/threat-drafts", json={
        "scope_mode": "world", "world_id": world.world_id, "campaign_id": None,
        "name": "Durable Keeper", "description": "Synthetic keeper.", "threat_kind": "creature",
        "generation_intent": {"ruleset": {"system": "dnd5e", "edition": "2024"}},
        "graph_context_snapshot": {"graph_revision_id": None, "selected_node_ids": [], "admitted_source_anchor_ids": []},
        "created_by": "gm",
    })
    assert response.status_code == 200, response.text
    draft_id = response.json()["draft_id"]
    generated = client.post(f"/api/live/threat-drafts/{draft_id}/candidates:generate", json={"expected_draft_version": 1, "client_request_id": "durable-generation"})
    assert generated.status_code == 200, generated.text
    assert generated.json()["outcome"] == "success"
    current = client.get(f"/api/live/threat-drafts/{draft_id}").json()
    validation = fixture("validate-response.json")
    request = {"operation_id": "accop_durable", "expected_draft_version": current["version"],
               "definition": fixture("candidate-response.json")["definition"],
               "validation_receipt": validation["validation_receipt"], "validation_definition_digest": validation["definition_digest"],
               "change_summary": "Synthetic acceptance", "actor": "gm"}
    saved = client.post(f"/api/live/threat-drafts/{draft_id}/mechanics:accept", json=request)
    assert saved.status_code == 200, saved.text
    assert saved.json()["result_label"] == "mechanics_saved"
    snapshot = client.get(f"/api/live/threat-drafts/{draft_id}").json()
    monkeypatch.setattr(drafts, "repo_root", lambda: code_b)
    monkeypatch.setattr(candidates, "repo_root", lambda: code_b)
    reopened = TestClient(create_app())
    assert reopened.get(f"/api/live/threat-drafts/{draft_id}").json() == snapshot
    assert reopened.get("/api/live/statblock-candidates/cand_durable1").json()["status"] == "active"
    journal = reopened.get(f"/api/live/threat-drafts/{draft_id}/acceptance-operations/accop_durable")
    assert journal.status_code == 200, journal.text
    assert journal.json()["result_label"] == "mechanics_saved"
    assert reopened.post(f"/api/live/threat-drafts/{draft_id}/mechanics:accept", json=request).json()["result_label"] == "mechanics_saved"
    assert (dms.generate_calls, dms.create_calls) == (1, 1)
    assert not list(code_a.iterdir()) and not list(code_b.iterdir())
    monkeypatch.setenv("DMB_ARTIFACT_DATA_ROOT", str(tmp_path / "missing"))
    assert reopened.get(f"/api/live/threat-drafts/{draft_id}").status_code == 503
    assert reopened.get("/api/live/statblock-candidates/cand_durable1").status_code == 503
    assert reopened.post(f"/api/live/threat-drafts/{draft_id}/mechanics:accept", json=request).status_code == 503
    assert (dms.generate_calls, dms.create_calls) == (1, 1)
    assert not list(code_a.iterdir()) and not list(code_b.iterdir())
