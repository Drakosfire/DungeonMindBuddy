from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from threading import Event, Thread

import pytest
from fastapi.testclient import TestClient

from apps.live_control_server.main import create_app
from apps.live_control_server.services.play_run_registry import (
    PLAY_RUN_RECORD_SCHEMA,
    PlayRunRegistryError,
    create_or_replay_play_run,
    get_play_run,
    list_play_runs,
    play_runs_dir,
)
from apps.live_control_server.services.tiptap_markdown_write import (
    TiptapMarkdownWriteCommitRequest,
    TiptapMarkdownWritePrepareRequest,
    commit_tiptap_markdown_write,
    prepare_tiptap_markdown_write,
)
from apps.live_control_server.services.workspace_document_registry import (
    WorkspaceDocumentSnapshot,
    create_workspace_document,
    get_workspace_document_snapshot,
    update_workspace_document_metadata,
)
from tests.application_state.playable_binding import (
    playable_binding,
    remember_committed_playable,
)

pytest_plugins = ["tests.application_state.conftest"]

RUN_ID_A = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
RUN_ID_B = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
RUN_ID_C = "cccccccc-cccc-4ccc-8ccc-cccccccccccc"
RUN_ID_D = "dddddddd-dddd-4ddd-8ddd-dddddddddddd"
PLAYABLE_ID = "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee"
SHA = "a" * 64


def _persist_record(root: Path, *, run_id: str, created_at: str) -> Path:
    path = play_runs_dir(root) / f"{run_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": PLAY_RUN_RECORD_SCHEMA,
                "run_id": run_id,
                "campaign_id": "longmont-c2",
                "playable_artifact_id": PLAYABLE_ID,
                "playable_revision": 7,
                "playable_content_sha256": SHA,
                "run_revision": 1,
                "created_at": created_at,
                "updated_at": created_at,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def _create_committed_runbook(root: Path) -> WorkspaceDocumentSnapshot:
    record = create_workspace_document(
        root,
        title="Concurrency Runbook",
        campaign_id="longmont-c2",
        kind="runbook",
        target_relpath=(
            "evals/c2_live_prep/mireward-prep/content/tiptap/"
            "run-binding-concurrency.md"
        ),
    )
    markdown = "# Runbook\n\nExact revision N.\n"
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


def _create_run(root: Path, snapshot: WorkspaceDocumentSnapshot, *, run_id: str) -> None:
    revision_n, sha = playable_binding(snapshot)
    create_or_replay_play_run(
        root,
        run_id=run_id,
        playable_artifact_id=snapshot.record.document_id,
        expected_playable_revision=revision_n,
        expected_playable_content_sha256=sha,
    )


def test_list_orders_mixed_timestamp_precision_by_time_then_run_id(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot = _create_committed_runbook(tmp_path)
    timestamps = iter(
        [
            "2026-08-15T12:00:00Z",
            "2026-08-15T12:00:00Z",
            "2026-08-15T12:00:00.500000Z",
            "2026-08-15T11:00:00Z",
        ]
    )

    def fake_now_utc() -> datetime:
        return datetime.fromisoformat(next(timestamps).replace("Z", "+00:00"))

    monkeypatch.setattr(
        "application_state.play.repository.now_utc",
        fake_now_utc,
    )
    _create_run(tmp_path, snapshot, run_id=RUN_ID_B)
    _create_run(tmp_path, snapshot, run_id=RUN_ID_A)
    _create_run(tmp_path, snapshot, run_id=RUN_ID_C)
    _create_run(tmp_path, snapshot, run_id=RUN_ID_D)

    assert [record.run_id for record in list_play_runs(tmp_path)] == [
        RUN_ID_C,
        RUN_ID_A,
        RUN_ID_B,
        RUN_ID_D,
    ]


def test_persisted_run_id_must_match_filename_identity(tmp_path: Path) -> None:
    path = _persist_record(
        root=tmp_path,
        run_id=RUN_ID_B,
        created_at="2026-08-15T12:00:00Z",
    )
    mismatched = play_runs_dir(tmp_path) / f"{RUN_ID_A}.json"
    path.replace(mismatched)

    with pytest.raises(PlayRunRegistryError) as exc_info:
        get_play_run(tmp_path, RUN_ID_A)

    assert exc_info.value.status_code == 404
    assert mismatched.is_file()


def test_unknown_playable_document_returns_404_and_creates_no_run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "apps.live_control_server.routes.play_runs.repo_root",
        lambda: tmp_path,
    )
    client = TestClient(create_app())

    response = client.put(
        f"/api/live/play-runs/{RUN_ID_A}",
        json={
            "playable_artifact_id": PLAYABLE_ID,
            "expected_playable_revision": 1,
            "expected_playable_content_sha256": SHA,
        },
    )

    assert response.status_code == 404
    assert not (play_runs_dir(tmp_path) / f"{RUN_ID_A}.json").exists()


def test_new_run_commit_holds_runbook_mutation_lock_through_atomic_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot = _create_committed_runbook(tmp_path)
    insert_entered = Event()
    allow_insert = Event()
    mutation_started = Event()
    mutation_done = Event()
    create_errors: list[BaseException] = []
    mutation_errors: list[BaseException] = []
    created_records = []
    real_insert_manifest = None

    import application_state.play.repository as play_repository

    real_insert_manifest = play_repository.insert_manifest

    def blocking_insert_manifest(conn, manifest):
        insert_entered.set()
        if not allow_insert.wait(timeout=2.0):
            raise AssertionError("timed out waiting to release manifest insert")
        return real_insert_manifest(conn, manifest)

    monkeypatch.setattr(
        "application_state.play.repository.insert_manifest",
        blocking_insert_manifest,
    )

    def create_run() -> None:
        try:
            created_records.append(
                create_or_replay_play_run(
                    tmp_path,
                    run_id=RUN_ID_A,
                    playable_artifact_id=snapshot.record.document_id,
                    expected_playable_revision=playable_binding(snapshot)[0],
                    expected_playable_content_sha256=playable_binding(snapshot)[1],
                )
            )
        except BaseException as exc:  # pragma: no cover - surfaced below
            create_errors.append(exc)

    def mutate_runbook() -> None:
        mutation_started.set()
        try:
            update_workspace_document_metadata(
                tmp_path,
                snapshot.record.document_id,
                title="Advanced after Run admission",
                expected_revision=snapshot.loaded_revision,
            )
        except BaseException as exc:  # pragma: no cover - surfaced below
            mutation_errors.append(exc)
        finally:
            mutation_done.set()

    create_thread = Thread(target=create_run, daemon=True)
    create_thread.start()
    assert insert_entered.wait(timeout=2.0)

    mutation_thread = Thread(target=mutate_runbook, daemon=True)
    mutation_thread.start()
    assert mutation_started.wait(timeout=2.0)

    try:
        assert not mutation_done.wait(timeout=0.2)
    finally:
        allow_insert.set()

    create_thread.join(timeout=2.0)
    mutation_thread.join(timeout=2.0)

    assert not create_thread.is_alive()
    assert not mutation_thread.is_alive()
    assert create_errors == []
    assert mutation_errors == []
    assert mutation_done.is_set()
    assert len(created_records) == 1
    assert created_records[0].playable_revision == playable_binding(snapshot)[0]
    assert created_records[0].playable_content_sha256 == snapshot.content_sha256

    advanced = get_workspace_document_snapshot(
        tmp_path,
        snapshot.record.document_id,
    )
    assert advanced.loaded_revision == snapshot.loaded_revision + 1
