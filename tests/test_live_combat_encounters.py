from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from application_state.combat_encounters.types import (
    AddGeneratedStatblockRequest,
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
    monkeypatch.setenv("DMB_AGENT_GRAPH_AUTH_MODE", "local_operator")
    monkeypatch.setenv("DMB_AGENT_GRAPH_AUTH_ENVIRONMENT", "development")
    monkeypatch.setenv("DMB_AGENT_GRAPH_LOCAL_OPERATOR_TOKEN", "test-combat-local-operator-token-123456")
    app = FastAPI()
    app.include_router(route.router)
    with TestClient(app, client=("127.0.0.1", 50000), headers={"Authorization": "Bearer test-combat-local-operator-token-123456"}) as test_client:
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


def test_real_generated_statblock_uses_configured_artifact_root_through_save_reopen(client, tmp_path, monkeypatch):
    from apps.live_control_server.services import combat_encounters as service
    from apps.live_control_server.services.statblock_draft_store import store_statblock_draft
    from apps.live_control_server.services.statblock_workbench import build_statblock_workbench_sample_response
    from tests.test_statblock_view import _promote_record
    from hashlib import sha256
    test_client, _ = client
    code, artifacts, session = tmp_path/'code', tmp_path/'artifacts', tmp_path/'session'
    for path in (code, artifacts, session):
        path.mkdir()
    monkeypatch.setenv('DMB_ARTIFACT_DATA_ROOT', str(artifacts))
    monkeypatch.setattr(service, 'repo_root', lambda: code)
    monkeypatch.setattr(service, 'session_dir', lambda: session)
    artifact = build_statblock_workbench_sample_response().artifact
    stored = store_statblock_draft(base=session,campaign_id='synthetic',session=1,artifact=artifact)
    promoted = _promote_record(session, artifacts, stored.model_dump(mode='json'))
    created = _create(test_client, 'Isolated artifact-root acceptance')
    added = test_client.post(f"/api/live/combat/encounters/{created['encounter_id']}/statblocks/{artifact.artifact_id}",
        params={'world_id':'elderwyld'}, json={'expected_revision':1,'count':1,'team':'enemy'})
    assert added.status_code == 200, added.text
    encounter = added.json()['encounter']
    row = encounter['draft']['entities'][0]
    source = artifacts/'corpus/eldyrwild-markdown'/promoted.corpus_relpath
    assert row['corpus_fingerprint'] == sha256(source.read_bytes()).hexdigest()[:32]
    draft = encounter['draft']
    draft['entities'][0]['notes'] = 'Retained after reopen'
    saved = test_client.put(f"/api/live/combat/encounters/{created['encounter_id']}", params={'world_id':'elderwyld'},
        json={'expected_revision':2,'draft':draft})
    assert saved.status_code == 200, saved.text
    reopened = test_client.get(f"/api/live/combat/encounters/{created['encounter_id']}",params={'world_id':'elderwyld'})
    assert reopened.json() == saved.json()
    assert reopened.json()['draft']['entities'][0]['notes'] == 'Retained after reopen'
    # A missing configured repository cannot be repaired from a code-local file.
    decoy = code/'corpus/eldyrwild-markdown'/promoted.corpus_relpath
    decoy.parent.mkdir(parents=True)
    decoy.write_text('Wrong checkout copy',encoding='utf-8')
    monkeypatch.setenv('DMB_ARTIFACT_DATA_ROOT',str(tmp_path/'missing'))
    with pytest.raises(RuntimeError):
        service.add_generated_statblock_to_world_combat_encounter(world_id='elderwyld', encounter_id=created['encounter_id'],
            artifact_id=artifact.artifact_id,request=AddGeneratedStatblockRequest(expected_revision=3,count=1,team='enemy'))


def _manual_world_actor():
    return {"id": "scout-instance-a", "name": "Scout", "team": "ally", "order": 1,
            "source": "manual", "hp": 18, "max_hp": 18, "world_identity": {
                "managed_world_id": "elderwyld", "native_world_id": "native-elderwyld",
                "binding_version": 1, "graph_revision_id": "graph-a", "node_id": "scout-node",
                "label": "Scout", "kind": "npc", "role": "npc", "campaign_scope": "campaign-c2"}}


def _mock_world_identity(monkeypatch):
    from apps.live_control_server.services import managed_world_graph_projection as projection
    calls = []
    def project(request):
        calls.append(request)
        return SimpleNamespace(managed_world_id="elderwyld", native_world_id="native-elderwyld", binding_version=1,
            projection=SimpleNamespace(snapshot=SimpleNamespace(revision_id="graph-a"),
                nodes=[SimpleNamespace(node_id="scout-node", label="Scout", kind="npc", role="npc", campaign_scope="campaign-c2")]))
    monkeypatch.setattr(projection, "project_managed_world_graph", project)
    return calls


def test_world_assembly_verifies_once_and_preserves_instances_through_http_reopen(client, monkeypatch):
    test_client, _ = client
    calls = _mock_world_identity(monkeypatch)
    created = _create(test_client)
    actor = _manual_world_actor()
    second = {**actor, "id": "scout-instance-b", "order": 2, "hp": 11}
    draft = {**created["draft"], "entities": [actor, second]}
    path = f'/api/live/combat/encounters/{created["encounter_id"]}?world_id=elderwyld'
    saved = test_client.put(path, json={"expected_revision": 1, "draft": draft})
    assert saved.status_code == 200, saved.text
    assert len(calls) == 1
    assert calls[0].revision_pin == "graph-a"
    assert saved.json()["draft"]["entities"][0]["ac"] is None
    assert saved.json()["draft"]["entities"][0]["world_identity"] == actor["world_identity"]
    replay = test_client.put(path, json={"expected_revision": 1, "draft": draft})
    assert replay.status_code == 409
    assert len(calls) == 1  # No repeated Graph read for a known stale Save.
    assert test_client.get(path).json() == saved.json()
    updated = saved.json()["draft"]
    updated["entities"][0]["hp"] = 7
    changed = test_client.put(path, json={"expected_revision": 2, "draft": updated})
    assert changed.status_code == 200, changed.text
    assert len(calls) == 1  # Retained source facts need no re-hydration on HP edits.
    assert [e["hp"] for e in changed.json()["draft"]["entities"]] == [7, 11]


@pytest.mark.parametrize("field,value", [("managed_world_id", "other-world"), ("native_world_id", "other-native"),
    ("binding_version", 2), ("label", "Fabricated"), ("node_id", "absent"), ("kind", "location"), ("graph_revision_id", "wrong")])
def test_world_assembly_rejects_identity_tampering_without_writing(client, monkeypatch, field, value):
    test_client, _ = client
    _mock_world_identity(monkeypatch)
    created = _create(test_client)
    actor = _manual_world_actor(); actor["world_identity"][field] = value
    path = f'/api/live/combat/encounters/{created["encounter_id"]}?world_id=elderwyld'
    response = test_client.put(path, json={"expected_revision": 1, "draft": {**created["draft"], "entities": [actor]}})
    assert response.status_code == 422, response.text
    assert test_client.get(path).json() == created


def test_saved_world_identity_cannot_be_rewritten_but_tracker_stats_can(client, monkeypatch):
    test_client, _ = client
    _mock_world_identity(monkeypatch)
    created = _create(test_client)
    path = f'/api/live/combat/encounters/{created["encounter_id"]}?world_id=elderwyld'
    saved = test_client.put(path, json={"expected_revision": 1, "draft": {**created["draft"], "entities": [_manual_world_actor()]}}).json()
    draft = saved["draft"];draft["entities"][0]["world_identity"]["label"] = "Changed after verification"
    refused = test_client.put(path, json={"expected_revision": 2, "draft": draft})
    assert refused.status_code == 422
    assert test_client.get(path).json()["draft"]["entities"][0]["world_identity"]["label"] == "Scout"


def test_combat_requires_native_gm_access(client):
    test_client, _ = client
    test_client.headers.pop("authorization")
    response = test_client.get("/api/live/combat/encounters?world_id=elderwyld")
    assert response.status_code == 401


@pytest.mark.parametrize("field,value", [("statblock_title", "Pretend mechanics"), ("corpus_fingerprint", "unverified"), ("tags", ["generated_statblock"])])
def test_manual_world_identity_cannot_claim_mechanics(client, monkeypatch, field, value):
    test_client, _ = client
    _mock_world_identity(monkeypatch)
    created = _create(test_client); actor = _manual_world_actor(); actor[field] = value
    path = f'/api/live/combat/encounters/{created["encounter_id"]}?world_id=elderwyld'
    refused = test_client.put(path,json={"expected_revision":1,"draft":{**created["draft"],"entities":[actor]}})
    assert refused.status_code == 422, refused.text
    assert test_client.get(path).json() == created
