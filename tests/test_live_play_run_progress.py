from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.live_control_server.main import create_app
from apps.live_control_server.services.play_run_registry import get_play_run
from apps.live_control_server.services.play_run_reference_manifest import (
    get_play_run_reference_manifest,
    play_run_reference_manifest_path,
)
from apps.live_control_server.services.tiptap_markdown_write import (
    TiptapMarkdownWriteCommitRequest,
    TiptapMarkdownWritePrepareRequest,
    commit_tiptap_markdown_write,
    prepare_tiptap_markdown_write,
)
from apps.live_control_server.services.workspace_document_registry import (
    WorkspaceDocumentRecord,
    WorkspaceDocumentSnapshot,
    create_workspace_document,
    get_workspace_document_snapshot,
)
from tests.application_state.playable_binding import (
    playable_binding,
    remember_committed_playable,
)

pytest_plugins = ["tests.application_state.conftest"]

RUN_ID_A = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"

PROGRESS_MARKDOWN = "\n".join(
    [
        "<!-- dmb-playable-element:v1 kind=scene id=scene:gate -->",
        "## The Gate",
        "",
        "<!-- dmb-playable-element:v1 kind=beat id=beat:arrival -->",
        "### Arrival",
        "",
        "<!-- dmb-playable-element:v1 kind=choice id=choice:route -->",
        "### Which route do they take?",
        "",
        "<!-- dmb-playable-element:v1 kind=option id=option:fire -->",
        "#### Burn through the growth",
        "",
        "<!-- dmb-playable-element:v1 kind=option id=option:wait -->",
        "#### Wait and watch",
        "",
    ]
)


@pytest.fixture(autouse=True)
def _application_state(application_state_dsn: str) -> str:
    return application_state_dsn


