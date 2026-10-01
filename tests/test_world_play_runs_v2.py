from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from application_state.content.service import (
    commit_runbook,
    create_world_runbook,
    update_runbook_metadata,
)
from apps.live_control_server.main import create_app
from apps.live_control_server.services.world_container_registry import create_world_container
from tests.application_state.play_runtime_helpers import (
    SOURCE_MARKDOWN,
    SURVIVING_TARGET_MARKDOWN,
    gate_progress,
)

pytest_plugins = ["tests.application_state.conftest"]

WORLD_RUN_ID = "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee"
WORLD_RUN_ID_2 = "ffffffff-ffff-4fff-8fff-ffffffffffff"


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(
        "apps.live_control_server.routes.play_runs.repo_root",
        lambda: tmp_path,
    )
    return TestClient(create_app())


@pytest.fixture
def world_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    for module in (
        "apps.live_control_server.routes.play_runs",
        "apps.live_control_server.routes.workspace_documents",
        "apps.live_control_server.routes.live",
    ):
        monkeypatch.setattr(f"{module}.repo_root", lambda: tmp_path)
    return TestClient(create_app())


def _create_world_runbook(world_id: str, *, markdown: str = SOURCE_MARKDOWN):
    created = create_world_runbook(title=f"Runbook {world_id}", world_id=world_id)
    work_object, revision = commit_runbook(
        str(created.work_object_id),
        markdown,
        expected_revision=created.object_revision,
    )
    return work_object, revision


def _create_body(work_object, revision) -> dict[str, object]:
    return {
        "playable_artifact_id": str(work_object.work_object_id),
        "expected_playable_revision": revision.revision_n,
        "expected_playable_content_sha256": revision.content_sha256,
    }


