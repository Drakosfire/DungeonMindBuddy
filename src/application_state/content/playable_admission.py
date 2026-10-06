"""Content-owned Playable admission for a shared Play unit of work."""

from __future__ import annotations

from uuid import UUID

import psycopg
from psycopg.rows import dict_row

from application_state.content import repository as repo
from application_state.content.types import (
    CommittedPlayableRevision,
    WorkObject,
    WorkRevision,
    sha256_utf8,
)
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
    expected_world_id: str | None = None,
    require_current: bool = False,
    require_clean: bool = False,
) -> CommittedPlayableRevision:
    """Admit an exact committed Playable WorkRevision on ``conn``.

    World Runs may be sourced from World Plans or World Runbooks. Campaign
    Runs remain Runbook-only. Does not commit; callers hold the Play unit of
    work.
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
    if expected_world_id is None:
        require_runbook_work_object(obj)
        if obj.world_id is not None:
            raise ApplicationStateValidationError(
                "World-owned Runbooks cannot start a campaign PlayRun V1"
            )
        if obj.campaign_id is None:
            raise ApplicationStateConflictError(
                "campaign PlayRun requires a campaign-owned Runbook"
            )
    else:
        if obj.kind not in {"plan", "runbook"}:
            raise ApplicationStateValidationError(
                "playable_artifact_id must identify a World Plan or Runbook"
            )
        if not expected_world_id.strip() or expected_world_id != expected_world_id.strip():
            raise ApplicationStateValidationError("world_id must be non-empty and canonical")
        if obj.world_id != expected_world_id or obj.campaign_id is not None:
            raise ApplicationStateConflictError(
                "selected World does not own the Runbook"
            )
    if obj.status != "active":
        raise ApplicationStateConflictError("playable workspace document is discarded")
    if obj.current_revision_id is None:
        raise ApplicationStateConflictError(
            "playable workspace document is not committed"
        )
    revision = _lock_work_revision_for_share(conn, object_id, revision_n)
    if revision is None:
        raise ApplicationStateNotFoundError(
            "historical revision bytes were never retained"
        )
    if revision.content_sha256 != digest:
        raise ApplicationStateConflictError("playable content SHA mismatch")
    if revision.work_object_id != obj.work_object_id or revision.world_id != obj.world_id:
        raise ApplicationStateConflictError(
            "playable revision owner does not match its WorkObject"
        )
    if sha256_utf8(revision.markdown) != revision.content_sha256:
        raise ApplicationStateConflictError(
            "playable revision content SHA does not match its Markdown"
        )
    current = repo.get_work_revision(conn, obj.current_revision_id)
    if current is None:
        raise ApplicationStateConflictError(
            "committed workspace document is missing its WorkRevision"
        )
    if (
        current.work_object_id != obj.work_object_id
        or current.world_id != obj.world_id
        or sha256_utf8(current.markdown) != current.content_sha256
    ):
        raise ApplicationStateConflictError(
            "current playable revision owner or digest does not match its WorkObject"
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


def resolve_pinned_playable_revision(
    conn: psycopg.Connection,
    work_object_id: UUID | str,
    revision_n: int,
    work_revision_id: UUID | str,
    expected_sha256: str,
    *,
    expected_world_id: str,
) -> WorkRevision:
    """Verify an existing World Run's exact retained immutable Runbook pin.

    Unlike admission for a new Run or rebase target, an existing binding remains
    readable after its source document is discarded or advances to another
    current revision. The exact WorkObject and WorkRevision ownership and digest
    still have to agree.
    """
    if not isinstance(revision_n, int) or isinstance(revision_n, bool) or revision_n <= 0:
        raise ApplicationStateValidationError("revision_n must be a positive integer")
    if (
        not isinstance(expected_world_id, str)
        or not expected_world_id.strip()
        or expected_world_id != expected_world_id.strip()
    ):
        raise ApplicationStateValidationError("world_id must be non-empty and canonical")
    if (
        not isinstance(expected_sha256, str)
        or len(expected_sha256) != 64
        or any(ch not in "0123456789abcdef" for ch in expected_sha256)
    ):
        raise ApplicationStateValidationError(
            "expected_sha256 must be 64 lowercase hex characters"
        )

    object_id = _as_uuid(work_object_id, field_name="work_object_id")
    pinned_revision_id = _as_uuid(work_revision_id, field_name="work_revision_id")
    obj = repo.lock_work_object(conn, object_id)
    if obj is None:
        raise ApplicationStateNotFoundError(
            f"workspace document not found: {object_id}"
        )
    if obj.kind not in {"plan", "runbook"}:
        raise ApplicationStateValidationError(
            "playable_artifact_id must identify a World Plan or Runbook"
        )
    if obj.world_id != expected_world_id or obj.campaign_id is not None:
        raise ApplicationStateConflictError(
            "selected World does not own the Runbook"
        )
    if obj.status not in {"active", "discarded"}:
        raise ApplicationStateConflictError("runbook workspace document is unavailable")

    revision = _lock_work_revision_for_share(conn, object_id, revision_n)
    if revision is None:
        raise ApplicationStateNotFoundError(
            "historical revision bytes were never retained"
        )
    if (
        revision.work_revision_id != pinned_revision_id
        or revision.revision_n != revision_n
        or revision.work_object_id != obj.work_object_id
        or revision.world_id != expected_world_id
    ):
        raise ApplicationStateConflictError(
            "playable revision owner or identity does not match the pinned World Run"
        )
    if revision.content_sha256 != expected_sha256:
        raise ApplicationStateConflictError("playable content SHA mismatch")
    if sha256_utf8(revision.markdown) != revision.content_sha256:
        raise ApplicationStateConflictError(
            "playable revision content SHA does not match its Markdown"
        )
    return revision


def _lock_work_revision_for_share(
    conn: psycopg.Connection, work_object_id: UUID, revision_n: int
) -> WorkRevision | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT work_revision_id, work_object_id, world_id, revision_n,
                   markdown, content_sha256, created_at
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


def require_world_runbook_rebase_source(
    conn: psycopg.Connection,
    work_object_id: UUID | str,
    *,
    expected_world_id: str,
) -> None:
    """Keep World Run rebasing Runbook-only, even for same-target retries."""
    object_id = _as_uuid(work_object_id, field_name="work_object_id")
    obj = repo.lock_work_object(conn, object_id)
    if obj is None:
        raise ApplicationStateNotFoundError(
            f"workspace document not found: {object_id}"
        )
    if obj.kind != "runbook":
        raise ApplicationStateValidationError(
            "Plan-backed World PlayRun rebasing is not supported"
        )
    if obj.world_id != expected_world_id or obj.campaign_id is not None:
        raise ApplicationStateConflictError(
            "selected World does not own the Runbook"
        )
