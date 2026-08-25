"""Exact, idempotent adoption of existing file-backed Plan documents."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID, uuid4

from application_state.cli import assert_at_head
from application_state.config import load_runtime_dsn
from application_state.content import repository as repo
from application_state.content.types import (
    ImportReport,
    WorkObject,
    WorkRevision,
    WorkingCopy,
    normalize_markdown,
    sha256_utf8,
)
from application_state.errors import (
    ApplicationStateConflictError,
    ApplicationStateIntegrityError,
)
from application_state.unit_of_work import unit_of_work


def _read_markdown(root: Path, relpath: str | None) -> str | None:
    if relpath is None or relpath == "":
        return None
    target = root / relpath
    if not target.is_file():
        return None
    return normalize_markdown(target.read_text(encoding="utf-8"))


def import_plans_from_registry(root: Path, records: list[object]) -> ImportReport:
    """Import kind=plan registry records. Does not switch leftover file writers.

    ``records`` are ``WorkspaceDocumentRecord``-shaped objects with attributes
    used by the predecessor mapping in the AS1 handoff.
    """
    dsn = load_runtime_dsn()
    assert_at_head(dsn=dsn)
    report = ImportReport()
    with unit_of_work(dsn) as conn:
        for record in records:
            kind = getattr(record, "kind", None)
            if kind != "plan":
                continue
            result = _import_one(conn, root, record)
            report.work_object_ids.append(str(getattr(record, "document_id")))
            if result == "imported":
                report.imported += 1
            elif result == "noop":
                report.noop += 1
            else:
                report.skipped_empty += 1
    return report


def _import_one(conn, root: Path, record: object) -> str:
    document_id = UUID(str(getattr(record, "document_id")))
    title = str(getattr(record, "title"))
    campaign_id = str(getattr(record, "campaign_id"))
    status = str(getattr(record, "status"))
    content_status = str(getattr(record, "content_status"))
    revision_n = int(getattr(record, "revision"))
    target_relpath = getattr(record, "target_relpath", None)
    target_session = getattr(record, "target_session", None)
    created_at = getattr(record, "created_at")
    updated_at = getattr(record, "updated_at")
    bytes_or_none = _read_markdown(root, target_relpath)
    if content_status == "committed" and bytes_or_none is None:
        raise ApplicationStateIntegrityError(
            f"committed plan {document_id} has no current Markdown bytes to import"
        )
    markdown = bytes_or_none if bytes_or_none is not None else ""
    digest = sha256_utf8(markdown)
    existing = repo.get_work_object(conn, document_id)
    if existing is not None:
        return _replay_or_conflict(
            conn,
            existing,
            digest=digest,
            revision_n=revision_n,
            content_status=content_status,
            markdown=markdown,
        )
    from datetime import datetime

    def _parse_dt(value: object) -> datetime:
        if isinstance(value, datetime):
            return value
        text = str(value).replace("Z", "+00:00")
        return datetime.fromisoformat(text)

    obj = WorkObject(
        work_object_id=document_id,
        kind="plan",
        campaign_id=campaign_id,
        title=title,
        target_session=target_session,
        target_relpath=target_relpath,
        status="active" if status == "active" else "discarded",
        current_revision_id=None,
        object_revision=revision_n,
        created_at=_parse_dt(created_at),
        updated_at=_parse_dt(updated_at),
    )
    repo.insert_work_object(conn, obj)
    if content_status == "committed":
        revision = WorkRevision(
            work_revision_id=uuid4(),
            work_object_id=document_id,
            revision_n=revision_n,
            markdown=markdown,
            content_sha256=digest,
            created_at=_parse_dt(created_at),
        )
        repo.insert_work_revision(conn, revision)
        updated = obj.model_copy(update={"current_revision_id": revision.work_revision_id})
        persisted = repo.update_work_object(
            conn, updated, expected_object_revision=revision_n
        )
        if persisted is None:
            raise ApplicationStateConflictError(
                f"plan import CAS failed for {document_id}"
            )
        repo.upsert_working_copy(
            conn,
            WorkingCopy(
                work_object_id=document_id,
                markdown=markdown,
                content_sha256=digest,
                base_revision_id=revision.work_revision_id,
                working_copy_revision=1,
                updated_at=_parse_dt(updated_at),
            ),
        )
        return "imported"
    if markdown == "":
        return "skipped_empty"
    repo.upsert_working_copy(
        conn,
        WorkingCopy(
            work_object_id=document_id,
            markdown=markdown,
            content_sha256=digest,
            base_revision_id=None,
            working_copy_revision=1,
            updated_at=_parse_dt(updated_at),
        ),
    )
    return "imported"


def _replay_or_conflict(
    conn,
    existing: WorkObject,
    *,
    digest: str,
    revision_n: int,
    content_status: str,
    markdown: str,
) -> str:
    if existing.object_revision != revision_n:
        raise ApplicationStateConflictError(
            f"plan {existing.work_object_id} already exists with different revision"
        )
    if content_status == "committed":
        if existing.current_revision_id is None:
            raise ApplicationStateConflictError(
                f"plan {existing.work_object_id} exists as draft; import is committed"
            )
        current = repo.get_work_revision(conn, existing.current_revision_id)
        if current is None or current.content_sha256 != digest:
            raise ApplicationStateConflictError(
                f"plan {existing.work_object_id} digest conflict; refusing overwrite"
            )
        if current.revision_n != revision_n:
            raise ApplicationStateConflictError(
                f"plan {existing.work_object_id} revision_n conflict; refusing overwrite"
            )
        return "noop"
    working = repo.get_working_copy(conn, existing.work_object_id)
    if working is None and markdown == "":
        return "noop"
    if working is not None and working.content_sha256 == digest:
        return "noop"
    raise ApplicationStateConflictError(
        f"plan {existing.work_object_id} digest conflict; refusing overwrite"
    )
