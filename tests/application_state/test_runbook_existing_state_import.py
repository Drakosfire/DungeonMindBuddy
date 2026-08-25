from __future__ import annotations

import uuid
from pathlib import Path
from threading import Event, Thread

import pytest

from apps.live_control_server.services.play_run_registry import (
    create_or_replay_play_run,
    get_play_run,
)
from apps.live_control_server.services.registry_file_lock import (
    registry_mutation_lock,
    workspace_document_mutation_lock,
)
from apps.live_control_server.services.workspace_document_registry import (
    WorkspaceDocumentRecord,
    WorkspaceDocumentRegistryDocument,
    WorkspaceDocumentRegistryError,
    capture_legacy_runbook_snapshots,
    get_committed_playable_revision,
    get_workspace_document_snapshot,
    workspace_documents_path,
)
from application_state.content.import_runbooks import (
    freeze_legacy_runbook,
    import_runbooks_from_snapshots,
)
from application_state.content.service import commit_runbook, exact_committed_revision
from application_state.content.types import sha256_utf8
from application_state.errors import ApplicationStateConflictError, ApplicationStateNotFoundError
from src.live_play.live_store import write_json

RUN_ID_A = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"


def _legacy_file_runbook(root: Path, *, revision: int = 17) -> tuple[WorkspaceDocumentRecord, str]:
    document_id = str(uuid.uuid4())
    relpath = f"out/workspace/runbooks/{document_id}.md"
    markdown = "# imported exactly\n"
    target = root / relpath
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(markdown, encoding="utf-8")
    now = "2026-01-01T00:00:00Z"
    record = WorkspaceDocumentRecord(
        document_id=document_id,
        title="Legacy Runbook",
        campaign_id="longmont-c2",
        target_session=23,
        kind="runbook",
        target_relpath=relpath,
        status="active",
        content_status="committed",
        revision=revision,
        created_at=now,
        updated_at=now,
    )
    return record, markdown


def _write_leftover_registry(root: Path, record: WorkspaceDocumentRecord) -> None:
    path = workspace_documents_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json(path, WorkspaceDocumentRegistryDocument(records=[record]).model_dump(mode="json"))


def test_import_exact_revision_n_and_idempotent(
    tmp_path: Path, application_state_dsn: str
) -> None:
    source_root = tmp_path / "legacy"
    source_root.mkdir()
    record, markdown = _legacy_file_runbook(source_root, revision=17)
    snapshot = freeze_legacy_runbook(record, markdown)
    report = import_runbooks_from_snapshots([snapshot])
    assert report.imported == 1
    replay = import_runbooks_from_snapshots([snapshot])
    assert replay.imported == 0
    assert replay.noop == 1
    loaded = get_workspace_document_snapshot(tmp_path, record.document_id)
    assert loaded.markdown == "# imported exactly\n"
    committed = get_committed_playable_revision(record.document_id)
    assert committed.revision_n == 17
    assert committed.markdown == "# imported exactly\n"
    with pytest.raises(ApplicationStateNotFoundError, match="historical revision bytes were never retained"):
        exact_committed_revision(record.document_id, 16, kind="runbook")


def test_import_conflict_fails_closed(tmp_path: Path, application_state_dsn: str) -> None:
    source_root = tmp_path / "legacy"
    source_root.mkdir()
    record, markdown = _legacy_file_runbook(source_root, revision=17)
    import_runbooks_from_snapshots([freeze_legacy_runbook(record, markdown)])
    conflict = freeze_legacy_runbook(record, "# different bytes\n")
    with pytest.raises(ApplicationStateConflictError):
        import_runbooks_from_snapshots([conflict])
    committed = get_committed_playable_revision(record.document_id)
    assert committed.markdown == "# imported exactly\n"


def test_next_save_after_legacy_17_is_revision_18(
    tmp_path: Path, application_state_dsn: str
) -> None:
    source_root = tmp_path / "legacy"
    source_root.mkdir()
    record, markdown = _legacy_file_runbook(source_root, revision=17)
    import_runbooks_from_snapshots([freeze_legacy_runbook(record, markdown)])
    obj, next_revision = commit_runbook(
        record.document_id,
        "# next save\n",
        expected_revision=17,
    )
    assert next_revision.revision_n == 18
    assert exact_committed_revision(record.document_id, 17, kind="runbook").work_revision.markdown == (
        "# imported exactly\n"
    )
    assert obj.object_revision >= 18


