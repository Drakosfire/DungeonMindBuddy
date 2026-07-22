from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from apps.live_control_server.main import create_app
import apps.live_control_server.routes.threat_drafts as threat_drafts_routes


def _payload() -> dict:
    return {
        "world_id": "world_1",
        "campaign_id": "campaign_1",
        "name": "Ironhide Brute",
        "description": "A brutal enforcer.",
        "threat_kind": "creature",
        "generation_intent": {
            "ruleset": {"system": "dnd5e", "edition": "2024"},
            "target_cr": "3",
            "must_include": [],
            "must_avoid": [],
        },
        "encounter_context": {"terrain_notes": []},
        "graph_context_snapshot": {
            "graph_revision_id": "rev_graph_1",
            "selected_node_ids": ["node_a"],
            "admitted_source_anchor_ids": ["anchor_1"],
        },
        "created_by": "gm",
    }


def test_threat_draft_routes_crud_and_stale(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(threat_drafts_routes, "repo_root", lambda: tmp_path)
    client = TestClient(create_app())

    create_response = client.post("/api/live/threat-drafts", json=_payload())
    assert create_response.status_code == 200
    created = create_response.json()
    draft_id = created["draft_id"]
    assert created["schema"] == "dmb_threat_draft_v1"
    assert created["version"] == 1

    read_response = client.get(f"/api/live/threat-drafts/{draft_id}")
    assert read_response.status_code == 200
    assert read_response.json()["draft_id"] == draft_id

    list_response = client.get("/api/live/threat-drafts", params={"campaign_id": "campaign_1"})
    assert list_response.status_code == 200
    assert len(list_response.json()["drafts"]) == 1

    update_body = {
        "expected_version": 1,
        "name": "Ironhide Brute",
        "description": "Updated.",
        "threat_kind": "creature",
        "generation_intent": created["generation_intent"],
        "encounter_context": created["encounter_context"],
        "graph_context_snapshot": created["graph_context_snapshot"],
    }
    update_response = client.put(f"/api/live/threat-drafts/{draft_id}", json=update_body)
    assert update_response.status_code == 200
    assert update_response.json()["version"] == 2

    stale = client.put(f"/api/live/threat-drafts/{draft_id}", json=update_body)
    assert stale.status_code == 409


def test_threat_draft_rejects_extra_fields(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(threat_drafts_routes, "repo_root", lambda: tmp_path)
    client = TestClient(create_app())
    payload = _payload()
    payload["unexpected"] = "nope"
    response = client.post("/api/live/threat-drafts", json=payload)
    assert response.status_code == 422
