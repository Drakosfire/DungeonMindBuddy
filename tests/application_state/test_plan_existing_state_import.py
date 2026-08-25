from __future__ import annotations

from pathlib import Path

import pytest

from apps.live_control_server.services.workspace_document_registry import (
    WorkspaceDocumentRecord,
    create_workspace_document,
    get_workspace_document_snapshot,
    mark_workspace_document_committed,
)
from application_state.content.import_plans import import_plans_from_registry
from application_state.errors import ApplicationStateConflictError


def _file_plan(root: Path, *, revision: int = 3, committed: bool = True) -> WorkspaceDocumentRecord:
    monkey = pytest.MonkeyPatch()
    monkey.delenv("DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL", raising=False)
    try:
        record = create_workspace_document(
            root,
            title="Legacy Plan",
            campaign_id="longmont-c2",
            kind="plan",
            target_session=24,
        )
        target = root / str(record.target_relpath)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("# imported exactly\n", encoding="utf-8")
        if committed:
            record = mark_workspace_document_committed(root, record.document_id)
        # The registry revision after commit is 2 by default; rewrite the stored
        # revision number by importing the in-memory record with an explicit n.
        return record.model_copy(update={"revision": revision})
    finally:
        monkey.undo()


def test_import_exact_and_idempotent(tmp_path: Path, application_state_dsn: str) -> None:
    source_root = tmp_path / "legacy"
    source_root.mkdir()
    record = _file_plan(source_root, revision=7)
    report = import_plans_from_registry(source_root, [record])
    assert report.imported == 1
    replay = import_plans_from_registry(source_root, [record])
    assert replay.imported == 0
    assert replay.noop == 1
    snapshot = get_workspace_document_snapshot(tmp_path, record.document_id)
    assert snapshot.markdown == "# imported exactly\n"
    assert snapshot.record.revision == 7
    assert snapshot.record.document_id == record.document_id


def test_import_conflict_fails_closed(tmp_path: Path, application_state_dsn: str) -> None:
    source_root = tmp_path / "legacy"
    source_root.mkdir()
    record = _file_plan(source_root, revision=4)
    import_plans_from_registry(source_root, [record])
    conflict = record.model_copy(update={})
    target = source_root / str(record.target_relpath)
    target.write_text("# different bytes\n", encoding="utf-8")
    with pytest.raises(ApplicationStateConflictError):
        import_plans_from_registry(source_root, [conflict])
    snapshot = get_workspace_document_snapshot(tmp_path, record.document_id)
    assert snapshot.markdown == "# imported exactly\n"