def test_world_runbook_v2_crud_tiptap_and_exact_revision(
    application_state_dsn: str,
    world_client: TestClient,
    tmp_path: Path,
) -> None:
    world_a = create_world_container(tmp_path, name="Runbook Owner A")
    world_b = create_world_container(tmp_path, name="Runbook Owner B")

    created_response = world_client.post(
        "/api/live/workspace-documents/world-runbooks",
        json={
            "schema_version": "dmb_workspace_document_create_v2",
            "scope_mode": "world",
            "world_id": world_a.world_id,
            "title": "A world-scoped Runbook",
        },
    )
    assert created_response.status_code == 200, created_response.text
    created = created_response.json()
    assert created["schema_version"] == "dmb_world_owned_runbook_record_v2"
    assert created["world_id"] == world_a.world_id
    assert created["campaign_id"] is None
    assert created["target_session"] is None
    document_id = created["document_id"]

    listed_a = world_client.get(
        "/api/live/workspace-documents/world-runbooks",
        params={"world_id": world_a.world_id},
    )
    assert listed_a.status_code == 200, listed_a.text
    assert [record["document_id"] for record in listed_a.json()["records"]] == [
        document_id
    ]
    listed_b = world_client.get(
        "/api/live/workspace-documents/world-runbooks",
        params={"world_id": world_b.world_id},
    )
    assert listed_b.status_code == 200, listed_b.text
    assert listed_b.json()["records"] == []

    path = f"/api/live/workspace-documents/world-runbooks/{document_id}"
    assert world_client.get(path, params={"world_id": world_b.world_id}).status_code == 404
    read_a = world_client.get(path, params={"world_id": world_a.world_id})
    assert read_a.status_code == 200, read_a.text
    assert read_a.json() == created
    assert world_client.get(f"/api/live/workspace-documents/{document_id}").status_code == 404
    assert world_client.get(f"/api/live/workspace-documents/{document_id}/snapshot").status_code == 404

    # A campaign Runbook whose campaign string equals World A remains outside
    # World A's typed inventory.
    campaign_runbook = world_client.post(
        "/api/live/workspace-documents",
        json={
            "title": "Same-string Campaign Runbook",
            "campaign_id": world_a.world_id,
            "kind": "runbook",
        },
    )
    assert campaign_runbook.status_code == 200, campaign_runbook.text
    again_a = world_client.get(
        "/api/live/workspace-documents/world-runbooks",
        params={"world_id": world_a.world_id},
    )
    assert [record["document_id"] for record in again_a.json()["records"]] == [
        document_id
    ]
    legacy_list = world_client.get(
        "/api/live/workspace-documents",
        params={"campaign_id": world_a.world_id, "kind": "runbook"},
    )
    assert legacy_list.status_code == 200, legacy_list.text
    assert [record["document_id"] for record in legacy_list.json()["records"]] == [
        campaign_runbook.json()["document_id"]
    ]

    markdown = SOURCE_MARKDOWN
    prepare = world_client.post(
        f"{path}/tiptap/prepare",
        params={"world_id": world_a.world_id},
        json={
            "schema_version": "dmb_tiptap_markdown_write_prepare_v2",
            "scope_mode": "world",
            "world_id": world_a.world_id,
            "document_id": document_id,
            "markdown": markdown,
            "expected_revision": created["revision"],
        },
    )
    assert prepare.status_code == 200, prepare.text
    prepare_payload = prepare.json()
    assert prepare_payload["world_id"] == world_a.world_id
    assert prepare_payload["schema_version"] == "dmb_tiptap_markdown_write_prepare_v2"
    assert prepare_payload["writer_confirm_token"]

    commit = world_client.post(
        f"{path}/tiptap/commit",
        params={"world_id": world_a.world_id},
        json={
            "schema_version": "dmb_tiptap_markdown_write_commit_v2",
            "scope_mode": "world",
            "world_id": world_a.world_id,
            "document_id": document_id,
            "markdown": markdown,
            "expected_revision": prepare_payload["registry_revision"],
            "writer_confirm_token": prepare_payload["writer_confirm_token"],
        },
    )
    assert commit.status_code == 200, commit.text
    commit_payload = commit.json()
    assert commit_payload["world_id"] == world_a.world_id
    assert commit_payload["committed_record"]["world_id"] == world_a.world_id

    snapshot = world_client.get(
        f"{path}/snapshot", params={"world_id": world_a.world_id}
    )
    assert snapshot.status_code == 200, snapshot.text
    assert snapshot.json()["schema_version"] == "dmb_workspace_runbook_snapshot_v2"
    assert snapshot.json()["markdown"] == markdown.rstrip("\n") + "\n"
    assert snapshot.json()["content_sha256"] == commit_payload["normalized_content_sha256"]

    committed = world_client.get(
        f"{path}/committed-revision", params={"world_id": world_a.world_id}
    )
    assert committed.status_code == 200, committed.text
    committed_payload = committed.json()
    assert committed_payload["schema_version"] == "dmb_workspace_committed_revision_v2"
    assert committed_payload["world_id"] == world_a.world_id
    assert committed_payload["kind"] == "runbook"
    assert committed_payload["content_sha256"] == snapshot.json()["content_sha256"]
    exact = world_client.get(
        f"{path}/committed-revision/{committed_payload['revision_n']}",
        params={
            "world_id": world_a.world_id,
            "expected_sha256": committed_payload["content_sha256"],
        },
    )
    assert exact.status_code == 200, exact.text
    assert exact.json() == committed_payload
    wrong_exact_sha = world_client.get(
        f"{path}/committed-revision/{committed_payload['revision_n']}",
        params={"world_id": world_a.world_id, "expected_sha256": "0" * 64},
    )
    assert wrong_exact_sha.status_code == 409, wrong_exact_sha.text
    missing_exact_sha = world_client.get(
        f"{path}/committed-revision/{committed_payload['revision_n']}",
        params={"world_id": world_a.world_id},
    )
    assert missing_exact_sha.status_code == 422

    # Generic V1 writes and revision reads cannot omit the World owner proof.
    assert world_client.get(
        f"/api/live/workspace-documents/{document_id}/committed-revision"
    ).status_code == 404
    missing_scope = world_client.post(
        f"{path}/tiptap/prepare",
        params={"world_id": world_a.world_id},
        json={
            "document_id": document_id,
            "markdown": markdown,
        },
    )
    assert missing_scope.status_code == 422

    foreign_prepare = world_client.post(
        f"{path}/tiptap/prepare",
        params={"world_id": world_b.world_id},
        json={
            "schema_version": "dmb_tiptap_markdown_write_prepare_v2",
            "scope_mode": "world",
            "world_id": world_b.world_id,
            "document_id": document_id,
            "markdown": markdown,
            "expected_revision": created["revision"],
        },
    )
    assert foreign_prepare.status_code == 404, foreign_prepare.text
    foreign_commit = world_client.post(
        f"{path}/tiptap/commit",
        params={"world_id": world_b.world_id},
        json={
            "schema_version": "dmb_tiptap_markdown_write_commit_v2",
            "scope_mode": "world",
            "world_id": world_b.world_id,
            "document_id": document_id,
            "markdown": markdown,
            "expected_revision": prepare_payload["registry_revision"],
            "writer_confirm_token": prepare_payload["writer_confirm_token"],
        },
    )
    assert foreign_commit.status_code == 404, foreign_commit.text
    unchanged = world_client.get(
        f"{path}/snapshot", params={"world_id": world_a.world_id}
    )
    assert unchanged.status_code == 200, unchanged.text
    assert unchanged.json()["content_sha256"] == snapshot.json()["content_sha256"]


