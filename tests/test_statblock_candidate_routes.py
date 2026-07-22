from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from apps.live_control_server.main import create_app
import apps.live_control_server.routes.statblock_candidates as candidate_routes
import apps.live_control_server.routes.threat_drafts as threat_drafts_routes
from apps.live_control_server.services import statblock_candidate_generation as generation


def _draft_payload() -> dict:
    return {
        "world_id": "world_1",
        "campaign_id": "campaign_1",
        "name": "Ironhide Brute",
        "description": "A brutal enforcer.",
        "threat_kind": "creature",
        "generation_intent": {
            "ruleset": {"system": "dnd5e", "edition": "2024"},
            "must_include": [],
            "must_avoid": [],
        },
        "encounter_context": {"terrain_notes": []},
        "graph_context_snapshot": {
            "graph_revision_id": "rev_graph_1",
            "selected_node_ids": [],
            "admitted_source_anchor_ids": [],
        },
        "created_by": "gm",
    }


def test_generate_and_read_candidate_routes(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(threat_drafts_routes, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(candidate_routes, "repo_root", lambda: tmp_path)

    fixture = {
        "candidate_id": "cand_route_1",
        "contract": "dungeonmind.dungeonbuddy-statblocks",
        "contract_version": "1.0.0",
        "created_at": "2026-01-01T00:00:00Z",
        "expires_at": "2099-01-01T00:00:00Z",
        "definition": {"identity": {"name": "Ironhide Brute"}},
    }

    class FakeClient:
        def generate_candidate(self, body: dict):
            assert body["asset_options"]["generate_images"] is False
            return fixture

        def get_candidate(self, candidate_id: str):
            return fixture

    original = generation.generate_candidate_from_draft

    def _wrapped(root, **kwargs):
        kwargs["client"] = FakeClient()
        return original(root, **kwargs)

    monkeypatch.setattr(generation, "generate_candidate_from_draft", _wrapped)
    # Route imports the function by name; patch the route module binding too.
    monkeypatch.setattr(candidate_routes, "generate_candidate_from_draft", _wrapped)

    client = TestClient(create_app())
    created = client.post("/api/live/threat-drafts", json=_draft_payload()).json()
    draft_id = created["draft_id"]

    generated = client.post(
        f"/api/live/threat-drafts/{draft_id}/candidates:generate",
        json={"expected_draft_version": 1},
    )
    assert generated.status_code == 200
    body = generated.json()
    assert body["outcome"] == "success"
    assert body["candidate_ref"]["candidate_id"] == "cand_route_1"

    read = client.get("/api/live/statblock-candidates/cand_route_1")
    assert read.status_code == 200
    assert read.json()["status"] == "active"
    assert read.json()["candidate"]["candidate_id"] == "cand_route_1"

    stale = client.post(
        f"/api/live/threat-drafts/{draft_id}/candidates:generate",
        json={"expected_draft_version": 99},
    )
    assert stale.status_code == 409
