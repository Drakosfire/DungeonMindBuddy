"""PostgreSQL persistence for Plan action reservations and safe projections."""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from application_state.agent_conversation.types import ProviderOutcomeEventV1
from application_state.agent_conversation.types import WorldPointer

from application_state.errors import ApplicationStateConflictError, ApplicationStateValidationError
from application_state.plan_action_dialogue.types import (
    PlanActionBasis,
    PrivatePlanActionConsultation,
    decode_consultation,
    PlanActionPlayableTargetReceipt,
    PlanActionSelectionAnchorV1,
    PlanActionRecord,
    PlanActionReservation,
)


_RETURNING = """
    action_id, idempotency_key, request_fingerprint, action_type, world_id,
    document_id, object_revision, work_revision_id, revision_n,
    content_sha256, draft_matches_basis, draft_sha256, target_kind,
    selected_text_sha256, playable_target_receipt, selection_anchor,
    instruction, status, assistant_summary,
    failure_code, dispatch_token, fence, action_sequence, accepted_at,
    completed_at, lease_expires_at, consultation, authoring_origin
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
        authoring_origin=row["authoring_origin"],
        action_id=row["action_id"],
        idempotency_key=row["idempotency_key"],
        request_fingerprint=row["request_fingerprint"],
        action_type=row["action_type"],
        basis=basis,
        draft_matches_basis=row["draft_matches_basis"],
        draft_sha256=row["draft_sha256"],
        target_kind=row["target_kind"],
        selected_text_sha256=row["selected_text_sha256"],
        playable_target_receipt=(
            PlanActionPlayableTargetReceipt.model_validate(row["playable_target_receipt"])
            if row["playable_target_receipt"] is not None else None
        ),
        selection_anchor=(
            PlanActionSelectionAnchorV1.model_validate(row["selection_anchor"])
            if row["selection_anchor"] is not None else None
        ),
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
        consultation=(decode_consultation(row["consultation"])
                      if row.get("consultation") is not None else None),
    )


def _get_by_key(
    conn: psycopg.Connection, world_id: str, key: UUID, *, lock: bool
) -> PlanActionRecord | None:
    suffix = " FOR UPDATE" if lock else ""
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"SELECT {_RETURNING} FROM plan_action.action "
            f"WHERE world_id = %s AND idempotency_key = %s{suffix}",
            (world_id, key),
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
                updated_at = clock_timestamp()
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
                target_kind, selected_text_sha256, playable_target_receipt,
                selection_anchor, instruction, status,
                dispatch_token, fence, accepted_at, lease_expires_at, updated_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                'pending', %s, 1, clock_timestamp(),
                clock_timestamp() + interval '120 seconds', clock_timestamp()
            )
            ON CONFLICT (world_id, idempotency_key) DO NOTHING
            RETURNING {_RETURNING}
            """,
            (
                action_id, request.idempotency_key, request.request_fingerprint,
                request.action_type, basis.world_id, basis.document_id,
                basis.object_revision, basis.work_revision_id, basis.revision_n,
                basis.content_sha256, request.draft_matches_basis,
                request.draft_sha256, request.target_kind,
                request.selected_text_sha256,
                Jsonb(request.playable_target_receipt.model_dump(mode="json"))
                if request.playable_target_receipt is not None else None,
                Jsonb(request.selection_anchor.model_dump(mode="json", by_alias=True))
                if request.selection_anchor is not None else None,
                request.instruction, token,
            ),
        )
        row = cur.fetchone()
    if row is not None:
        if request.expected_world_pointer is not None:
            expect_world_pointer(conn, request.expected_world_pointer)
        return _record(row), True

    existing = _get_by_key(conn, basis.world_id, request.idempotency_key, lock=True)
    if existing is None:
        raise RuntimeError("Plan action idempotency conflict did not resolve to a row")
    if (
        existing.request_fingerprint != request.request_fingerprint
        or existing.playable_target_receipt != request.playable_target_receipt
        or existing.selection_anchor != request.selection_anchor
        or existing.action_type != request.action_type
        or existing.basis != request.basis
        or existing.draft_matches_basis != request.draft_matches_basis
        or existing.draft_sha256 != request.draft_sha256
        or existing.target_kind != request.target_kind
        or existing.selected_text_sha256 != request.selected_text_sha256
        or existing.instruction != request.instruction
    ):
        raise ApplicationStateConflictError("Plan action key was reused with a different request")
    if request.expected_world_pointer is not None:
        if (existing.consultation is not None
                and (existing.consultation.receipt.origin_conversation_id
                     != request.expected_world_pointer.active_conversation_id
                     or existing.consultation.receipt.origin_pointer_revision
                     != request.expected_world_pointer.revision)):
            raise ApplicationStateConflictError("Plan action key was reused in another World conversation")
        expect_world_pointer(conn, request.expected_world_pointer)
    if existing.status == "pending":
        existing = _reconcile_expiry(conn, existing.action_id)
    return existing, False