def test_live_query_world_play_context_v2_is_world_run_and_pin_bound(
    application_state_dsn: str,
    world_client: TestClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from application_state.content.service import commit_runbook, create_runbook
    from tests.test_play_run_reference_manifest import C2S27_SHAPED_V2_MARKDOWN

    world_a = create_world_container(tmp_path, name="Play Context Owner A")
    world_b = create_world_container(tmp_path, name="Play Context Owner B")
    created = world_client.post(
        "/api/live/workspace-documents/world-runbooks",
        json={
            "schema_version": "dmb_workspace_document_create_v2",
            "scope_mode": "world",
            "world_id": world_a.world_id,
            "title": "Pinned Runbook",
        },
    )
    assert created.status_code == 200, created.text
    document_id = created.json()["document_id"]
    prepared = world_client.post(
        f"/api/live/workspace-documents/world-runbooks/{document_id}/tiptap/prepare",
        params={"world_id": world_a.world_id},
        json={
            "schema_version": "dmb_tiptap_markdown_write_prepare_v2",
            "scope_mode": "world",
            "world_id": world_a.world_id,
            "document_id": document_id,
            "markdown": C2S27_SHAPED_V2_MARKDOWN,
            "expected_revision": created.json()["revision"],
        },
    )
    assert prepared.status_code == 200, prepared.text
    committed_write = world_client.post(
        f"/api/live/workspace-documents/world-runbooks/{document_id}/tiptap/commit",
        params={"world_id": world_a.world_id},
        json={
            "schema_version": "dmb_tiptap_markdown_write_commit_v2",
            "scope_mode": "world",
            "world_id": world_a.world_id,
            "document_id": document_id,
            "markdown": C2S27_SHAPED_V2_MARKDOWN,
            "expected_revision": prepared.json()["registry_revision"],
            "writer_confirm_token": prepared.json()["writer_confirm_token"],
        },
    )
    assert committed_write.status_code == 200, committed_write.text
    revision = world_client.get(
        f"/api/live/workspace-documents/world-runbooks/{document_id}/committed-revision",
        params={"world_id": world_a.world_id},
    )
    assert revision.status_code == 200, revision.text
    pinned = revision.json()

    world_run_id = "12121212-1212-4212-8212-121212121212"
    world_run = world_client.put(
        f"/api/live/world-play-runs/v2/{world_run_id}",
        params={"world_id": world_a.world_id},
        json={
            "playable_artifact_id": document_id,
            "expected_playable_revision": pinned["revision_n"],
            "expected_playable_content_sha256": pinned["content_sha256"],
        },
    )
    assert world_run.status_code == 200, world_run.text
    manifest_path = f"/api/live/world-play-runs/v2/{world_run_id}/reference-manifest"
    seal = world_client.put(manifest_path, params={"world_id": world_a.world_id})
    assert seal.status_code == 200, seal.text
    progress = world_client.put(
        f"/api/live/world-play-runs/v2/{world_run_id}/progress",
        params={"world_id": world_a.world_id},
        json={
            "expected_run_revision": 1,
            "progress": {
                "current_scene_id": "scene:gate-line",
                "current_beat_id": "beat:hold-the-gate",
                "resolved_beat_ids": [],
                "selections": {},
                "notes_by_element_id": {},
            },
        },
    )
    assert progress.status_code == 200, progress.text
    current_run_revision = progress.json()["run_revision"]

    captured: list[object] = []

    def process_stub(*_args: object, **kwargs: object) -> dict[str, object]:
        captured.append(kwargs["surface_context"])
        return {"accepted": True}

    monkeypatch.setattr(
        "apps.live_control_server.routes.live.process_live_query", process_stub
    )

    def query(*, outer_world_id: str, context: dict[str, object]):
        return world_client.post(
            "/api/live/query",
            json={
                "campaign_id": outer_world_id,
                "session": 1,
                "query_backend": "hermes",
                "text": "Describe the current moment.",
                "world_graph_context": {
                    "schema": "dmb_agent_world_graph_query_context_request_v1",
                    "world_id": outer_world_id,
                    "campaign_id": "",
                    "scope_mode": "world",
                    "admissibility": "gm",
                    "focus": {"kind": "none"},
                },
                "surface_context": context,
            },
        )

    valid_context = {
        "schema": "dmb_agent_world_play_surface_context_request_v2",
        "surface_id": "play",
        "world_id": world_a.world_id,
        "run_id": world_run_id,
        "run_revision": current_run_revision,
    }
    accepted = query(outer_world_id=world_a.world_id, context=valid_context)
    assert accepted.status_code == 200, accepted.text
    assert accepted.json() == {"accepted": True}
    assert len(captured) == 1
    assert captured[0].model_dump(by_alias=True) == valid_context

    stale = query(
        outer_world_id=world_a.world_id,
        context={**valid_context, "run_revision": current_run_revision - 1},
    )
    assert stale.status_code == 409, stale.text
    assert len(captured) == 1

    foreign = query(outer_world_id=world_b.world_id, context=valid_context)
    assert foreign.status_code == 422, foreign.text
    assert len(captured) == 1

    unscoped = world_client.post(
        "/api/live/query",
        json={
            "campaign_id": "longmont-c2",
            "session": 1,
            "query_backend": "hermes",
            "text": "Do not use a World Run here.",
            "surface_context": valid_context,
        },
    )
    assert unscoped.status_code == 422, unscoped.text
    assert len(captured) == 1

    # A campaign-owned Runbook and Run using the same string as World A cannot
    # satisfy the explicit World V2 owner lookup.
    campaign_runbook = create_runbook(
        title="Campaign string equals World string", campaign_id=world_a.world_id
    )
    campaign_runbook, campaign_revision = commit_runbook(
        str(campaign_runbook.work_object_id),
        SOURCE_MARKDOWN,
        expected_revision=campaign_runbook.object_revision,
    )
    campaign_run_id = "34343434-3434-4434-8434-343434343434"
    campaign_run = world_client.put(
        f"/api/live/play-runs/{campaign_run_id}",
        json={
            "playable_artifact_id": str(campaign_runbook.work_object_id),
            "expected_playable_revision": campaign_revision.revision_n,
            "expected_playable_content_sha256": campaign_revision.content_sha256,
        },
    )
    assert campaign_run.status_code == 200, campaign_run.text
    matched_string = query(
        outer_world_id=world_a.world_id,
        context={
            **valid_context,
            "run_id": campaign_run_id,
            "run_revision": 1,
        },
    )
    assert matched_string.status_code == 409, matched_string.text
    assert len(captured) == 1


def test_world_v2_create_replay_progress_manifest_and_campaign_v1_fence(
    application_state_dsn: str, client: TestClient
) -> None:
    _work_object, _revision = _create_world_runbook("demo-world-a")
    body = _create_body(_work_object, _revision)
    path = f"/api/live/world-play-runs/v2/{WORLD_RUN_ID}"

    created_response = client.put(path, params={"world_id": "demo-world-a"}, json=body)
    assert created_response.status_code == 200, created_response.text
    created = created_response.json()
    assert created["schema_version"] == "dmb_world_play_run_record_v2"
    assert created["run_id"] == WORLD_RUN_ID
    assert created["world_id"] == "demo-world-a"
    assert "campaign_id" not in created
    assert created["playable_artifact_id"] == str(_work_object.work_object_id)
    assert created["playable_revision"] == _revision.revision_n
    assert created["playable_content_sha256"] == _revision.content_sha256
    assert created["run_revision"] == 1

    replayed = client.put(path, params={"world_id": "demo-world-a"}, json=body)
    assert replayed.status_code == 200, replayed.text
    assert replayed.json() == created
    loaded = client.get(path, params={"world_id": "demo-world-a"})
    assert loaded.status_code == 200
    assert loaded.json() == created
    listed = client.get(
        "/api/live/world-play-runs/v2", params={"world_id": "demo-world-a"}
    )
    assert listed.status_code == 200
    assert listed.json() == {
        "schema_version": "dmb_world_play_runs_list_v2",
        "records": [created],
    }
    assert client.get(
        "/api/live/world-play-runs/v2", params={"world_id": "demo-world-b"}
    ).json()["records"] == []
    assert client.get(path, params={"world_id": "demo-world-b"}).status_code == 404

    manifest_url = f"{path}/reference-manifest"
    manifest = client.get(manifest_url, params={"world_id": "demo-world-a"})
    assert manifest.status_code == 200, manifest.text
    assert manifest.json()["run_id"] == WORLD_RUN_ID
    assert manifest.json()["playable_revision"] == _revision.revision_n
    assert client.get(manifest_url, params={"world_id": "demo-world-b"}).status_code == 404
    sealed = client.put(manifest_url, params={"world_id": "demo-world-a"})
    assert sealed.status_code == 200
    assert sealed.json() == manifest.json()

    progressed = client.put(
        f"{path}/progress",
        params={"world_id": "demo-world-a"},
        json={"expected_run_revision": 1, "progress": gate_progress().model_dump(mode="json")},
    )
    assert progressed.status_code == 200, progressed.text
    assert progressed.json()["run_revision"] == 2

    # Campaign V1 keeps its shape and cannot expose or mutate this World Run.
    v1_list = client.get("/api/live/play-runs")
    assert v1_list.status_code == 200
    assert v1_list.json() == {
        "schema_version": "dmb_play_runs_list_v1",
        "records": [],
    }
    assert client.get(f"/api/live/play-runs/{WORLD_RUN_ID}").status_code == 404
    v1_progress = client.put(
        f"/api/live/play-runs/{WORLD_RUN_ID}/progress",
        json={"expected_run_revision": 2, "progress": gate_progress().model_dump(mode="json")},
    )
    assert v1_progress.status_code == 404
    assert client.get(
        f"/api/live/play-runs/{WORLD_RUN_ID}/reference-manifest"
    ).status_code == 404
    assert client.put(
        f"/api/live/play-runs/{WORLD_RUN_ID}/reference-manifest"
    ).status_code == 404
    assert client.put("/api/live/play-active-run", json={"run_id": WORLD_RUN_ID}).status_code == 404

    # A World-owned Runbook cannot enter through campaign V1 create/replay.
    v1_create = client.put(
        f"/api/live/play-runs/{WORLD_RUN_ID_2}", json=body
    )
    assert v1_create.status_code == 422
    assert client.get("/api/live/play-runs").json()["records"] == []


def test_create_rejects_wrong_world_and_bad_sha_without_persisting(
    application_state_dsn: str, client: TestClient
) -> None:
    work_object, revision = _create_world_runbook("demo-world-a")
    body = _create_body(work_object, revision)
    path = f"/api/live/world-play-runs/v2/{WORLD_RUN_ID_2}"

    wrong_world = client.put(path, params={"world_id": "demo-world-b"}, json=body)
    assert wrong_world.status_code == 409
    wrong_sha_body = {**body, "expected_playable_content_sha256": "0" * 64}
    wrong_sha = client.put(
        path, params={"world_id": "demo-world-a"}, json=wrong_sha_body
    )
    assert wrong_sha.status_code == 409
    assert client.get(
        "/api/live/world-play-runs/v2", params={"world_id": "demo-world-a"}
    ).json()["records"] == []


def test_world_run_keeps_its_exact_pin_after_source_runbook_is_discarded(
    application_state_dsn: str,
    client: TestClient,
) -> None:
    world_id = "discarded-runbook-world"
    work_object, pinned_revision = _create_world_runbook(world_id)
    path = f"/api/live/world-play-runs/v2/{WORLD_RUN_ID}"
    created = client.put(
        path,
        params={"world_id": world_id},
        json=_create_body(work_object, pinned_revision),
    )
    assert created.status_code == 200, created.text
    created_record = created.json()
    assert created_record["playable_revision"] == pinned_revision.revision_n
    assert created_record["playable_work_revision_id"] == str(
        pinned_revision.work_revision_id
    )
    assert created_record["playable_content_sha256"] == pinned_revision.content_sha256

    target_work_object, newer_revision = commit_runbook(
        str(work_object.work_object_id),
        SURVIVING_TARGET_MARKDOWN,
        expected_revision=work_object.object_revision,
    )
    discarded = update_runbook_metadata(
        str(work_object.work_object_id),
        status="discarded",
        expected_revision=target_work_object.object_revision,
    )
    assert discarded.status == "discarded"

    listed = client.get(
        "/api/live/world-play-runs/v2", params={"world_id": world_id}
    )
    assert listed.status_code == 200, listed.text
    assert listed.json()["records"] == [created_record]
    detail = client.get(path, params={"world_id": world_id})
    assert detail.status_code == 200, detail.text
    assert detail.json() == created_record
    assert client.get(path, params={"world_id": "another-world"}).status_code == 404

    replay = client.put(
        path,
        params={"world_id": world_id},
        json=_create_body(work_object, pinned_revision),
    )
    assert replay.status_code == 200, replay.text
    assert replay.json() == created_record

    progressed = client.put(
        f"{path}/progress",
        params={"world_id": world_id},
        json={
            "expected_run_revision": 1,
            "progress": gate_progress().model_dump(mode="json"),
        },
    )
    assert progressed.status_code == 200, progressed.text
    progressed_record = progressed.json()
    assert progressed_record["world_id"] == world_id
    assert progressed_record["run_revision"] == 2
    assert progressed_record["playable_revision"] == pinned_revision.revision_n
    assert progressed_record["playable_work_revision_id"] == str(
        pinned_revision.work_revision_id
    )
    assert progressed_record["playable_content_sha256"] == pinned_revision.content_sha256

    manifest_path = f"{path}/reference-manifest"
    fetched_manifest = client.get(manifest_path, params={"world_id": world_id})
    assert fetched_manifest.status_code == 200, fetched_manifest.text
    manifest = fetched_manifest.json()
    assert manifest["run_id"] == WORLD_RUN_ID
    assert manifest["playable_revision"] == pinned_revision.revision_n
    assert manifest["playable_content_sha256"] == pinned_revision.content_sha256
    sealed_manifest = client.put(manifest_path, params={"world_id": world_id})
    assert sealed_manifest.status_code == 200, sealed_manifest.text
    assert sealed_manifest.json() == manifest

    rebase_after_discard = client.put(
        f"{path}/rebase",
        params={"world_id": world_id},
        json={
            "expected_run_revision": 2,
            "target_playable_revision": newer_revision.revision_n,
            "target_playable_content_sha256": newer_revision.content_sha256,
        },
    )
    assert rebase_after_discard.status_code == 409
    assert client.get(path, params={"world_id": world_id}).json() == progressed_record

    new_run_after_discard = client.put(
        f"/api/live/world-play-runs/v2/{WORLD_RUN_ID_2}",
        params={"world_id": world_id},
        json=_create_body(target_work_object, newer_revision),
    )
    assert new_run_after_discard.status_code == 409
    assert client.get(
        "/api/live/world-play-runs/v2", params={"world_id": world_id}
    ).json()["records"] == [progressed_record]


def test_world_rebase_is_same_owner_newer_only_and_uses_run_revision_cas(
    application_state_dsn: str, client: TestClient
) -> None:
    work_object, first_revision = _create_world_runbook("demo-world-a")
    path = f"/api/live/world-play-runs/v2/{WORLD_RUN_ID}"
    created = client.put(
        path,
        params={"world_id": "demo-world-a"},
        json=_create_body(work_object, first_revision),
    ).json()
    target_work_object, second_revision = commit_runbook(
        str(work_object.work_object_id),
        SURVIVING_TARGET_MARKDOWN,
        expected_revision=work_object.object_revision,
    )
    assert target_work_object.world_id == "demo-world-a"

    rebased = client.put(
        f"{path}/rebase",
        params={"world_id": "demo-world-a"},
        json={
            "expected_run_revision": created["run_revision"],
            "target_playable_revision": second_revision.revision_n,
            "target_playable_content_sha256": second_revision.content_sha256,
        },
    )
    assert rebased.status_code == 200, rebased.text
    rebased_record = rebased.json()
    assert rebased_record["world_id"] == "demo-world-a"
    assert rebased_record["run_revision"] == 2
    assert rebased_record["rebased_from_run_revision"] == 1
    assert rebased_record["playable_revision"] == second_revision.revision_n
    assert rebased_record["playable_work_revision_id"] == str(
        second_revision.work_revision_id
    )
    sealed = client.get(
        f"{path}/reference-manifest", params={"world_id": "demo-world-a"}
    ).json()
    assert sealed["playable_revision"] == second_revision.revision_n

    progressed = client.put(
        f"{path}/progress",
        params={"world_id": "demo-world-a"},
        json={"expected_run_revision": 2, "progress": gate_progress().model_dump(mode="json")},
    )
    assert progressed.status_code == 200
    before = client.get(path, params={"world_id": "demo-world-a"}).json()

    wrong_world_rebase = client.put(
        f"{path}/rebase",
        params={"world_id": "demo-world-b"},
        json={
            "expected_run_revision": 3,
            "target_playable_revision": second_revision.revision_n,
            "target_playable_content_sha256": second_revision.content_sha256,
        },
    )
    assert wrong_world_rebase.status_code == 404

    target_work_object, third_revision = commit_runbook(
        str(work_object.work_object_id),
        SURVIVING_TARGET_MARKDOWN + "\nA newer exact revision.\n",
        expected_revision=target_work_object.object_revision,
    )
    assert third_revision.revision_n > second_revision.revision_n
    stale = client.put(
        f"{path}/rebase",
        params={"world_id": "demo-world-a"},
        json={
            "expected_run_revision": 1,
            "target_playable_revision": third_revision.revision_n,
            "target_playable_content_sha256": third_revision.content_sha256,
        },
    )
    assert stale.status_code == 409
    after = client.get(path, params={"world_id": "demo-world-a"}).json()
    assert after == before
    assert client.get(
        f"{path}/reference-manifest", params={"world_id": "demo-world-a"}
    ).json() == sealed
