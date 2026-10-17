from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

pytest_plugins = ["tests.application_state.conftest"]


@pytest.fixture
def client(application_state_dsn: str, monkeypatch: pytest.MonkeyPatch):
    from apps.live_control_server.routes import combat_encounters as route
    from apps.live_control_server.services.managed_world_graph_projection import (
        VerifiedManagedWorldBinding,
    )

    repo = Path(__file__).resolve().parents[1]
    resolved: list[tuple[str, Path]] = []
    monkeypatch.setattr(route, "repo_root", lambda: repo)
    monkeypatch.setattr(route, "managed_world_data_root", lambda root: root)

    def resolve(world_id: str, *, root: Path | None = None):
        assert root == repo
        resolved.append((world_id, root))
        return VerifiedManagedWorldBinding(
            managed_world_id=world_id,
            native_world_id=f"native-{world_id}",
            binding_version=1,
            source_root_relpath=f"corpus/{world_id}",
        )

    monkeypatch.setattr(route, "resolve_managed_world_binding", resolve)
    app = FastAPI()
    app.include_router(route.router)
    with TestClient(app) as test_client:
        yield test_client, resolved


def _create(client: TestClient, title: str = "Mireward Gate") -> dict:
    response = client.post(
        "/api/live/combat/encounters",
        params={"world_id": "elderwyld"},
        json={"title": title, "campaign_id": "longmont-c2", "session": 29},
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_world_scoped_encounter_http_create_open_save_and_conflict(client) -> None:
    test_client, resolutions = client
    created = _create(test_client)
    encounter_id = created["encounter_id"]
    assert created["world_id"] == "elderwyld"
    assert created["revision"] == 1
    assert created["ruleset"]["config_id"] == "generic.manual-tracking"

    listed = test_client.get(
        "/api/live/combat/encounters", params={"world_id": "elderwyld"}
    )
    opened = test_client.get(
        f"/api/live/combat/encounters/{encounter_id}",
        params={"world_id": "elderwyld"},
    )
    assert listed.status_code == 200
    assert listed.json() == [created]
    assert opened.status_code == 200
    assert opened.json() == created

    draft = {**created["draft"], "title": "The Gate Holds"}
    saved = test_client.put(
        f"/api/live/combat/encounters/{encounter_id}",
        params={"world_id": "elderwyld"},
        json={"expected_revision": 1, "draft": draft},
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["revision"] == 2
    assert saved.json()["draft"]["title"] == "The Gate Holds"

    stale = test_client.put(
        f"/api/live/combat/encounters/{encounter_id}",
        params={"world_id": "elderwyld"},
        json={"expected_revision": 1, "draft": {**draft, "title": "Stale"}},
    )
    wrong_world = test_client.get(
        f"/api/live/combat/encounters/{encounter_id}",
        params={"world_id": "conks-and-cons"},
    )
    assert stale.status_code == 409
    assert wrong_world.status_code == 404
    assert all(world_id in {"elderwyld", "conks-and-cons"} for world_id, _ in resolutions)


def test_unverified_world_binding_fails_before_encounter_access(client, monkeypatch) -> None:
    from apps.live_control_server.routes import combat_encounters as route
    from apps.live_control_server.services.managed_world_graph_projection import (
        WorldGraphProjectionServiceError,
    )

    test_client, _ = client

    def reject(_world_id: str, *, root: Path | None = None):
        raise WorldGraphProjectionServiceError(
            "Managed World is not verified by its source root.",
            code="managed_world_unverified",
            status_code=409,
        )

    monkeypatch.setattr(route, "resolve_managed_world_binding", reject)
    response = test_client.get(
        "/api/live/combat/encounters", params={"world_id": "elderwyld"}
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "Managed World is not verified by its source root."


def test_generated_statblock_add_targets_selected_durable_encounter(client, monkeypatch) -> None:
    from apps.live_control_server.services import combat_encounters as combat_service

    test_client, _ = client
    created = _create(test_client, "South Road Ambush")
    encounter_id = created["encounter_id"]
    draft = {
        **created["draft"],
        "entities": [{"id": "guard-1", "name": "Gate Guard", "order": 1}],
    }
    saved = test_client.put(
        f"/api/live/combat/encounters/{encounter_id}",
        params={"world_id": "elderwyld"},
        json={"expected_revision": 1, "draft": draft},
    )
    assert saved.status_code == 200, saved.text

    detail = SimpleNamespace(
        artifact_id="statblock:geomantic-drake",
        draft_id="draft:geomantic-drake",
        title="Geomantic Drake",
        corpus_display_path="corpus/eldyrwild-markdown/Longmont/geomantic-drake.md",
        corpus_file_fingerprint="f" * 64,
        combat_defaults=SimpleNamespace(name="Geomantic Drake", armor_class=15, hit_points=76),
        retrieval={"status": "retrieval_verified", "verified_at": "2026-10-17T00:00:00Z"},
        warnings=[],
    )
    monkeypatch.setattr(combat_service, "read_generated_statblock", lambda **_kwargs: detail)

    added = test_client.post(
        f"/api/live/combat/encounters/{encounter_id}/statblocks/{detail.artifact_id}",
        params={"world_id": "elderwyld"},
        json={
            "team": "enemy",
            "count": 2,
            "insert_after_entity_id": "guard-1",
            "group_key": "drakes",
        },
    )
    assert added.status_code == 200, added.text
    body = added.json()
    assert body["encounter"]["revision"] == 3
    assert [item["order"] for item in body["added_entities"]] == [2, 3]
    assert [item["id"] for item in body["added_entities"]] == [
        item["id"] for item in body["encounter"]["draft"]["entities"][1:]
    ]
    assert body["encounter"]["draft"]["groups"][0]["member_ids"] == [
        item["id"] for item in body["added_entities"]
    ]
    assert body["added_entities"][0]["provenance"][0]["artifact_id"] == detail.artifact_id

    invalid_anchor = test_client.post(
        f"/api/live/combat/encounters/{encounter_id}/statblocks/{detail.artifact_id}",
        params={"world_id": "elderwyld"},
        json={"insert_after_entity_id": "missing-entity"},
    )
    assert invalid_anchor.status_code == 422
    reopened = test_client.get(
        f"/api/live/combat/encounters/{encounter_id}",
        params={"world_id": "elderwyld"},
    )
    assert reopened.json()["revision"] == 3


def test_generated_statblock_errors_keep_their_http_status(client, monkeypatch) -> None:
    from apps.live_control_server.services import combat_encounters as combat_service
    from apps.live_control_server.services.statblock_draft_store import (
        StatblockDraftNotFoundError,
    )

    test_client, _ = client
    created = _create(test_client)

    def missing(**_kwargs):
        raise StatblockDraftNotFoundError("generated statblock not found")

    monkeypatch.setattr(combat_service, "read_generated_statblock", missing)
    response = test_client.post(
        f"/api/live/combat/encounters/{created['encounter_id']}/statblocks/statblock%3Amissing",
        params={"world_id": "elderwyld"},
        json={},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "generated statblock not found"
