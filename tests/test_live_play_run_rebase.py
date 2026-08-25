from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.live_control_server.main import create_app
from apps.live_control_server.services.play_run_rebase import play_run_rebase_intent_path
from apps.live_control_server.services.play_run_registry import play_run_path
from apps.live_control_server.services.play_run_reference_manifest import (
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
    get_committed_playable_revision,
    get_workspace_document_snapshot,
)
from src.live_play.live_store import write_json

pytest_plugins = ["tests.application_state.conftest"]

_PLAYABLE_BY_SHA: dict[tuple[str, str], int] = {}


@pytest.fixture(autouse=True)
def _application_state(application_state_dsn: str) -> str:
    _PLAYABLE_BY_SHA.clear()
    return application_state_dsn


def _remember_playable(snapshot: WorkspaceDocumentSnapshot) -> WorkspaceDocumentSnapshot:
    if snapshot.record.kind != "runbook":
        return snapshot
    committed = get_committed_playable_revision(snapshot.record.document_id, kind=None)
    if committed.content_sha256 == snapshot.content_sha256:
        _PLAYABLE_BY_SHA[(snapshot.record.document_id, snapshot.content_sha256)] = (
            committed.revision_n
        )
    return snapshot


def _playable(snapshot: WorkspaceDocumentSnapshot) -> tuple[int, str]:
    key = (snapshot.record.document_id, snapshot.content_sha256)
    remembered = _PLAYABLE_BY_SHA.get(key)
    if remembered is not None:
        return remembered, snapshot.content_sha256
    committed = get_committed_playable_revision(snapshot.record.document_id, kind=None)
    return committed.revision_n, committed.content_sha256


RUN_ID_A = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"

