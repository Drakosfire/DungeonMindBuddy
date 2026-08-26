"""Content-owned Playable admission for a shared Play unit of work."""

from __future__ import annotations

from uuid import UUID

import psycopg
from psycopg.rows import dict_row

from application_state.content import repository as repo
from application_state.content.types import CommittedPlayableRevision, WorkObject, WorkRevision
from application_state.errors import (
    ApplicationStateConflictError,
    ApplicationStateNotFoundError,
    ApplicationStateValidationError,
)


def _as_uuid(value: UUID | str, *, field_name: str) -> UUID:
    if isinstance(value, UUID):
        return value
    try:
        parsed = UUID(str(value))
    except (AttributeError, TypeError, ValueError) as exc:
        raise ApplicationStateValidationError(f"{field_name} must be a UUID") from exc
    if str(value) != str(parsed):
        raise ApplicationStateValidationError(f"{field_name} must be a canonical UUID")
    return parsed


def admit_playable_revision(
    conn: psycopg.Connection,
    work_object_id: UUID | str,
    revision_n: int,
    expected_sha256: str,
    *,
    require_current: bool = False,
    require_clean: bool = False,
) -> CommittedPlayableRevision:
    """Admit an exact committed Runbook WorkRevision on ``conn``.

    Does not commit. Callers must hold the surrounding Play unit of work.
    """
    if not isinstance(revision_n, int) or isinstance(revision_n, bool) or revision_n <= 0:
        raise ApplicationStateValidationError("revision_n must be a positive integer")
    digest = expected_sha256.strip()
    if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
        raise ApplicationStateValidationError(
            "expected_sha256 must be 64 lowercase hex characters"
        )
    object_id = _as_uuid(work_object_id, field_name="work_object_id")
    obj = repo.lock_work_object(conn, object_id)
    if obj is None:
        raise ApplicationStateNotFoundError(
            f"workspace document not found: {object_id}"
        )
    if obj.kind != "runbook":
        raise ApplicationStateValidationError(
            "playable_artifact_id must identify a runbook workspace document"
        )
    if obj.status != "active":
        raise ApplicationStateConflictError("runbook workspace document is discarded")
    if obj.current_revision_id is None:
        raise ApplicationStateConflictError(
            "runbook workspace document is not committed"
        )
    revision = _lock_work_revision_for_share(conn, object_id, revision_n)
    if revision is None:
        raise ApplicationStateNotFoundError(
            "historical revision bytes were never retained"
        )
    if revision.content_sha256 != digest:
        raise ApplicationStateConflictError("playable content SHA mismatch")
    current = repo.get_work_revision(conn, obj.current_revision_id)
    if current is None:
        raise ApplicationStateConflictError(
            "committed workspace document is missing its WorkRevision"
        )
    if require_current and revision.work_revision_id != current.work_revision_id:
        raise ApplicationStateConflictError(
            "playable revision mismatch: "
            f"expected {revision_n}, current {current.revision_n}"
        )
    working = repo.get_working_copy(conn, object_id)
    divergent = (
        working is not None and working.content_sha256 != current.content_sha256
    )
    if require_clean and divergent:
        raise ApplicationStateConflictError(
            "runbook workspace document is not committed"
        )
    return CommittedPlayableRevision(
        work_object=obj,
        work_revision=revision,
        has_divergent_working_copy=divergent,
    )


def _lock_work_revision_for_share(
    conn: psycopg.Connection, work_object_id: UUID, revision_n: int
) -> WorkRevision | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT work_revision_id, work_object_id, revision_n, markdown,
                   content_sha256, created_at
            FROM content.work_revision
            WHERE work_object_id = %s AND revision_n = %s
            FOR SHARE
            """,
            (work_object_id, revision_n),
        )
        row = cur.fetchone()
    return None if row is None else WorkRevision.model_validate(row)


def require_runbook_work_object(obj: WorkObject) -> None:
    if obj.kind != "runbook":
        raise ApplicationStateValidationError(
            "playable_artifact_id must identify a runbook workspace document"
        )
