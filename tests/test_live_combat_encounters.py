from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from application_state.combat_encounters.types import (
    CombatEncounterDraft,
    SaveCombatEncounterRequest,
)

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


@pytest.mark.parametrize("campaign_id", ["", "   "])
@pytest.mark.parametrize("session", [None, 29])
def test_create_rejects_blank_campaign_before_database_write(
    client, campaign_id, session
) -> None:
    test_client, _ = client
    before = test_client.get(
        "/api/live/combat/encounters", params={"world_id": "elderwyld"}
    )
    body = {"title": "Invalid campaign scope", "campaign_id": campaign_id}
    if session is not None:
        body["session"] = session

    response = test_client.post(
        "/api/live/combat/encounters",
        params={"world_id": "elderwyld"},
        json=body,
    )

    assert response.status_code == 422
    assert "campaign_id must not be blank" in response.text
    after = test_client.get(
        "/api/live/combat/encounters", params={"world_id": "elderwyld"}
    )
    assert after.json() == before.json() == []


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
    detail_reads: list[str] = []

    def read_detail(**_kwargs):
        detail_reads.append("read")
        return detail

    monkeypatch.setattr(combat_service, "read_generated_statblock", read_detail)

    add_options = {
        "team": "enemy",
        "count": 2,
        "insert_after_entity_id": "guard-1",
        "group_key": "drakes",
    }
    missing_revision = test_client.post(
        f"/api/live/combat/encounters/{encounter_id}/statblocks/{detail.artifact_id}",
        params={"world_id": "elderwyld"},
        json=add_options,
    )
    assert missing_revision.status_code == 422

    stale_before_add = test_client.post(
        f"/api/live/combat/encounters/{encounter_id}/statblocks/{detail.artifact_id}",
        params={"world_id": "elderwyld"},
        json={"expected_revision": 1, **add_options},
    )
    assert stale_before_add.status_code == 409
    assert detail_reads == []
    unchanged_before_add = test_client.get(
        f"/api/live/combat/encounters/{encounter_id}",
        params={"world_id": "elderwyld"},
    ).json()
    assert unchanged_before_add["revision"] == 2
    assert [item["id"] for item in unchanged_before_add["draft"]["entities"]] == ["guard-1"]

    added = test_client.post(
        f"/api/live/combat/encounters/{encounter_id}/statblocks/{detail.artifact_id}",
        params={"world_id": "elderwyld"},
        json={"expected_revision": 2, **add_options},
    )
    assert added.status_code == 200, added.text
    body = added.json()
    assert body["encounter"]["revision"] == 3
    assert detail_reads == ["read"]
    assert [item["order"] for item in body["added_entities"]] == [2, 3]
    assert [item["id"] for item in body["added_entities"]] == [
        item["id"] for item in body["encounter"]["draft"]["entities"][1:]
    ]
    assert body["encounter"]["draft"]["groups"][0]["member_ids"] == [
        item["id"] for item in body["added_entities"]
    ]
    assert body["added_entities"][0]["provenance"][0]["artifact_id"] == detail.artifact_id

    stale_after_add = test_client.post(
        f"/api/live/combat/encounters/{encounter_id}/statblocks/{detail.artifact_id}",
        params={"world_id": "elderwyld"},
        json={"expected_revision": 2, **add_options},
    )
    assert stale_after_add.status_code == 409
    assert detail_reads == ["read"]
    unchanged_after_add = test_client.get(
        f"/api/live/combat/encounters/{encounter_id}",
        params={"world_id": "elderwyld"},
    ).json()
    assert unchanged_after_add["revision"] == 3
    assert unchanged_after_add["draft"] == body["encounter"]["draft"]

    invalid_anchor = test_client.post(
        f"/api/live/combat/encounters/{encounter_id}/statblocks/{detail.artifact_id}",
        params={"world_id": "elderwyld"},
        json={"expected_revision": 3, "insert_after_entity_id": "missing-entity"},
    )
    assert invalid_anchor.status_code == 422
    reopened = test_client.get(
        f"/api/live/combat/encounters/{encounter_id}",
        params={"world_id": "elderwyld"},
    )
    assert reopened.json()["revision"] == 3


def test_generated_statblock_add_cas_preserves_a_concurrent_save(client, monkeypatch) -> None:
    from apps.live_control_server.services import combat_encounters as combat_service

    test_client, _ = client
    created = _create(test_client, "Concurrent statblock add")
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

    def read_and_concurrently_save(**_kwargs):
        saved = combat_service.save_world_combat_encounter(
            world_id="elderwyld",
            encounter_id=created["encounter_id"],
            request=SaveCombatEncounterRequest(
                expected_revision=created["revision"],
                draft=CombatEncounterDraft(title="Saved during statblock lookup"),
            ),
        )
        assert saved.revision == created["revision"] + 1
        return detail

    monkeypatch.setattr(
        combat_service, "read_generated_statblock", read_and_concurrently_save
    )
    response = test_client.post(
        f"/api/live/combat/encounters/{created['encounter_id']}/statblocks/{detail.artifact_id}",
        params={"world_id": "elderwyld"},
        json={"expected_revision": created["revision"]},
    )

    assert response.status_code == 409
    reopened = test_client.get(
        f"/api/live/combat/encounters/{created['encounter_id']}",
        params={"world_id": "elderwyld"},
    ).json()
    assert reopened["revision"] == created["revision"] + 1
    assert reopened["draft"]["title"] == "Saved during statblock lookup"
    assert reopened["draft"]["entities"] == []


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
        json={"expected_revision": 1},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "generated statblock not found"