def test_import_uses_frozen_bytes_not_later_file(
    tmp_path: Path, application_state_dsn: str
) -> None:
    source_root = tmp_path / "legacy"
    source_root.mkdir()
    record, markdown = _legacy_file_runbook(source_root, revision=17)
    frozen = freeze_legacy_runbook(record, markdown)
    (source_root / str(record.target_relpath)).write_text("# later file bytes\n", encoding="utf-8")
    import_runbooks_from_snapshots([frozen])
    committed = get_committed_playable_revision(record.document_id)
    assert committed.revision_n == 17
    assert committed.markdown == "# imported exactly\n"
    assert committed.content_sha256 == sha256_utf8("# imported exactly\n")


def test_capture_under_lock_cannot_pair_revision_n_with_later_bytes(
    tmp_path: Path, application_state_dsn: str
) -> None:
    record, markdown_a = _legacy_file_runbook(tmp_path, revision=17)
    _write_leftover_registry(tmp_path, record)
    later = "# revision 18 bytes\n"
    captured: list = []
    hold_writer = Event()
    writer_entered = Event()

    def capture() -> None:
        captured.extend(capture_legacy_runbook_snapshots(tmp_path))

    def writer() -> None:
        with workspace_document_mutation_lock(tmp_path, record.document_id):
            writer_entered.set()
            hold_writer.wait(timeout=2.0)
            target = tmp_path / str(record.target_relpath)
            target.write_text(later, encoding="utf-8")
            bumped = record.model_copy(update={"revision": 18, "updated_at": "2026-01-01T00:00:01Z"})
            with registry_mutation_lock(workspace_documents_path(tmp_path)):
                write_json(
                    workspace_documents_path(tmp_path),
                    WorkspaceDocumentRegistryDocument(records=[bumped]).model_dump(mode="json"),
                )

    capture_thread = Thread(target=capture, daemon=True)
    writer_thread = Thread(target=writer, daemon=True)
    writer_thread.start()
    assert writer_entered.wait(timeout=2.0)
    capture_thread.start()
    hold_writer.set()
    writer_thread.join(timeout=2.0)
    capture_thread.join(timeout=2.0)
    assert captured, "capture produced no snapshot"
    snapshot = captured[0]
    import_runbooks_from_snapshots([snapshot])
    committed = get_committed_playable_revision(record.document_id)
    assert committed.revision_n == snapshot.record.revision
    assert committed.content_sha256 == snapshot.content_sha256
    assert not (committed.revision_n == 17 and committed.markdown == later)
    del markdown_a


def test_existing_legacy_run_survives_import_through_play_admission(
    tmp_path: Path, application_state_dsn: str
) -> None:
    record, markdown = _legacy_file_runbook(tmp_path, revision=17)
    digest = sha256_utf8(markdown)
    import_runbooks_from_snapshots([freeze_legacy_runbook(record, markdown)])
    created = create_or_replay_play_run(
        tmp_path,
        run_id=RUN_ID_A,
        playable_artifact_id=record.document_id,
        expected_playable_revision=17,
        expected_playable_content_sha256=digest,
    )
    loaded = get_play_run(tmp_path, RUN_ID_A)
    admitted = get_committed_playable_revision(
        loaded.playable_artifact_id,
        revision_n=loaded.playable_revision,
        expected_sha256=loaded.playable_content_sha256,
    )
    assert created.playable_revision == 17
    assert admitted.revision_n == 17
    assert admitted.markdown == markdown
    assert admitted.content_sha256 == digest


def test_missing_historical_legacy_run_fails_through_play_admission(
    tmp_path: Path, application_state_dsn: str
) -> None:
    record, markdown = _legacy_file_runbook(tmp_path, revision=17)
    import_runbooks_from_snapshots([freeze_legacy_runbook(record, markdown)])
    with pytest.raises(
        WorkspaceDocumentRegistryError,
        match="historical revision bytes were never retained",
    ):
        get_committed_playable_revision(
            record.document_id,
            revision_n=16,
            expected_sha256=sha256_utf8(markdown),
        )
