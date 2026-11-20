from __future__ import annotations
from tests.application_state.world_catalog_fixtures import world_snapshot

from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from apps.live_control_server.main import create_app
import apps.live_control_server.routes.threat_drafts as threat_drafts_routes
from dungeonmind.domain.errors import PersistenceIntegrityError, PersistenceUnavailableError
from apps.live_control_server.services.world_container_registry import create_world_container
from apps.live_control_server.services.managed_world_graph_projection import VerifiedManagedWorldBinding



@pytest.fixture(autouse=True)
def _forbid_classic_authority(monkeypatch):
    from apps.live_control_server.ports import world_graph_authority_access

    monkeypatch.setattr(world_graph_authority_access, "get_world_graph_authority",
                        lambda *a, **k: pytest.fail("Draft admission opened classic graph authority"))


def _install_native_reader(monkeypatch, read_revision):
    repository = SimpleNamespace(
        get_revision=read_revision,
        get_head=lambda *a, **k: pytest.fail("Draft admission looked up the current head"),
    )
    monkeypatch.setattr(threat_drafts_routes.native, "read_repository", lambda: repository)


def _native_snapshot(space_id, revision_id):
    return SimpleNamespace(revision=SimpleNamespace(space_id=space_id, revision_id=revision_id))


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
    client = TestClient(create_app(), client=("127.0.0.1", 50000))

    create_response = client.post("/api/live/threat-drafts", json=_payload())
    assert create_response.status_code == 200
    created = create_response.json()
    draft_id = created["draft_id"]
    assert created["schema"] == "dmb_threat_draft_v1"
    assert created["version"] == 1
    assert created["workflow_state"] == "drafting"
    assert created["candidate_refs"] == []

    # Fresh app instance simulates process restart against durable store files.
    restarted = TestClient(create_app(), client=("127.0.0.1", 50000))
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
    client = TestClient(create_app(), client=("127.0.0.1", 50000))
    payload = _payload()
    payload["unexpected"] = "nope"
    response = client.post("/api/live/threat-drafts", json=payload)
    assert response.status_code == 422


