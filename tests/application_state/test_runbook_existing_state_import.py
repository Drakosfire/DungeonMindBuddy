from __future__ import annotations

import uuid
from pathlib import Path

import pytest

from apps.live_control_server.services.workspace_document_registry import (
    WorkspaceDocumentRecord,
    get_committed_playable_revision,
    get_workspace_document_snapshot,
)
from application_state.content.import_runbooks import import_runbooks_from_registry
from application_state.content.service import commit_runbook, exact_committed_revision
from application_state.errors import ApplicationStateConflictError, ApplicationStateNotFoundError


def _legacy_file_runbook(root: Path, *, revision: int = 17) -> WorkspaceDocumentRecord:
    document_id = str(uuid.uuid4())
    relpath = f"out/workspace/runbooks/{document_id}.md"
    target = root / relpath
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("# imported exactly\n", encoding="utf-8")
    now = "2026-01-01T00:00:00Z"
    return WorkspaceDocumentRecord(
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


def test_import_exact_revision_n_and_idempotent(
    tmp_path: Path, application_state_dsn: str
) -> None:
    source_root = tmp_path / "legacy"
    source_root.mkdir()
    record = _legacy_file_runbook(source_root, revision=17)
    report = import_runbooks_from_registry(source_root, [record])
    assert report.imported == 1
    replay = import_runbooks_from_registry(source_root, [record])
    assert replay.imported == 0
    assert replay.noop == 1
    snapshot = get_workspace_document_snapshot(tmp_path, record.document_id)
    assert snapshot.markdown == "# imported exactly\n"
    committed = get_committed_playable_revision(record.document_id)
    assert committed.revision_n == 17
    assert committed.markdown == "# imported exactly\n"
    with pytest.raises(ApplicationStateNotFoundError, match="historical revision bytes were never retained"):
        exact_committed_revision(record.document_id, 16, kind="runbook")


def test_import_conflict_fails_closed(tmp_path: Path, application_state_dsn: str) -> None:
    source_root = tmp_path / "legacy"
    source_root.mkdir()
    record = _legacy_file_runbook(source_root, revision=17)
    import_runbooks_from_registry(source_root, [record])
    conflict = record.model_copy(update={})
    target = source_root / str(record.target_relpath)
    target.write_text("# different bytes\n", encoding="utf-8")
    with pytest.raises(ApplicationStateConflictError):
        import_runbooks_from_registry(source_root, [conflict])
    committed = get_committed_playable_revision(record.document_id)
    assert committed.markdown == "# imported exactly\n"


def test_next_save_after_legacy_17_is_revision_18(
    tmp_path: Path, application_state_dsn: str
) -> None:
    source_root = tmp_path / "legacy"
    source_root.mkdir()
    record = _legacy_file_runbook(source_root, revision=17)
    import_runbooks_from_registry(source_root, [record])
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