@pytest.fixture
def root(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def client(root: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(
        "apps.live_control_server.routes.play_runs.repo_root",
        lambda: root,
    )
    return TestClient(create_app())


def _commit_record(
    root: Path,
    record: WorkspaceDocumentRecord,
    markdown: str,
) -> WorkspaceDocumentSnapshot:
    prepared = prepare_tiptap_markdown_write(
        root=root,
        request=TiptapMarkdownWritePrepareRequest(
            document_id=record.document_id,
            markdown=markdown,
            expected_revision=record.revision,
        ),
    )
    assert prepared.writer_ok is True
    assert prepared.writer_confirm_token
    commit_tiptap_markdown_write(
        root=root,
        request=TiptapMarkdownWriteCommitRequest(
            document_id=record.document_id,
            markdown=markdown,
            writer_confirm_token=prepared.writer_confirm_token,
            expected_revision=record.revision,
        ),
    )
    return remember_committed_playable(get_workspace_document_snapshot(root, record.document_id))


def _create_committed_runbook(root: Path) -> WorkspaceDocumentSnapshot:
    record = create_workspace_document(
        root,
        title="Runbook progress-http",
        campaign_id="longmont-c2",
        kind="runbook",
        target_relpath=(
            "evals/c2_live_prep/mireward-prep/content/tiptap/"
            "progress-http.md"
        ),
    )
    return _commit_record(root, record, PROGRESS_MARKDOWN)


def _run_request(snapshot: WorkspaceDocumentSnapshot) -> dict[str, object]:
    revision_n, sha = playable_binding(snapshot)
    return {
        "playable_artifact_id": snapshot.record.document_id,
        "expected_playable_revision": revision_n,
        "expected_playable_content_sha256": sha,
    }


def _progress_body(expected_run_revision: int = 1) -> dict[str, object]:
    return {
        "expected_run_revision": expected_run_revision,
        "progress": {
            "current_scene_id": "scene:gate",
            "current_beat_id": "beat:arrival",
            "resolved_beat_ids": ["beat:arrival"],
            "selections": {"choice:route": "option:fire"},
            "notes_by_element_id": {"choice:route": "They hesitated."},
        },
    }


def _create_run(client: TestClient, root: Path, snapshot: WorkspaceDocumentSnapshot) -> None:
    created = client.put(f"/api/live/play-runs/{RUN_ID_A}", json=_run_request(snapshot))
    assert created.status_code == 200


def test_progress_put_round_trip_and_get_includes_snapshot(
    client: TestClient,
    root: Path,
) -> None:
    snapshot = _create_committed_runbook(root)
    _create_run(client, root, snapshot)
    manifest_before = get_play_run_reference_manifest(root, RUN_ID_A)

    response = client.put(
        f"/api/live/play-runs/{RUN_ID_A}/progress",
        json=_progress_body(),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["run_revision"] == 2
    assert body["progress"]["current_scene_id"] == "scene:gate"
    assert body["progress"]["selections"] == {"choice:route": "option:fire"}
    assert body["progress"]["notes_by_element_id"]["choice:route"] == "They hesitated."

    fetched = client.get(f"/api/live/play-runs/{RUN_ID_A}")
    assert fetched.status_code == 200
    assert fetched.json() == body
    listed = client.get("/api/live/play-runs")
    assert listed.status_code == 200
    assert listed.json()["records"] == [body]
    assert get_play_run_reference_manifest(root, RUN_ID_A) == manifest_before
    assert not play_run_reference_manifest_path(root, RUN_ID_A).exists()


def _create_and_seal(
    client: TestClient,
    root: Path,
) -> WorkspaceDocumentSnapshot:
    snapshot = _create_committed_runbook(root)
    _create_run(client, root, snapshot)
    return snapshot


def test_progress_put_rejects_partial_payload(client: TestClient, root: Path) -> None:
    _create_and_seal(client, root)
    response = client.put(
        f"/api/live/play-runs/{RUN_ID_A}/progress",
        json={"expected_run_revision": 1},
    )
    assert response.status_code == 422
    omitted = client.put(
        f"/api/live/play-runs/{RUN_ID_A}/progress",
        json={
            "expected_run_revision": 1,
            "progress": {
                "current_scene_id": "scene:gate",
                "current_beat_id": None,
                "resolved_beat_ids": [],
                "selections": {},
            },
        },
    )
    assert omitted.status_code == 422


def test_missing_manifest_is_409(client: TestClient, root: Path) -> None:
    snapshot = _create_committed_runbook(root)
    created = client.put(f"/api/live/play-runs/{RUN_ID_A}", json=_run_request(snapshot))
    assert created.status_code == 200
    record_before = get_play_run(root, RUN_ID_A)

    response = client.put(
        f"/api/live/play-runs/{RUN_ID_A}/progress",
        json=_progress_body(),
    )

    assert response.status_code == 200
    assert response.json()["run_revision"] == 2
    assert get_play_run(root, RUN_ID_A).run_revision == 2
    assert record_before.run_revision == 1
    assert not play_run_reference_manifest_path(root, RUN_ID_A).exists()


def test_http_noop_and_lost_response_replay(client: TestClient, root: Path) -> None:
    _create_and_seal(client, root)
    first = client.put(
        f"/api/live/play-runs/{RUN_ID_A}/progress",
        json=_progress_body(),
    )
    assert first.status_code == 200
    record_after = get_play_run(root, RUN_ID_A)

    noop = client.put(
        f"/api/live/play-runs/{RUN_ID_A}/progress",
        json=_progress_body(expected_run_revision=2),
    )
    assert noop.status_code == 200
    assert noop.json() == first.json()
    assert get_play_run(root, RUN_ID_A) == record_after

    replay = client.put(
        f"/api/live/play-runs/{RUN_ID_A}/progress",
        json=_progress_body(expected_run_revision=1),
    )
    assert replay.status_code == 200
    assert replay.json() == first.json()
    assert get_play_run(root, RUN_ID_A) == record_after


def test_stale_different_state_is_409(client: TestClient, root: Path) -> None:
    _create_and_seal(client, root)
    first = client.put(
        f"/api/live/play-runs/{RUN_ID_A}/progress",
        json=_progress_body(),
    )
    assert first.status_code == 200
    stale = _progress_body(expected_run_revision=1)
    stale["progress"]["current_beat_id"] = None
    response = client.put(f"/api/live/play-runs/{RUN_ID_A}/progress", json=stale)
    assert response.status_code == 409
    assert client.get(f"/api/live/play-runs/{RUN_ID_A}").json() == first.json()


def test_unknown_reference_is_422(client: TestClient, root: Path) -> None:
    _create_and_seal(client, root)
    body = _progress_body()
    body["progress"]["current_scene_id"] = "scene:ghost"
    response = client.put(f"/api/live/play-runs/{RUN_ID_A}/progress", json=body)
    assert response.status_code == 422
    assert client.get(f"/api/live/play-runs/{RUN_ID_A}").json()["run_revision"] == 1
