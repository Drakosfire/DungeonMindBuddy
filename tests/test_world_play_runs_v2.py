from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from application_state.content.service import commit_runbook, create_world_runbook
from apps.live_control_server.main import create_app
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