def expect_world_pointer(conn: psycopg.Connection, expected: WorldPointer) -> None:
    """Lock the World pointer so New conversation cannot overtake this transaction."""
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT active_conversation_id, pointer_revision FROM agent.world_state "
            "WHERE world_id = %s FOR UPDATE", (expected.world_id,),
        )
        current = cur.fetchone()
    if (current is None
            or current["active_conversation_id"] != expected.active_conversation_id
            or current["pointer_revision"] != expected.revision):
        raise ApplicationStateConflictError("World active conversation changed before Plan action authorization")


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
    current = _get_by_id(conn, action_id, lock=True)
    if current is not None and current.authoring_origin is not None:
        raise ApplicationStateValidationError("Agent-owned Plan authoring requires atomic turn finalization")
    if (current is not None and current.status == "pending" and current.consultation is not None
            and current.consultation.execution is not None
            and any(isinstance(event, ProviderOutcomeEventV1) and event.outcome == "outcome_unknown"
                    for event in current.consultation.execution.events)):
        raise ApplicationStateValidationError("unknown consultation outcome must remain indeterminate")
    if (current is not None and current.status == "pending"
            and current.consultation is not None and status == "completed"):
        raise ApplicationStateValidationError("consulted action requires a typed terminal result")
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""
            UPDATE plan_action.action
            SET status = %s, assistant_summary = %s, failure_code = %s,
                dispatch_token = NULL, lease_expires_at = NULL,
                completed_at = CASE WHEN %s THEN clock_timestamp() ELSE NULL END,
                updated_at = clock_timestamp()
            WHERE action_id = %s AND status = 'pending'
              AND dispatch_token = %s AND fence = %s
              AND lease_expires_at > clock_timestamp()
            RETURNING {_RETURNING}
            """,
            (status, summary, failure_code, status == "completed", action_id, token, fence),
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


def lock_dispatch(
    conn: psycopg.Connection, action_id: UUID, token: UUID, fence: int,
) -> PlanActionRecord:
    record = _get_by_id(conn, action_id, lock=True)
    if record is None:
        raise ApplicationStateConflictError("Plan action does not exist")
    if record.status == "pending":
        record = _reconcile_expiry(conn, action_id)
    if (record.status != "pending" or record.dispatch_token != token or record.fence != fence):
        raise ApplicationStateConflictError("Plan action consultation is fenced by a stale dispatch")
    return record


def validate_predecessor(
    conn: psycopg.Connection, current: PlanActionRecord, consultation: PrivatePlanActionConsultation,
) -> None:
    from application_state.plan_action_dialogue.graph_consultation import consultation_result_digest

    receipt = consultation.receipt
    link = receipt.continuation
    if link is None:
        return
    if link.continuation_of_action_id == receipt.action_id:
        raise ApplicationStateConflictError("action cannot continue itself")
    predecessor = _get_by_id(conn, link.continuation_of_action_id, lock=True)
    previous = None if predecessor is None else predecessor.consultation
    if (predecessor is None or predecessor.status != "completed" or previous is None
            or previous.result is None or previous.result.kind != "clarification"
            or previous.result.result_id != link.clarification_id
            or consultation_result_digest(previous.result) != link.previous_result_sha256
            or predecessor.instruction != link.previous_instruction
            or predecessor.basis != receipt.basis
            or predecessor.draft_matches_basis != receipt.draft_matches_basis
            or predecessor.draft_sha256 != receipt.draft_sha256
            or predecessor.target_kind != receipt.target_kind
            or predecessor.selected_text_sha256 != receipt.selected_text_sha256
            or predecessor.selection_anchor != current.selection_anchor
            or previous.receipt.origin_conversation_id != receipt.origin_conversation_id
            or previous.receipt.origin_pointer_revision != receipt.origin_pointer_revision
            or previous.receipt.surface_id != receipt.surface_id
            or previous.receipt.surface_instance_id != receipt.surface_instance_id):
        raise ApplicationStateConflictError("clarification predecessor differs from the current action basis")
    with conn.cursor() as cur:
        cur.execute(
            "SELECT action_id FROM plan_action.action WHERE action_id <> %s AND "
            "consultation->'receipt'->'continuation'->>'continuation_of_action_id' = %s LIMIT 1",
            (receipt.action_id, str(link.continuation_of_action_id)),
        )
        if cur.fetchone() is not None:
            raise ApplicationStateConflictError("clarification predecessor is already superseded")


def write_consultation(
    conn: psycopg.Connection, record: PlanActionRecord, consultation: PrivatePlanActionConsultation,
    *, status: str = "pending", summary: str | None = None, failure_code: str | None = None,
) -> PlanActionRecord:
    # Validate the full row before writing; readback validates it again.
    PlanActionRecord.model_validate(record.model_dump(mode="python") | {
        "consultation": consultation, "status": status,
        "assistant_summary": summary, "failure_code": failure_code,
    })
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""UPDATE plan_action.action
            SET consultation = %s, status = %s, assistant_summary = %s, failure_code = %s,
                dispatch_token = CASE WHEN %s THEN dispatch_token ELSE NULL END,
                lease_expires_at = CASE WHEN %s THEN lease_expires_at ELSE NULL END,
                completed_at = CASE WHEN %s THEN clock_timestamp() ELSE NULL END,
                updated_at = clock_timestamp()
            WHERE action_id = %s AND status = 'pending' AND dispatch_token = %s
                AND fence = %s AND lease_expires_at > clock_timestamp()
            RETURNING {_RETURNING}""",
            (Jsonb(consultation.model_dump(mode="json", by_alias=True)), status, summary,
             failure_code, status == "pending", status == "pending", status == "completed",
             record.action_id, record.dispatch_token, record.fence),
        )
        row = cur.fetchone()
    if row is None:
        raise ApplicationStateConflictError("Plan action consultation lost its dispatch fence")
    return _record(row)


