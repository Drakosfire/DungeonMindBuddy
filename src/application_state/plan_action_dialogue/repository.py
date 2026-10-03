"""PostgreSQL persistence for Plan action reservations and safe projections."""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

import psycopg
from psycopg.rows import dict_row

from application_state.errors import ApplicationStateConflictError
from application_state.plan_action_dialogue.types import (
    PlanActionBasis,
    PlanActionRecord,
    PlanActionReservation,
)


_RETURNING = """
    action_id, idempotency_key, request_fingerprint, action_type, world_id,
    document_id, object_revision, work_revision_id, revision_n,
    content_sha256, draft_matches_basis, draft_sha256, target_kind,
    selected_text_sha256, instruction, status, assistant_summary,
    failure_code, dispatch_token, fence, action_sequence, accepted_at,
    completed_at, lease_expires_at
"""


def _record(row: dict[str, Any]) -> PlanActionRecord:
    basis = PlanActionBasis(
        world_id=row["world_id"],
        document_id=row["document_id"],
        object_revision=row["object_revision"],
        work_revision_id=row["work_revision_id"],
        revision_n=row["revision_n"],
        content_sha256=row["content_sha256"],
    )
    return PlanActionRecord(
        action_id=row["action_id"],
        idempotency_key=row["idempotency_key"],
        request_fingerprint=row["request_fingerprint"],
        action_type=row["action_type"],
        basis=basis,
        draft_matches_basis=row["draft_matches_basis"],
        draft_sha256=row["draft_sha256"],
        target_kind=row["target_kind"],
        selected_text_sha256=row["selected_text_sha256"],
        instruction=row["instruction"],
        status=row["status"],
        assistant_summary=row["assistant_summary"],
        failure_code=row["failure_code"],
        dispatch_token=row["dispatch_token"],
        fence=row["fence"],
        action_sequence=row["action_sequence"],
        accepted_at=row["accepted_at"],
        completed_at=row["completed_at"],
        lease_expires_at=row["lease_expires_at"],
    )


def _get_by_key(conn: psycopg.Connection, key: UUID, *, lock: bool) -> PlanActionRecord | None:
    suffix = " FOR UPDATE" if lock else ""
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"SELECT {_RETURNING} FROM plan_action.action WHERE idempotency_key = %s{suffix}",
            (key,),
        )
        row = cur.fetchone()
    return None if row is None else _record(row)


def _get_by_id(conn: psycopg.Connection, action_id: UUID, *, lock: bool = False) -> PlanActionRecord | None:
    suffix = " FOR UPDATE" if lock else ""
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"SELECT {_RETURNING} FROM plan_action.action WHERE action_id = %s{suffix}",
            (action_id,),
        )
        row = cur.fetchone()
    return None if row is None else _record(row)


def _reconcile_expiry(conn: psycopg.Connection, action_id: UUID) -> PlanActionRecord:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""
            UPDATE plan_action.action
            SET status = 'indeterminate', failure_code = 'lease_expired',
                assistant_summary = NULL, dispatch_token = NULL,
                fence = fence + 1, lease_expires_at = NULL,
                completed_at = clock_timestamp(), updated_at = clock_timestamp()
            WHERE action_id = %s AND status = 'pending'
              AND lease_expires_at <= clock_timestamp()
            RETURNING {_RETURNING}
            """,
            (action_id,),
        )
        row = cur.fetchone()
    if row is not None:
        return _record(row)
    current = _get_by_id(conn, action_id, lock=True)
    if current is None:
        raise RuntimeError("Plan action disappeared during expiry reconciliation")
    return current


def reserve(conn: psycopg.Connection, request: PlanActionReservation) -> tuple[PlanActionRecord, bool]:
    action_id = uuid4()
    token = uuid4()
    basis = request.basis
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""
            INSERT INTO plan_action.action (
                action_id, idempotency_key, request_fingerprint, action_type,
                world_id, document_id, object_revision, work_revision_id,
                revision_n, content_sha256, draft_matches_basis, draft_sha256,
                target_kind, selected_text_sha256, instruction, status,
                dispatch_token, fence, accepted_at, lease_expires_at, updated_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                'pending', %s, 1, clock_timestamp(),
                clock_timestamp() + interval '120 seconds', clock_timestamp()
            )
            ON CONFLICT (idempotency_key) DO NOTHING
            RETURNING {_RETURNING}
            """,
            (
                action_id, request.idempotency_key, request.request_fingerprint,
                request.action_type, basis.world_id, basis.document_id,
                basis.object_revision, basis.work_revision_id, basis.revision_n,
                basis.content_sha256, request.draft_matches_basis,
                request.draft_sha256, request.target_kind,
                request.selected_text_sha256, request.instruction, token,
            ),
        )
        row = cur.fetchone()
    if row is not None:
        return _record(row), True

    existing = _get_by_key(conn, request.idempotency_key, lock=True)
    if existing is None:
        raise RuntimeError("Plan action idempotency conflict did not resolve to a row")
    if existing.request_fingerprint != request.request_fingerprint:
        raise ApplicationStateConflictError("Plan action key was reused with a different request")
    if existing.status == "pending":
        existing = _reconcile_expiry(conn, existing.action_id)
    return existing, False