SOURCE_MARKDOWN = "\n".join(
    [
        "<!-- dmb-playable-element:v1 kind=scene id=scene:gate -->",
        "## The Gate",
        "",
        "<!-- dmb-playable-element:v1 kind=beat id=beat:arrival -->",
        "### Arrival",
        "",
        "<!-- dmb-playable-element:v1 kind=beat id=beat:briefing -->",
        "### Briefing",
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

SURVIVING_TARGET_MARKDOWN = SOURCE_MARKDOWN + "\n".join(
    [
        "<!-- dmb-playable-element:v1 kind=scene id=scene:keep -->",
        "## The Keep",
        "",
        "<!-- dmb-playable-element:v1 kind=beat id=beat:inside -->",
        "### Inside",
        "",
    ]
)

REPLACED_TARGET_MARKDOWN = "\n".join(
    [
        "<!-- dmb-playable-element:v1 kind=scene id=scene:harbor -->",
        "## Harbor",
        "",
        "<!-- dmb-playable-element:v1 kind=beat id=beat:dock -->",
        "### Dock",
        "",
    ]
)


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
    return _remember_playable(get_workspace_document_snapshot(root, record.document_id))


def _create_committed_runbook(root: Path) -> WorkspaceDocumentSnapshot:
    record = create_workspace_document(
        root,
        title="Runbook rebase-http",
        campaign_id="longmont-c2",
        kind="runbook",
        target_relpath=(
            "evals/c2_live_prep/mireward-prep/content/tiptap/rebase-http.md"
        ),
    )
    return _commit_record(root, record, SOURCE_MARKDOWN)


def _run_request(snapshot: WorkspaceDocumentSnapshot) -> dict[str, object]:
    return {
        "playable_artifact_id": snapshot.record.document_id,
        "expected_playable_revision": _playable(snapshot)[0],
        "expected_playable_content_sha256": _playable(snapshot)[1],
    }


def _rebase_body(snapshot: WorkspaceDocumentSnapshot, expected_run_revision: int) -> dict[str, object]:
    return {
        "expected_run_revision": expected_run_revision,
        "target_playable_revision": _playable(snapshot)[0],
        "target_playable_content_sha256": _playable(snapshot)[1],
    }


def _create_and_seal(
    client: TestClient,
    root: Path,
) -> WorkspaceDocumentSnapshot:
    snapshot = _create_committed_runbook(root)
    created = client.put(f"/api/live/play-runs/{RUN_ID_A}", json=_run_request(snapshot))
    assert created.status_code == 200
    sealed = client.put(f"/api/live/play-runs/{RUN_ID_A}/reference-manifest")
    assert sealed.status_code == 200
    return snapshot


def test_http_rebase_round_trip_and_replay(client: TestClient, root: Path) -> None:
    source = _create_and_seal(client, root)
    target = _commit_record(root, source.record, SURVIVING_TARGET_MARKDOWN)

    first = client.put(
        f"/api/live/play-runs/{RUN_ID_A}/rebase",
        json=_rebase_body(target, expected_run_revision=1),
    )
    assert first.status_code == 200
    body = first.json()
    assert body["run_revision"] == 2
    assert body["rebased_from_run_revision"] == 1
    assert body["playable_revision"] == _playable(target)[0]
    assert body["playable_content_sha256"] == target.content_sha256
    assert body["progress"]["current_scene_id"] is None
    assert not play_run_rebase_intent_path(root, RUN_ID_A).exists()

    fetched = client.get(f"/api/live/play-runs/{RUN_ID_A}")
    assert fetched.status_code == 200
    assert fetched.json() == body
    run_bytes = play_run_path(root, RUN_ID_A).read_bytes()

    replay = client.put(
        f"/api/live/play-runs/{RUN_ID_A}/rebase",
        json=_rebase_body(target, expected_run_revision=1),
    )
    assert replay.status_code == 200
    assert replay.json() == body
    assert play_run_path(root, RUN_ID_A).read_bytes() == run_bytes

    current = client.put(
        f"/api/live/play-runs/{RUN_ID_A}/rebase",
        json=_rebase_body(target, expected_run_revision=2),
    )
    assert current.status_code == 200
    assert current.json() == body


def test_http_removed_refs_are_409(client: TestClient, root: Path) -> None:
    source = _create_and_seal(client, root)
    progress = client.put(
        f"/api/live/play-runs/{RUN_ID_A}/progress",
        json={
            "expected_run_revision": 1,
            "progress": {
                "current_scene_id": "scene:gate",
                "current_beat_id": "beat:arrival",
                "resolved_beat_ids": ["beat:briefing"],
                "selections": {"choice:route": "option:fire"},
                "notes_by_element_id": {"beat:arrival": "Door barred."},
            },
        },
    )
    assert progress.status_code == 200
    run_before = play_run_path(root, RUN_ID_A).read_bytes()
    target = _commit_record(root, source.record, REPLACED_TARGET_MARKDOWN)
    response = client.put(
        f"/api/live/play-runs/{RUN_ID_A}/rebase",
        json=_rebase_body(target, expected_run_revision=2),
    )
    assert response.status_code == 409
    assert "scene:gate" in response.json()["detail"]
    assert play_run_path(root, RUN_ID_A).read_bytes() == run_before
    assert not play_run_rebase_intent_path(root, RUN_ID_A).exists()


def test_http_pending_intent_is_503(
    client: TestClient,
    root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = _create_and_seal(client, root)
    target = _commit_record(root, source.record, SURVIVING_TARGET_MARKDOWN)
    original = write_json

    def boom(path: Path, data: dict) -> None:
        if path == play_run_reference_manifest_path(root, RUN_ID_A) and play_run_rebase_intent_path(
            root, RUN_ID_A
        ).is_file():
            raise OSError("stop after intent")
        original(path, data)

    monkeypatch.setattr(
        "apps.live_control_server.services.play_run_rebase.write_json",
        boom,
    )
    failed = client.put(
        f"/api/live/play-runs/{RUN_ID_A}/rebase",
        json=_rebase_body(target, expected_run_revision=1),
    )
    assert failed.status_code == 503
    assert play_run_rebase_intent_path(root, RUN_ID_A).is_file()

    assert client.get(f"/api/live/play-runs/{RUN_ID_A}").status_code == 503
    assert client.get("/api/live/play-runs").status_code == 503
    assert client.get(f"/api/live/play-runs/{RUN_ID_A}/reference-manifest").status_code == 503
    assert client.put(
        f"/api/live/play-runs/{RUN_ID_A}/reference-manifest"
    ).status_code == 503
    assert client.put(
        f"/api/live/play-runs/{RUN_ID_A}",
        json=_run_request(source),
    ).status_code == 503
    assert client.put(
        f"/api/live/play-runs/{RUN_ID_A}/progress",
        json={
            "expected_run_revision": 1,
            "progress": {
                "current_scene_id": None,
                "current_beat_id": None,
                "resolved_beat_ids": [],
                "selections": {},
                "notes_by_element_id": {},
            },
        },
    ).status_code == 503

    monkeypatch.setattr(
        "apps.live_control_server.services.play_run_rebase.write_json",
        original,
    )
    recovered = client.put(
        f"/api/live/play-runs/{RUN_ID_A}/rebase",
        json=_rebase_body(target, expected_run_revision=1),
    )
    assert recovered.status_code == 200
    assert recovered.json()["run_revision"] == 2
    assert client.get(f"/api/live/play-runs/{RUN_ID_A}").status_code == 200


def test_http_completed_replay_requires_intact_manifest(client: TestClient, root: Path) -> None:
    source = _create_and_seal(client, root)
    target = _commit_record(root, source.record, SURVIVING_TARGET_MARKDOWN)
    first = client.put(
        f"/api/live/play-runs/{RUN_ID_A}/rebase",
        json=_rebase_body(target, expected_run_revision=1),
    )
    assert first.status_code == 200
    play_run_reference_manifest_path(root, RUN_ID_A).write_text("{}\n", encoding="utf-8")
    replay = client.put(
        f"/api/live/play-runs/{RUN_ID_A}/rebase",
        json=_rebase_body(target, expected_run_revision=1),
    )
    assert replay.status_code == 500
    assert client.get(f"/api/live/play-runs/{RUN_ID_A}").json()["run_revision"] == 2
