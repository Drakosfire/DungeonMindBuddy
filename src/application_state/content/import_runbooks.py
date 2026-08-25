"""Exact, idempotent adoption of existing file-backed Runbook documents."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
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


@dataclass(frozen=True)
class FrozenLegacyRunbook:
    """Registry metadata + Markdown captured together under predecessor authority.

    Import never re-reads the file. A leftover revision N cannot be paired with
    later bytes because those bytes are not consulted after capture.
    """

    record: object
    markdown: str | None
    content_sha256: str


def freeze_legacy_runbook(record: object, markdown: str | None) -> FrozenLegacyRunbook:
    normalized = None if markdown is None else normalize_markdown(markdown)
    digest = sha256_utf8("" if normalized is None else normalized)
    return FrozenLegacyRunbook(record=record, markdown=normalized, content_sha256=digest)


def import_runbooks_from_snapshots(snapshots: list[FrozenLegacyRunbook]) -> ImportReport:
    """Import frozen leftover Runbook snapshots. Does not switch leftover file writers.

    Current captured bytes become one WorkRevision whose ``revision_n`` equals
    the captured registry revision. Older unseen revisions are not fabricated.
    """
    dsn = load_runtime_dsn()
    assert_at_head(dsn=dsn)
    report = ImportReport()
    with unit_of_work(dsn) as conn:
        for snapshot in snapshots:
            kind = getattr(snapshot.record, "kind", None)
            if kind != "runbook":
                continue
            result = _import_one(conn, snapshot)
            report.work_object_ids.append(str(getattr(snapshot.record, "document_id")))
            if result == "imported":
                report.imported += 1
            elif result == "noop":
                report.noop += 1
            else:
                report.skipped_empty += 1
    return report


def import_runbooks_from_registry(
    _root: object, snapshots: list[FrozenLegacyRunbook]
) -> ImportReport:
    """Compatibility wrapper: import already-frozen snapshots, never re-read files."""
    return import_runbooks_from_snapshots(snapshots)


def _import_one(conn, snapshot: FrozenLegacyRunbook) -> str:
    record = snapshot.record
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
    if snapshot.markdown is not None and sha256_utf8(snapshot.markdown) != snapshot.content_sha256:
        raise ApplicationStateIntegrityError(
            f"frozen runbook {document_id} digest does not match captured Markdown"
        )
    if content_status == "committed" and snapshot.markdown is None:
        raise ApplicationStateIntegrityError(
            f"committed runbook {document_id} has no current Markdown bytes to import"
        )
    markdown = snapshot.markdown if snapshot.markdown is not None else ""
    digest = snapshot.content_sha256
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

    def _parse_dt(value: object) -> datetime:
        if isinstance(value, datetime):
            return value
        text = str(value).replace("Z", "+00:00")
        return datetime.fromisoformat(text)

    obj = WorkObject(
        work_object_id=document_id,
        kind="runbook",
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
                f"runbook import CAS failed for {document_id}"
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
    if existing.kind != "runbook":
        raise ApplicationStateConflictError(
            f"{existing.work_object_id} already exists as kind={existing.kind}"
        )
    if existing.object_revision != revision_n:
        raise ApplicationStateConflictError(
            f"runbook {existing.work_object_id} already exists with different revision"
        )
    if content_status == "committed":
        if existing.current_revision_id is None:
            raise ApplicationStateConflictError(
                f"runbook {existing.work_object_id} exists as draft; import is committed"
            )
        current = repo.get_work_revision(conn, existing.current_revision_id)
        if current is None or current.content_sha256 != digest:
            raise ApplicationStateConflictError(
                f"runbook {existing.work_object_id} digest conflict; refusing overwrite"
            )
        if current.revision_n != revision_n:
            raise ApplicationStateConflictError(
                f"runbook {existing.work_object_id} revision_n conflict; refusing overwrite"
            )
        return "noop"
    working = repo.get_working_copy(conn, existing.work_object_id)
    if working is None and markdown == "":
        return "noop"
    if working is not None and working.content_sha256 == digest:
        return "noop"
    raise ApplicationStateConflictError(
        f"runbook {existing.work_object_id} digest conflict; refusing overwrite"
    )
