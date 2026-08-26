from __future__ import annotations

import uuid
from pathlib import Path
from threading import Event, Thread

import pytest

from apps.live_control_server.services.play_run_registry import (
    PlayRunRecord,
    PlayRunRegistryError,
    create_or_replay_play_run,
    get_play_run,
    play_run_path,
)
from apps.live_control_server.services.play_run_reference_manifest import (
    PlayRunReferenceManifestError,
    derive_sealed_manifest,
    play_run_reference_manifest_path,
    seal_or_replay_play_run_reference_manifest,
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
from application_state.play.import_runtime import import_play_runtime_from_legacy_files
from src.live_play.live_store import write_json
from tests.application_state.play_runtime_helpers import SOURCE_MARKDOWN


def _write_legacy_run_files(
    root: Path,
    *,
    run_id: str,
    record: WorkspaceDocumentRecord,
    markdown: str,
    playable_revision: int,
    playable_content_sha256: str,
) -> None:
    now = "2026-01-01T00:00:00Z"
    run = PlayRunRecord(
        run_id=run_id,
        campaign_id=record.campaign_id,
        playable_artifact_id=record.document_id,
        playable_revision=playable_revision,
        playable_content_sha256=playable_content_sha256,
        created_at=now,
        updated_at=now,
    )
    run_path = play_run_path(root, run_id)
    run_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(run_path, run.model_dump(mode="json"))
    manifest = derive_sealed_manifest(
        markdown,
        run_id=run_id,
        playable_artifact_id=record.document_id,
        playable_revision=playable_revision,
        playable_content_sha256=playable_content_sha256,
        sealed_at=now,
    )
    manifest_path = play_run_reference_manifest_path(root, run_id)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(manifest_path, manifest.model_dump(mode="json", exclude_none=True))

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


def _persist_pre_as2_play_run(
    root: Path,
    *,
    playable_artifact_id: str,
    playable_revision: int,
    playable_content_sha256: str,
    campaign_id: str,
    run_id: str = RUN_ID_A,
) -> None:
    """Write a file-backed Run as it existed before AS2 Content import."""
    now = "2026-01-01T00:00:00Z"
    record = PlayRunRecord(
        run_id=run_id,
        campaign_id=campaign_id,
        playable_artifact_id=playable_artifact_id,
        playable_revision=playable_revision,
        playable_content_sha256=playable_content_sha256,
        created_at=now,
        updated_at=now,
    )
    path = play_run_path(root, run_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json(path, record.model_dump(mode="json"))


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
    record = record.model_copy(
        update={
            "target_relpath": "evals/c2_live_prep/mireward-prep/content/tiptap/legacy-play.md"
        }
    )
    (tmp_path / str(record.target_relpath)).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / str(record.target_relpath)).write_text(SOURCE_MARKDOWN, encoding="utf-8")
    digest = sha256_utf8(SOURCE_MARKDOWN)
    _write_leftover_registry(tmp_path, record)
    _write_legacy_run_files(
        tmp_path,
        run_id=RUN_ID_A,
        record=record,
        markdown=SOURCE_MARKDOWN,
        playable_revision=17,
        playable_content_sha256=digest,
    )
    with pytest.raises(PlayRunRegistryError):
        get_play_run(tmp_path, RUN_ID_A)
    with pytest.raises(WorkspaceDocumentRegistryError):
        get_committed_playable_revision(record.document_id)

    import_runbooks_from_snapshots(capture_legacy_runbook_snapshots(tmp_path))
    import_play_runtime_from_legacy_files(tmp_path)

    loaded = get_play_run(tmp_path, RUN_ID_A)
    assert loaded.playable_revision == 17
    assert loaded.playable_content_sha256 == digest
    replayed = create_or_replay_play_run(
        tmp_path,
        run_id=RUN_ID_A,
        playable_artifact_id=record.document_id,
        expected_playable_revision=17,
        expected_playable_content_sha256=digest,
    )
    assert replayed.playable_revision == 17
    manifest = seal_or_replay_play_run_reference_manifest(tmp_path, RUN_ID_A)
    assert manifest.playable_revision == 17
    assert manifest.playable_content_sha256 == digest
    assert manifest.playable_artifact_id == record.document_id
    assert play_run_path(tmp_path, RUN_ID_A).is_file()


def test_missing_historical_legacy_run_fails_through_play_admission(
    tmp_path: Path, application_state_dsn: str
) -> None:
    record, markdown_17 = _legacy_file_runbook(tmp_path, revision=17)
    digest_16 = sha256_utf8(SOURCE_MARKDOWN)
    digest_17 = sha256_utf8(markdown_17)
    _write_leftover_registry(tmp_path, record)
    _write_legacy_run_files(
        tmp_path,
        run_id=RUN_ID_A,
        record=record,
        markdown=SOURCE_MARKDOWN,
        playable_revision=16,
        playable_content_sha256=digest_16,
    )
    with pytest.raises(PlayRunRegistryError):
        get_play_run(tmp_path, RUN_ID_A)

    import_runbooks_from_snapshots(capture_legacy_runbook_snapshots(tmp_path))
    with pytest.raises(ApplicationStateNotFoundError, match="historical revision bytes were never retained"):
        import_play_runtime_from_legacy_files(tmp_path)

    with pytest.raises(PlayRunRegistryError):
        get_play_run(tmp_path, RUN_ID_A)
    assert play_run_reference_manifest_path(tmp_path, RUN_ID_A).is_file()
    current = get_committed_playable_revision(record.document_id)
    assert current.revision_n == 17
    assert current.content_sha256 == digest_17
    created = create_or_replay_play_run(
        tmp_path,
        run_id=RUN_ID_A,
        playable_artifact_id=record.document_id,
        expected_playable_revision=17,
        expected_playable_content_sha256=digest_17,
    )
    assert created.playable_revision == 17
    assert created.playable_content_sha256 == digest_17
    assert get_play_run(tmp_path, RUN_ID_A).playable_revision == 17
    assert play_run_path(tmp_path, RUN_ID_A).is_file()
    with pytest.raises(PlayRunRegistryError, match="already bound to a different Playable revision"):
        create_or_replay_play_run(
            tmp_path,
            run_id=RUN_ID_A,
            playable_artifact_id=record.document_id,
            expected_playable_revision=16,
            expected_playable_content_sha256=digest_16,
        )