def get_by_key(conn: psycopg.Connection, world_id: str, key: UUID) -> PlanActionRecord | None:
    current = _get_by_key(conn, world_id, key, lock=True)
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


def list_conversation(
    conn: psycopg.Connection, world_id: str, conversation_id: UUID, *,
    limit: int, before_action_sequence: int | None,
) -> tuple[list[PlanActionRecord], int | None]:
    if not 1 <= limit <= 50:
        raise ValueError("Plan action conversation page limit must be between 1 and 50")
    if before_action_sequence is not None and before_action_sequence < 1:
        raise ValueError("Plan action conversation cursor must be positive")
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"SELECT {_RETURNING} FROM plan_action.action "
            "WHERE world_id = %s "
            "AND consultation->'receipt'->>'origin_conversation_id' = %s "
            "AND (%s::bigint IS NULL OR action_sequence < %s) "
            "ORDER BY action_sequence DESC LIMIT %s",
            (world_id, str(conversation_id), before_action_sequence,
             before_action_sequence, limit + 1),
        )
        rows = cur.fetchall()
    more = len(rows) > limit
    records = [_record(row) for row in rows[:limit]]
    next_cursor = records[-1].action_sequence if more else None
    return list(reversed(records)), next_cursor


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


def freeze_authoring_reservation(conn, record, origin):
    """Same-UOW marker before the new row can become visible to generic owners."""
    from application_state.agent_conversation.plan_authoring import PlanJevAuthoringReservationV1
    if not isinstance(origin, PlanJevAuthoringReservationV1):
        raise ApplicationStateValidationError('Typed Agent authoring reservation required')
    if record.authoring_origin is not None:
        if record.authoring_origin != origin:
            raise ApplicationStateConflictError('Plan action already has a different authoring origin')
        return record
    PlanActionRecord.model_validate(record.model_dump(mode='python') | {'authoring_origin': origin})
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(f"""UPDATE plan_action.action SET authoring_origin=%s,updated_at=clock_timestamp()
            WHERE action_id=%s AND status='pending' AND authoring_origin IS NULL AND consultation IS NULL
              AND dispatch_token=%s AND fence=%s AND lease_expires_at>clock_timestamp()
            RETURNING {_RETURNING}""",
            (Jsonb(origin.model_dump(mode='json',by_alias=True)),record.action_id,record.dispatch_token,record.fence))
        row=cur.fetchone()
    if row is None:
        raise ApplicationStateConflictError('Plan authoring reservation lost its dispatch fence')
    return _record(row)