def test_threat_draft_rejects_unbounded_fields(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(threat_drafts_routes, "repo_root", lambda: tmp_path)
    client = TestClient(create_app(), client=("127.0.0.1", 50000))
    payload = _payload()
    payload["tags"] = ["t" * 501]
    response = client.post("/api/live/threat-drafts", json=payload)
    assert response.status_code == 422


def test_threat_draft_list_rejects_oversized_limit(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(threat_drafts_routes, "repo_root", lambda: tmp_path)
    client = TestClient(create_app(), client=("127.0.0.1", 50000))
    response = client.get("/api/live/threat-drafts", params={"limit": 101})
    assert response.status_code == 422


def test_threat_draft_rejects_path_escape_id(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(threat_drafts_routes, "repo_root", lambda: tmp_path)
    client = TestClient(create_app(), client=("127.0.0.1", 50000))
    response = client.get("/api/live/threat-drafts/../escape")
    assert response.status_code in {404, 422}


def _world_payload(root: Path, name: str = "World A") -> dict:
    payload = _payload()
    payload.update(
        scope_mode="world", campaign_id=None,
        world_id=create_world_container(name=name).world_id,
        graph_context_snapshot={
            "graph_revision_id": None, "selected_node_ids": [],
            "admitted_source_anchor_ids": [],
        },
    )
    return payload


def test_world_routes_round_trip_scope_filter_and_restart(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(threat_drafts_routes, "repo_root", lambda: tmp_path)
    client = TestClient(create_app(), client=("127.0.0.1", 50000))
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
    restarted = TestClient(create_app(), client=("127.0.0.1", 50000))
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
    client = TestClient(create_app(), client=("127.0.0.1", 50000))
    payload = _world_payload(tmp_path)
    payload.update(mutation)
    response = client.post("/api/live/threat-drafts", json=payload)
    assert response.status_code in {404, 422}
    assert not (tmp_path / "out/threat_drafts").exists()


@pytest.mark.parametrize("result", [
    "exact", "foreign", "wrong_revision", "missing", "malformed",
    "corrupt", "unavailable", "unexpected_error",
])
def test_world_route_revision_admission_before_create_and_update(
    monkeypatch, tmp_path: Path, result: str,
) -> None:
    monkeypatch.setattr(threat_drafts_routes, "repo_root", lambda: tmp_path)
    client = TestClient(create_app(), client=("127.0.0.1", 50000))
    payload = _world_payload(tmp_path)
    existing = client.post("/api/live/threat-drafts", json=payload).json()
    binding = VerifiedManagedWorldBinding(payload["world_id"], "world:reserved", 1, "sources/owned")
    monkeypatch.setattr(threat_drafts_routes, "resolve_managed_world_binding", lambda *args, **kwargs: binding)
    calls = []

    def read_revision(space_id, revision_id):
        calls.append((space_id, revision_id))
        if result == "missing":
            return None
        if result == "malformed":
            return SimpleNamespace(revision=None)
        if result == "corrupt":
            raise PersistenceIntegrityError("Stored native revision is corrupt")
        if result == "unavailable":
            raise PersistenceUnavailableError("Native storage unavailable")
        if result == "unexpected_error":
            raise RuntimeError("Native repository read failed")
        return _native_snapshot(
            "foreign-space" if result == "foreign" else space_id,
            "other-revision" if result == "wrong_revision" else revision_id,
        )

    _install_native_reader(monkeypatch, read_revision)
    payload["graph_context_snapshot"]["graph_revision_id"] = "exact-pin"
    expected_status = (200 if result == "exact" else 500 if result == "corrupt"
                       else 503 if result in {"unavailable", "unexpected_error"} else 422)
    created = client.post("/api/live/threat-drafts", json=payload)
    assert created.status_code == expected_status, created.text
    assert calls == [("world:reserved", "exact-pin")]
    assert client.get("/api/live/threat-drafts", params={"world_id": payload["world_id"]}).json()["total"] == (2 if result == "exact" else 1)
    update = {key: value for key, value in payload.items()
              if key not in {"world_id", "campaign_id", "scope_mode", "created_by"}}
    update.update(expected_version=1, description="Changed.")
    assert client.put(f"/api/live/threat-drafts/{existing['draft_id']}", json=update).status_code == expected_status
    assert calls == [("world:reserved", "exact-pin")] * 2
    if result != "exact":
        assert client.get(f"/api/live/threat-drafts/{existing['draft_id']}").json() == existing


def test_world_route_rejects_factory_unavailable_but_freestanding_is_explicit(
    monkeypatch, tmp_path: Path,
) -> None:
    monkeypatch.setattr(threat_drafts_routes, "repo_root", lambda: tmp_path)
    client = TestClient(create_app(), client=("127.0.0.1", 50000))
    payload = _world_payload(tmp_path)

    calls = []
    def unavailable():
        calls.append("factory")
        raise RuntimeError("Not mounted")

    monkeypatch.setattr(threat_drafts_routes, "resolve_managed_world_binding",
                        lambda *a, **k: pytest.fail("Freestanding draft resolved a graph binding"))
    monkeypatch.setattr(threat_drafts_routes.native, "read_repository", unavailable)
    created = client.post("/api/live/threat-drafts", json=payload)
    assert created.status_code == 200, created.text
    existing = created.json()
    update = {key: value for key, value in payload.items()
              if key not in {"world_id", "campaign_id", "scope_mode", "created_by"}}
    update.update(expected_version=1, description="Freestanding edit.")
    edited = client.put(f"/api/live/threat-drafts/{existing['draft_id']}", json=update)
    assert edited.status_code == 200, edited.text
    assert calls == []
    existing = edited.json()
    monkeypatch.setattr(threat_drafts_routes, "resolve_managed_world_binding",
                        lambda *a, **k: VerifiedManagedWorldBinding(payload["world_id"], "world:reserved", 1, "sources/owned"))
    payload["graph_context_snapshot"]["graph_revision_id"] = "pin"
    assert client.post("/api/live/threat-drafts", json=payload).status_code == 503
    update.update(expected_version=2, graph_context_snapshot=payload["graph_context_snapshot"])
    assert client.put(f"/api/live/threat-drafts/{existing['draft_id']}", json=update).status_code == 503
    assert calls == ["factory", "factory"]
    assert client.get(f"/api/live/threat-drafts/{existing['draft_id']}").json() == existing


def test_world_draft_binding_change_rejects_before_mutation(monkeypatch, tmp_path):
    monkeypatch.setattr(threat_drafts_routes, "repo_root", lambda: tmp_path)
    client = TestClient(create_app(), client=("127.0.0.1", 50000))
    payload = _world_payload(tmp_path)
    existing = client.post("/api/live/threat-drafts", json=payload).json()
    first = VerifiedManagedWorldBinding(payload["world_id"], "world:one", 1, "sources/owned")
    changed = VerifiedManagedWorldBinding(payload["world_id"], "world:two", 2, "sources/owned")
    bindings = iter([first, changed, first, changed])
    monkeypatch.setattr(threat_drafts_routes, "resolve_managed_world_binding", lambda *args, **kwargs: next(bindings))
    calls = []
    def read_revision(space_id, revision_id):
        calls.append((space_id, revision_id))
        return _native_snapshot(space_id, revision_id)
    _install_native_reader(monkeypatch, read_revision)
    payload["graph_context_snapshot"]["graph_revision_id"] = "exact-pin"
    assert client.post("/api/live/threat-drafts", json=payload).status_code == 409
    update = {key: value for key, value in payload.items() if key not in {"world_id", "campaign_id", "scope_mode", "created_by"}}
    update["expected_version"] = 1
    assert client.put(f"/api/live/threat-drafts/{existing['draft_id']}", json=update).status_code == 409
    assert client.get(f"/api/live/threat-drafts/{existing['draft_id']}").json() == existing
    assert calls == [("world:one", "exact-pin")] * 2
    assert client.get("/api/live/threat-drafts", params={"world_id": payload["world_id"]}).json()["total"] == 1


def test_world_draft_reserved_identity_is_not_graph_authority(monkeypatch, tmp_path):
    monkeypatch.setattr(threat_drafts_routes, "repo_root", lambda: tmp_path)
    payload = _world_payload(tmp_path)
    payload["graph_context_snapshot"]["graph_revision_id"] = "exact-pin"
    monkeypatch.setattr(threat_drafts_routes.native, "read_repository", lambda: pytest.fail("Unbound World must not reach native authority"))
    client = TestClient(create_app(), client=("127.0.0.1", 50000))
    assert client.post("/api/live/threat-drafts", json=payload).status_code == 409
    assert not (tmp_path / "out/threat_drafts").exists()


def test_world_draft_admission_uses_configured_world_root(monkeypatch, tmp_path):
    code_root = tmp_path / "code"
    world_root = tmp_path / "world-data"
    code_root.mkdir(); world_root.mkdir()
    monkeypatch.setattr(threat_drafts_routes, "repo_root", lambda: code_root)
    payload = _world_payload(world_root)
    from tests.application_state.world_catalog_fixtures import store_world
    world = world_snapshot()[0].record
    store_world(world.model_copy(update={"native_graph_binding": {
        "status": "active", "native_world_id": "world:reserved", "binding_version": 1,
        "validated_at": "2026-10-22T00:00:00Z", "validated_head_revision_id": "exact-pin",
    }}))
    monkeypatch.setenv("DMB_MANAGED_WORLD_DATA_ROOT", str(world_root))
    calls = []
    def read_revision(world_id, revision_id):
        calls.append((world_id, revision_id))
        return _native_snapshot(world_id, revision_id)
    _install_native_reader(monkeypatch, read_revision)
    payload["graph_context_snapshot"]["graph_revision_id"] = "exact-pin"
    client = TestClient(create_app(), client=("127.0.0.1", 50000))
    response = client.post("/api/live/threat-drafts", json=payload)
    assert response.status_code == 200, response.text
    created = response.json()
    update = {key: value for key, value in payload.items() if key not in {"world_id", "campaign_id", "scope_mode", "created_by"}}
    update.update(expected_version=1, description="Changed.")
    assert client.put(f"/api/live/threat-drafts/{created['draft_id']}", json=update).status_code == 200
    assert calls == [("world:reserved", "exact-pin")] * 2
    assert not (code_root / "out/registries/world_containers.json").exists()
    monkeypatch.setenv("DMB_MANAGED_WORLD_DATA_ROOT", str(tmp_path / "missing"))
    assert client.post("/api/live/threat-drafts", json=payload).status_code == 503
    assert client.get("/api/live/threat-drafts", params={"world_id": payload["world_id"]}).json()["total"] == 1

pytestmark = pytest.mark.usefixtures("application_state_dsn")
