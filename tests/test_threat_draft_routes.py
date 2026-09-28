from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from apps.live_control_server.main import create_app
import apps.live_control_server.routes.threat_drafts as threat_drafts_routes
from apps.live_control_server.ports.world_graph_authority import WorldGraphAuthorityError
from apps.live_control_server.services.world_container_registry import create_world_container


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
    assert created["workflow_state"] == "drafting"
    assert created["candidate_refs"] == []

    # Fresh app instance simulates process restart against durable store files.
    restarted = TestClient(create_app())
    read_response = restarted.get(f"/api/live/threat-drafts/{draft_id}")
    assert read_response.status_code == 200
    assert read_response.json()["draft_id"] == draft_id

    list_response = restarted.get(
        "/api/live/threat-drafts",
        params={"campaign_id": "campaign_1", "limit": 10, "offset": 0},
    )
    assert list_response.status_code == 200
    body = list_response.json()
    assert body["total"] == 1
    assert body["limit"] == 10
    assert body["offset"] == 0
    assert len(body["drafts"]) == 1

    update_body = {
        "expected_version": 1,
        "name": "Ironhide Brute",
        "description": "Updated.",
        "threat_kind": "creature",
        "generation_intent": created["generation_intent"],
        "encounter_context": created["encounter_context"],
        "graph_context_snapshot": created["graph_context_snapshot"],
    }
    update_response = restarted.put(f"/api/live/threat-drafts/{draft_id}", json=update_body)
    assert update_response.status_code == 200
    assert update_response.json()["version"] == 2

    stale = restarted.put(f"/api/live/threat-drafts/{draft_id}", json=update_body)
    assert stale.status_code == 409