def finish(
    conn: psycopg.Connection,
    *,
    action_id: UUID,
    token: UUID,
    fence: int,
    status: str,
    summary: str | None = None,
    failure_code: str | None = None,
) -> PlanActionRecord:
    if status not in {"completed", "failed"}:
        raise ValueError("terminal Plan action status must be completed or failed")
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""
            UPDATE plan_action.action
            SET status = %s, assistant_summary = %s, failure_code = %s,
                dispatch_token = NULL, lease_expires_at = NULL,
                completed_at = clock_timestamp(), updated_at = clock_timestamp()
            WHERE action_id = %s AND status = 'pending'
              AND dispatch_token = %s AND fence = %s
              AND lease_expires_at > clock_timestamp()
            RETURNING {_RETURNING}
            """,
            (status, summary, failure_code, action_id, token, fence),
        )
        row = cur.fetchone()
    if row is not None:
        return _record(row)
    current = _get_by_id(conn, action_id, lock=True)
    if current is None:
        raise RuntimeError("Plan action disappeared during terminal compare-and-set")
    if current.status == "pending":
        current = _reconcile_expiry(conn, action_id)
    return current


def get_by_key(conn: psycopg.Connection, key: UUID) -> PlanActionRecord | None:
    current = _get_by_key(conn, key, lock=True)
    if current is not None and current.status == "pending":
        current = _reconcile_expiry(conn, current.action_id)
    return current


def list_basis(conn: psycopg.Connection, basis: PlanActionBasis) -> list[PlanActionRecord]:
    predicate = """
        world_id = %s AND document_id = %s AND object_revision = %s
        AND work_revision_id = %s AND revision_n = %s AND content_sha256 = %s
    """
    values = (
        basis.world_id, basis.document_id, basis.object_revision,
        basis.work_revision_id, basis.revision_n, basis.content_sha256,
    )
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"SELECT {_RETURNING} FROM plan_action.action WHERE {predicate} "
            "ORDER BY accepted_at DESC, action_sequence DESC LIMIT 50 FOR UPDATE",
            values,
        )
        rows = cur.fetchall()
    records = [_record(row) for row in rows]
    reconciled = [
        _reconcile_expiry(conn, record.action_id) if record.status == "pending" else record
        for record in records
    ]
    return list(reversed(reconciled))


def completed_context(conn: psycopg.Connection, basis: PlanActionBasis, *, limit: int) -> list[PlanActionRecord]:
    if not 1 <= limit <= 6:
        raise ValueError("completed Plan action context limit must be between 1 and 6")
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""
            SELECT {_RETURNING} FROM plan_action.action
            WHERE world_id = %s AND document_id = %s AND object_revision = %s
              AND work_revision_id = %s AND revision_n = %s AND content_sha256 = %s
              AND status = 'completed' AND assistant_summary IS NOT NULL
            ORDER BY accepted_at DESC, action_sequence DESC LIMIT %s
            """,
            (
                basis.world_id, basis.document_id, basis.object_revision,
                basis.work_revision_id, basis.revision_n, basis.content_sha256,
                limit,
            ),
        )
        rows = cur.fetchall()
    return list(reversed([_record(row) for row in rows]))