def test_threat_draft_rejects_extra_fields(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(threat_drafts_routes, "repo_root", lambda: tmp_path)
    client = TestClient(create_app())
    payload = _payload()
    payload["unexpected"] = "nope"
    response = client.post("/api/live/threat-drafts", json=payload)
    assert response.status_code == 422


def test_threat_draft_rejects_unbounded_fields(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(threat_drafts_routes, "repo_root", lambda: tmp_path)
    client = TestClient(create_app())
    payload = _payload()
    payload["tags"] = ["t" * 501]
    response = client.post("/api/live/threat-drafts", json=payload)
    assert response.status_code == 422


def test_threat_draft_list_rejects_oversized_limit(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(threat_drafts_routes, "repo_root", lambda: tmp_path)
    client = TestClient(create_app())
    response = client.get("/api/live/threat-drafts", params={"limit": 101})
    assert response.status_code == 422


def test_threat_draft_rejects_path_escape_id(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(threat_drafts_routes, "repo_root", lambda: tmp_path)
    client = TestClient(create_app())
    response = client.get("/api/live/threat-drafts/../escape")
    assert response.status_code in {404, 422}


def _world_payload(root: Path, name: str = "World A") -> dict:
    payload = _payload()
    payload.update(
        scope_mode="world", campaign_id=None,
        world_id=create_world_container(root, name=name).world_id,
        graph_context_snapshot={
            "graph_revision_id": None, "selected_node_ids": [],
            "admitted_source_anchor_ids": [],
        },
    )
    return payload


def test_world_routes_round_trip_scope_filter_and_restart(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(threat_drafts_routes, "repo_root", lambda: tmp_path)
    client = TestClient(create_app())
    a = _world_payload(tmp_path)
    b = _world_payload(tmp_path, "World B")
    created = client.post("/api/live/threat-drafts", json=a)
    assert created.status_code == 200
    draft = created.json()
    assert (draft["schema"], draft["scope_mode"], draft["campaign_id"]) == (
        "dmb_threat_draft_v2", "world", None,
    )
    assert client.post("/api/live/threat-drafts", json=b).status_code == 200
    assert client.post("/api/live/threat-drafts", json=_payload()).status_code == 200
    restarted = TestClient(create_app())
    assert restarted.get(f"/api/live/threat-drafts/{draft['draft_id']}").json() == draft
    update = {key: value for key, value in a.items()
              if key not in {"world_id", "campaign_id", "scope_mode", "created_by"}}
    update.update(expected_version=1, description="Edited World-owned brief.")
    edited = restarted.put(f"/api/live/threat-drafts/{draft['draft_id']}", json=update)
    assert edited.status_code == 200
    assert edited.json()["schema"] == "dmb_threat_draft_v2"
    assert edited.json()["world_id"] == a["world_id"]
    summaries = restarted.get("/api/live/threat-drafts", params={"world_id": a["world_id"]}).json()
    assert summaries["total"] == 1
    assert summaries["drafts"][0]["schema"] == "dmb_threat_draft_summary_v2"
    assert summaries["drafts"][0]["campaign_id"] is None
    assert restarted.get("/api/live/threat-drafts", params={"campaign_id": "campaign_1"}).json()["total"] == 1


@pytest.mark.parametrize("mutation", [
    {"world_id": "unknown-world"}, {"world_id": " "},
    {"campaign_id": "campaign_1"}, {"scope_mode": "campaign"},
])
def test_world_routes_reject_unknown_or_mixed_scope(monkeypatch, tmp_path: Path, mutation) -> None:
    monkeypatch.setattr(threat_drafts_routes, "repo_root", lambda: tmp_path)
    client = TestClient(create_app())
    payload = _world_payload(tmp_path)
    payload.update(mutation)
    response = client.post("/api/live/threat-drafts", json=payload)
    assert response.status_code in {404, 422}
    assert not (tmp_path / "out/threat_drafts").exists()


@pytest.mark.parametrize("result", ["exact", "foreign", "wrong_revision", "missing", "unavailable"])
def test_world_route_revision_admission_before_create_and_update(
    monkeypatch, tmp_path: Path, result: str,
) -> None:
    monkeypatch.setattr(threat_drafts_routes, "repo_root", lambda: tmp_path)
    client = TestClient(create_app())
    payload = _world_payload(tmp_path)
    existing = client.post("/api/live/threat-drafts", json=payload).json()
    calls = []

    def read_revision(world_id, revision_id):
        calls.append((world_id, revision_id))
        if result in {"missing", "unavailable"}:
            raise WorldGraphAuthorityError(
                "Unavailable pin", code="revision_unavailable" if result == "missing" else "authority_unavailable",
            )
        return SimpleNamespace(
            world_id="foreign-world" if result == "foreign" else world_id,
            revision_id="other-revision" if result == "wrong_revision" else revision_id,
        )

    monkeypatch.setattr(threat_drafts_routes, "get_world_graph_authority",
                        lambda: SimpleNamespace(read_revision=read_revision))
    payload["graph_context_snapshot"]["graph_revision_id"] = "exact-pin"
    expected_status = 200 if result == "exact" else 503 if result == "unavailable" else 422
    assert client.post("/api/live/threat-drafts", json=payload).status_code == expected_status
    update = {key: value for key, value in payload.items()
              if key not in {"world_id", "campaign_id", "scope_mode", "created_by"}}
    update.update(expected_version=1, description="Changed.")
    assert client.put(f"/api/live/threat-drafts/{existing['draft_id']}", json=update).status_code == expected_status
    assert calls == [(payload["world_id"], "exact-pin")] * 2
    if result != "exact":
        assert client.get(f"/api/live/threat-drafts/{existing['draft_id']}").json() == existing


def test_world_route_rejects_factory_unavailable_but_freestanding_is_explicit(
    monkeypatch, tmp_path: Path,
) -> None:
    monkeypatch.setattr(threat_drafts_routes, "repo_root", lambda: tmp_path)
    client = TestClient(create_app())
    payload = _world_payload(tmp_path)

    def unavailable():
        raise RuntimeError("Not mounted")

    monkeypatch.setattr(threat_drafts_routes, "get_world_graph_authority", unavailable)
    assert client.post("/api/live/threat-drafts", json=payload).status_code == 200
    payload["graph_context_snapshot"]["graph_revision_id"] = "pin"
    assert client.post("/api/live/threat-drafts", json=payload).status_code == 503
