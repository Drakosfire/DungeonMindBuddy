"""SQL repository for the typed Agent Conversation domain."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from pydantic import ValidationError

from application_state.agent_conversation.types import (
    CompletedPlanAskPair,
    Conversation,
    ConversationCommandReceipt,
    CommandResolutionRecordV1,
    Draft,
    HistoricalReference,
    LegacyImportReceipt,
    PlanAskContextBasis,
    PlanAskHistoryAttributionV1,
    CompletionBindingEventV1,
    PlanWorldGraphCompletion,
    PlanWorldGraphExecution,
    Turn,
    TurnProvenance,
    WorldPointer,
    decode_plan_playable_target_reference,
    turn_idempotency_fingerprint,
    validate_completion_against_receipt,
    validate_execution_completion,
)
from application_state.agent_conversation.types import (
    request_fingerprint as model_fingerprint,
)
from application_state.errors import ApplicationStateIntegrityError

_CONVERSATION_COLS = """
    conversation_id, world_id, status, revision, next_turn_sequence,
    created_at, updated_at, archived_at
"""
_WORLD_COLS = "world_id, active_conversation_id, pointer_revision AS revision"
_TURN_COLS = """
    turn_id, conversation_id, world_id, idempotency_key, sequence, revision,
    status, user_text, assistant_text, failure_code, surface_resolution,
    surface_id, surface_instance_id, submitted_intent_fingerprint_v1, attempt,
    submitted_intent_fingerprint_v2, graph_context_receipt, completion,
    graph_context_execution,
    claim_expires_at, accepted_at, completed_at, updated_at
"""
_TURN_COLS_T = ", ".join(f"t.{column.strip()}" for column in _TURN_COLS.split(","))
_DRAFT_COLS = """
    world_id, conversation_id, draft_id, revision, body, request_fingerprint,
    surface_resolution, surface_id, surface_instance_id,
    primary_resolution, primary_kind,
    primary_object_id, primary_revision, primary_content_sha256,
    primary_object_revision, primary_work_revision_id, primary_revision_n,
    selected_resolution, selected_kind, selected_object_id, selected_revision,
    selected_content_sha256, selected_object_revision, selected_work_revision_id,
    selected_revision_n, source_fingerprint, retired_at, created_at, updated_at
"""


def _reference_from_row(row: dict[str, Any]) -> HistoricalReference:
    return HistoricalReference(
        resolution=row["resolution"],
        kind=row["kind"],
        object_id=row["object_id"],
        revision=row["revision"],
        content_sha256=row["content_sha256"],
        object_revision=row["object_revision"],
        work_revision_id=row["work_revision_id"],
        revision_n=row["revision_n"],
    )


def _reference_values(reference: HistoricalReference) -> tuple[Any, ...]:
    return (
        reference.resolution,
        reference.kind,
        reference.object_id,
        reference.revision,
        reference.content_sha256,
        reference.object_revision,
        reference.work_revision_id,
        reference.revision_n,
    )


def _turn_references(
    conn: psycopg.Connection, turn_id: UUID
) -> tuple[HistoricalReference, list[HistoricalReference], HistoricalReference]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT reference_role, ordinal, resolution, kind, object_id, revision,
                   content_sha256, object_revision, work_revision_id, revision_n
            FROM agent.turn_reference
            WHERE turn_id = %s
            ORDER BY CASE reference_role WHEN 'primary' THEN 0 WHEN 'supporting' THEN 1 ELSE 2 END,
                     ordinal
            """,
            (turn_id,),
        )
        rows = cur.fetchall()
    primary = next((r for r in rows if r["reference_role"] == "primary"), None)
    selected = next((r for r in rows if r["reference_role"] == "selected"), None)
    if primary is None or selected is None:
        raise ApplicationStateIntegrityError(
            "turn is missing typed primary/selected provenance"
        )
    return (
        _reference_from_row(primary),
        [_reference_from_row(r) for r in rows if r["reference_role"] == "supporting"],
        _reference_from_row(selected),
    )


def _turn_from_row(conn: psycopg.Connection, row: dict[str, Any]) -> Turn:
    primary, supporting, selected = _turn_references(conn, row["turn_id"])
    provenance = TurnProvenance(
        world_id=row["world_id"],
        surface_resolution=row["surface_resolution"],
        surface_id=row["surface_id"],
        surface_instance_id=row["surface_instance_id"],
        primary_work=primary,
        supporting_work=supporting,
        selected_object=selected,
    )
    return Turn(
        **{
            key: row[key]
            for key in row
            if key not in {"surface_resolution", "surface_id", "surface_instance_id"}
        },
        provenance=provenance,
    )


def _draft_references(
    conn: psycopg.Connection, draft_id: UUID
) -> list[HistoricalReference]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT resolution, kind, object_id, revision, content_sha256,
                   object_revision, work_revision_id, revision_n
            FROM agent.draft_reference
            WHERE draft_id = %s
            ORDER BY ordinal
            """,
            (draft_id,),
        )
        rows = cur.fetchall()
    return [_reference_from_row(row) for row in rows]


def _draft_from_row(conn: psycopg.Connection, row: dict[str, Any]) -> Draft:
    provenance = TurnProvenance(
        world_id=row["world_id"],
        surface_resolution=row["surface_resolution"],
        surface_id=row["surface_id"],
        surface_instance_id=row["surface_instance_id"],
        primary_work=HistoricalReference(
            resolution=row["primary_resolution"],
            kind=row["primary_kind"],
            object_id=row["primary_object_id"],
            revision=row["primary_revision"],
            content_sha256=row["primary_content_sha256"],
            object_revision=row["primary_object_revision"],
            work_revision_id=row["primary_work_revision_id"],
            revision_n=row["primary_revision_n"],
        ),
        supporting_work=_draft_references(conn, row["draft_id"]),
        selected_object=HistoricalReference(
            resolution=row["selected_resolution"],
            kind=row["selected_kind"],
            object_id=row["selected_object_id"],
            revision=row["selected_revision"],
            content_sha256=row["selected_content_sha256"],
            object_revision=row["selected_object_revision"],
            work_revision_id=row["selected_work_revision_id"],
            revision_n=row["selected_revision_n"],
        ),
    )
    return Draft(
        world_id=row["world_id"],
        conversation_id=row["conversation_id"],
        draft_id=row["draft_id"],
        revision=row["revision"],
        body=row["body"],
        provenance=provenance,
        retired_at=row["retired_at"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def ensure_world_state(conn: psycopg.Connection, world_id: str, now: datetime) -> None:
    conn.execute(
        """
        INSERT INTO agent.world_state (world_id, active_conversation_id, pointer_revision, updated_at)
        VALUES (%s, NULL, 0, %s)
        ON CONFLICT (world_id) DO NOTHING
        """,
        (world_id, now),
    )


def lock_world_state(conn: psycopg.Connection, world_id: str) -> WorldPointer:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"SELECT {_WORLD_COLS} FROM agent.world_state WHERE world_id = %s FOR UPDATE",
            (world_id,),
        )
        row = cur.fetchone()
    if row is None:
        raise ApplicationStateIntegrityError("World state lock row was not created")
    return WorldPointer.model_validate(row)


def get_world_state(conn: psycopg.Connection, world_id: str) -> WorldPointer | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"SELECT {_WORLD_COLS} FROM agent.world_state WHERE world_id = %s",
            (world_id,),
        )
        row = cur.fetchone()
    return None if row is None else WorldPointer.model_validate(row)


def update_world_state(
    conn: psycopg.Connection,
    *,
    world_id: str,
    active_conversation_id: UUID | None,
    pointer_revision: int,
    now: datetime,
) -> WorldPointer:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""
            UPDATE agent.world_state
            SET active_conversation_id = %s, pointer_revision = %s, updated_at = %s
            WHERE world_id = %s
            RETURNING {_WORLD_COLS}
            """,
            (active_conversation_id, pointer_revision, now, world_id),
        )
        row = cur.fetchone()
    if row is None:
        raise ApplicationStateIntegrityError("World state update did not persist")
    return WorldPointer.model_validate(row)


def get_command_receipt(
    conn: psycopg.Connection, world_id: str, command_id: UUID
) -> tuple[ConversationCommandReceipt, str] | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT world_id, command_id, command_kind, conversation_id,
                   result_active_conversation_id AS active_conversation_id,
                   result_pointer_revision AS pointer_revision, recorded_at,
                   request_fingerprint
            FROM agent.command_receipt
            WHERE world_id = %s AND command_id = %s
            """,
            (world_id, command_id),
        )
        row = cur.fetchone()
    if row is None:
        return None
    fingerprint = row.pop("request_fingerprint")
    return ConversationCommandReceipt.model_validate(row), fingerprint


def insert_command_receipt(
    conn: psycopg.Connection,
    *,
    world_id: str,
    command_id: UUID,
    command_kind: str,
    request_fingerprint: str,
    expected_pointer_revision: int,
    expected_active_conversation_id: UUID | None,
    conversation_id: UUID,
    result_active_conversation_id: UUID | None,
    result_pointer_revision: int,
    recorded_at: datetime,
) -> ConversationCommandReceipt:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            INSERT INTO agent.command_receipt (
                world_id, command_id, command_kind, request_fingerprint,
                expected_pointer_revision, expected_active_conversation_id,
                conversation_id, result_active_conversation_id,
                result_pointer_revision, recorded_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING world_id, command_id, command_kind, conversation_id,
                      result_active_conversation_id AS active_conversation_id,
                      result_pointer_revision AS pointer_revision, recorded_at
            """,
            (
                world_id,
                command_id,
                command_kind,
                request_fingerprint,
                expected_pointer_revision,
                expected_active_conversation_id,
                conversation_id,
                result_active_conversation_id,
                result_pointer_revision,
                recorded_at,
            ),
        )
        row = cur.fetchone()
    if row is None:
        raise ApplicationStateIntegrityError(
            "conversation command receipt did not persist"
        )
    return ConversationCommandReceipt.model_validate(row)


def insert_conversation(
    conn: psycopg.Connection,
    *,
    conversation_id: UUID,
    world_id: str,
    status: str,
    revision: int,
    next_turn_sequence: int,
    now: datetime,
    archived_at: datetime | None,
) -> Conversation:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""
            INSERT INTO agent.conversation (
                conversation_id, world_id, status, revision, next_turn_sequence,
                created_at, updated_at, archived_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING {_CONVERSATION_COLS}
            """,
            (
                conversation_id,
                world_id,
                status,
                revision,
                next_turn_sequence,
                now,
                now,
                archived_at,
            ),
        )
        row = cur.fetchone()
    if row is None:
        raise ApplicationStateIntegrityError("conversation insert did not persist")
    return Conversation.model_validate(row)


def lock_conversation(
    conn: psycopg.Connection, world_id: str, conversation_id: UUID
) -> Conversation | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""
            SELECT {_CONVERSATION_COLS} FROM agent.conversation
            WHERE world_id = %s AND conversation_id = %s FOR UPDATE
            """,
            (world_id, conversation_id),
        )
        row = cur.fetchone()
    return None if row is None else Conversation.model_validate(row)


def get_conversation(
    conn: psycopg.Connection, world_id: str, conversation_id: UUID
) -> Conversation | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"SELECT {_CONVERSATION_COLS} FROM agent.conversation WHERE world_id = %s AND conversation_id = %s",
            (world_id, conversation_id),
        )
        row = cur.fetchone()
    return None if row is None else Conversation.model_validate(row)


def list_conversations(
    conn: psycopg.Connection, world_id: str, *, status: str | None, limit: int
) -> list[Conversation]:
    params: list[Any] = [world_id]
    status_clause = ""
    if status is not None:
        status_clause = "AND status = %s"
        params.append(status)
    params.append(limit)
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""
            SELECT {_CONVERSATION_COLS} FROM agent.conversation
            WHERE world_id = %s {status_clause}
            ORDER BY updated_at DESC, conversation_id
            LIMIT %s
            """,
            params,
        )
        rows = cur.fetchall()
    return [Conversation.model_validate(row) for row in rows]


def update_conversation_state(
    conn: psycopg.Connection,
    *,
    world_id: str,
    conversation_id: UUID,
    expected_revision: int,
    status: str,
    next_turn_sequence: int,
    now: datetime,
    archived_at: datetime | None,
) -> Conversation | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""
            UPDATE agent.conversation
            SET status = %s, revision = revision + 1, next_turn_sequence = %s,
                updated_at = %s, archived_at = %s
            WHERE world_id = %s AND conversation_id = %s AND revision = %s
            RETURNING {_CONVERSATION_COLS}
            """,
            (
                status,
                next_turn_sequence,
                now,
                archived_at,
                world_id,
                conversation_id,
                expected_revision,
            ),
        )
        row = cur.fetchone()
    return None if row is None else Conversation.model_validate(row)


def advance_conversation_for_turn(
    conn: psycopg.Connection,
    *,
    world_id: str,
    conversation_id: UUID,
    expected_revision: int,
    now: datetime,
) -> tuple[int, int] | None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE agent.conversation
            SET revision = revision + 1, next_turn_sequence = next_turn_sequence + 1,
                updated_at = %s
            WHERE world_id = %s AND conversation_id = %s
              AND status = 'active' AND revision = %s
            RETURNING revision, next_turn_sequence - 1
            """,
            (now, world_id, conversation_id, expected_revision),
        )
        row = cur.fetchone()
    return None if row is None else (int(row[0]), int(row[1]))


def get_active_conversation(
    conn: psycopg.Connection, world_id: str
) -> Conversation | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""
            SELECT c.{_CONVERSATION_COLS.replace(", ", ", c.")}
            FROM agent.world_state AS w
            JOIN agent.conversation AS c
              ON c.conversation_id = w.active_conversation_id AND c.world_id = w.world_id
            WHERE w.world_id = %s
            """,
            (world_id,),
        )
        row = cur.fetchone()
    return None if row is None else Conversation.model_validate(row)


def get_turn_by_world_key(
    conn: psycopg.Connection, world_id: str, idempotency_key: UUID
) -> tuple[Turn, str, str, str | None, str | None] | None:
    """Find the durable turn receipt in a World, regardless of its conversation."""

    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""
            SELECT {_TURN_COLS}, request_fingerprint, idempotency_fingerprint
            FROM agent.turn WHERE world_id = %s AND idempotency_key = %s
            """,
            (world_id, idempotency_key),
        )
        row = cur.fetchone()
    if row is None:
        return None
    request_hash = row.pop("request_fingerprint")
    idempotency_hash = row.pop("idempotency_fingerprint")
    return (
        _turn_from_row(conn, row),
        request_hash,
        idempotency_hash,
        row["submitted_intent_fingerprint_v1"],
        row["submitted_intent_fingerprint_v2"],
    )


def get_turn(conn: psycopg.Connection, world_id: str, turn_id: UUID) -> Turn | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"SELECT {_TURN_COLS} FROM agent.turn WHERE world_id = %s AND turn_id = %s",
            (world_id, turn_id),
        )
        row = cur.fetchone()
    return None if row is None else _turn_from_row(conn, row)


def lock_turn(conn: psycopg.Connection, world_id: str, turn_id: UUID) -> Turn | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"SELECT {_TURN_COLS} FROM agent.turn WHERE world_id = %s AND turn_id = %s FOR UPDATE",
            (world_id, turn_id),
        )
        row = cur.fetchone()
    return None if row is None else _turn_from_row(conn, row)


def list_turns(
    conn: psycopg.Connection,
    world_id: str,
    conversation_id: UUID,
    *,
    limit: int,
    before_sequence: int | None,
) -> list[Turn]:
    clauses = ["world_id = %s", "conversation_id = %s"]
    params: list[Any] = [world_id, conversation_id]
    if before_sequence is not None:
        clauses.append("sequence < %s")
        params.append(before_sequence)
    params.append(limit)
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""
            SELECT {_TURN_COLS} FROM agent.turn
            WHERE {" AND ".join(clauses)} ORDER BY sequence DESC LIMIT %s
            """,
            params,
        )
        rows = cur.fetchall()
    return [_turn_from_row(conn, row) for row in reversed(rows)]


def list_completed_plan_ask_context(
    conn: psycopg.Connection,
    verified_world_id: str,
    basis: PlanAskContextBasis,
    *,
    limit: int,
) -> list[CompletedPlanAskPair]:
    """Read eligible visible Ask pairs from the active World conversation.

    Pointer selection, completed-turn filtering, surface/basis eligibility, and
    the source limit deliberately share one statement snapshot.
    """

    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""
            SELECT {_TURN_COLS_T}
            FROM agent.world_state AS w
            JOIN agent.conversation AS c
              ON c.world_id = w.world_id
             AND c.conversation_id = w.active_conversation_id
             AND c.status = 'active'
            JOIN agent.turn AS t
              ON t.world_id = c.world_id
             AND t.conversation_id = c.conversation_id
            JOIN agent.turn_reference AS r
              ON r.turn_id = t.turn_id
             AND r.reference_role = 'primary'
            WHERE w.world_id = %s
              AND t.status = 'completed'
              AND t.user_text IS NOT NULL AND btrim(t.user_text) <> ''
              AND t.assistant_text IS NOT NULL AND btrim(t.assistant_text) <> ''
              AND t.surface_resolution = 'resolved' AND t.surface_id = 'plan'
              AND r.resolution = 'resolved' AND r.kind = 'plan'
              AND r.object_id = %s
              AND r.object_revision = %s
              AND r.work_revision_id = %s
              AND r.revision_n = %s
              AND r.content_sha256 = %s
            ORDER BY t.accepted_at DESC, t.sequence DESC, t.turn_id DESC
            LIMIT %s
            """,
            (
                verified_world_id,
                basis.document_id,
                basis.object_revision,
                basis.work_revision_id,
                basis.revision_n,
                basis.content_sha256,
                limit,
            ),
        )
        rows = cur.fetchall()
    pairs: list[CompletedPlanAskPair] = []
    for row in reversed(rows):
        try:
            turn = _turn_from_row(conn, row)
            history_attribution = _plan_ask_history_attribution(turn)
        except ApplicationStateIntegrityError:
            raise
        except (KeyError, TypeError, ValueError, ValidationError) as exc:
            raise ApplicationStateIntegrityError(
                "stored Plan Ask provenance or Graph completion is malformed"
            ) from exc
        pairs.append(
            CompletedPlanAskPair(
                source_sequence=turn.sequence,
                source_record_id=turn.turn_id,
                accepted_at=turn.accepted_at,
                question=turn.user_text,
                answer=turn.assistant_text or "",
                history_attribution=history_attribution,
            )
        )
    return pairs


def _plan_ask_history_attribution(
    turn: Turn,
) -> PlanAskHistoryAttributionV1 | None:
    """Project validated receipt/completion metadata without inferring legacy provenance."""
    receipt = turn.graph_context_receipt
    completion = turn.completion
    if receipt is None and completion is None:
        return None
    if receipt is None or completion is None:
        raise ApplicationStateIntegrityError(
            "completed Plan Ask has an incomplete Graph receipt/completion pair"
        )
    if (
        turn.status != "completed"
        or turn.provenance.surface_resolution != "resolved"
        or turn.provenance.surface_id != "plan"
        or not turn.provenance.surface_instance_id
    ):
        raise ApplicationStateIntegrityError(
            "Graph Ask provenance does not identify its completed Plan surface"
        )

    primary = turn.provenance.primary_work
    try:
        turn_basis = PlanAskContextBasis(
            world_id=turn.world_id,
            document_id=primary.object_id,
            object_revision=primary.object_revision,
            work_revision_id=primary.work_revision_id,
            revision_n=primary.revision_n,
            content_sha256=primary.content_sha256,
        )
    except (ValidationError, TypeError, ValueError) as exc:
        raise ApplicationStateIntegrityError(
            "Graph Ask primary Plan basis is incomplete"
        ) from exc
    if (
        primary.resolution != "resolved"
        or primary.kind != "plan"
        or receipt.plan_basis != turn_basis
    ):
        raise ApplicationStateIntegrityError(
            "Graph Ask receipt basis does not match its persisted Plan provenance"
        )

    stored_targets = [
        reference
        for reference in turn.provenance.supporting_work
        if reference.kind == "dmb_plan_playable_target_v1"
    ]
    try:
        stored_target = (
            decode_plan_playable_target_reference(stored_targets[0])
            if stored_targets
            else None
        )
        if turn.graph_context_execution is None:
            validate_completion_against_receipt(completion, receipt)
        else:
            bindings = [
                event for event in turn.graph_context_execution.events
                if isinstance(event, CompletionBindingEventV1)
            ]
            if len(bindings) != 1:
                raise ValueError("Graph Ask execution requires one completion binding")
            binding = bindings[0]
            validate_execution_completion(
                completion, receipt, turn.graph_context_execution,
                binding.provider_attempt_id, binding.claim_graph_event_ids,
            )
    except (ValidationError, TypeError, ValueError) as exc:
        raise ApplicationStateIntegrityError(
            "Graph Ask receipt or completion failed integrity validation"
        ) from exc
    if stored_target != receipt.playable_target:
        raise ApplicationStateIntegrityError(
            "Graph Ask receipt target does not match persisted Plan target provenance"
        )
    expected_answer = "\n".join(segment.text for segment in completion.answer_segments)
    if turn.assistant_text != expected_answer:
        raise ApplicationStateIntegrityError(
            "Graph Ask completion segments do not match the stored answer text"
        )

    return PlanAskHistoryAttributionV1(
        source_turn_id=turn.turn_id,
        source_conversation_id=turn.conversation_id,
        source_sequence=turn.sequence,
        source_turn_status="completed",
        surface_resolution="resolved",
        surface_id="plan",
        surface_instance_id=turn.provenance.surface_instance_id,
        plan_basis=receipt.plan_basis,
        playable_target=receipt.playable_target,
        context_receipt_sha256=receipt.context_receipt_sha256,
        answer_basis=completion.answer_basis,
        answer_context_status=completion.answer_context_status,
        answer_segments=completion.answer_segments,
        citation_map=completion.citation_map,
    )


def insert_turn(
    conn: psycopg.Connection,
    *,
    turn_id: UUID,
    request_fingerprint: str,
    idempotency_fingerprint: str,
    submitted_intent_fingerprint_v1: str | None = None,
    submitted_intent_fingerprint_v2: str | None = None,
    submission: Any,
    sequence: int,
    now: datetime,
    status: str = "accepted",
    assistant_text: str | None = None,
    failure_code: str | None = None,
    attempt: int = 0,
) -> Turn:
    provenance: TurnProvenance = submission.provenance
    graph_context_receipt = getattr(submission, "graph_context_receipt", None)
    graph_context_execution = getattr(submission, "graph_context_execution", None)
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""
            INSERT INTO agent.turn (
                turn_id, conversation_id, world_id, idempotency_key, idempotency_fingerprint, sequence,
                revision, status, request_fingerprint, user_text, assistant_text,
                failure_code, surface_resolution, surface_id, surface_instance_id,
                submitted_intent_fingerprint_v1, submitted_intent_fingerprint_v2,
                graph_context_receipt, completion, graph_context_execution,
                attempt, claim_expires_at,
                accepted_at, completed_at, updated_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s,
                1, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s,
                NULL, %s, %s, %s
            )
            RETURNING {_TURN_COLS}
            """,
            (
                turn_id,
                submission.conversation_id,
                submission.world_id,
                submission.idempotency_key,
                idempotency_fingerprint,
                sequence,
                status,
                request_fingerprint,
                submission.user_text,
                assistant_text,
                failure_code,
                provenance.surface_resolution,
                provenance.surface_id,
                provenance.surface_instance_id,
                submitted_intent_fingerprint_v1,
                submitted_intent_fingerprint_v2,
                (
                    None
                    if graph_context_receipt is None
                    else Jsonb(
                        graph_context_receipt.model_dump(mode="json", by_alias=True)
                    )
                ),
                None,
                (
                    None
                    if graph_context_execution is None
                    else Jsonb(graph_context_execution.model_dump(mode="json", by_alias=True))
                ),
                attempt,
                now,
                now if status in {"completed", "failed", "interrupted"} else None,
                now,
            ),
        )
        row = cur.fetchone()
    _insert_turn_reference(conn, turn_id, "primary", 0, provenance.primary_work)
    for ordinal, reference in enumerate(provenance.supporting_work):
        _insert_turn_reference(conn, turn_id, "supporting", ordinal, reference)
    _insert_turn_reference(conn, turn_id, "selected", 0, provenance.selected_object)
    if row is None:
        raise ApplicationStateIntegrityError("turn insert did not persist")
    return _turn_from_row(conn, row)


def _insert_turn_reference(
    conn: psycopg.Connection,
    turn_id: UUID,
    role: str,
    ordinal: int,
    reference: HistoricalReference,
) -> None:
    conn.execute(
        """
        INSERT INTO agent.turn_reference (
            turn_id, reference_role, ordinal, resolution, kind, object_id, revision,
            content_sha256, object_revision, work_revision_id, revision_n
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (turn_id, role, ordinal, *_reference_values(reference)),
    )


def database_clock(conn: psycopg.Connection) -> datetime:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT clock_timestamp() AS now")
        row = cur.fetchone()
    if row is None:
        raise ApplicationStateIntegrityError("database clock returned no value")
    return row["now"]


def claim_turn(
    conn: psycopg.Connection,
    *,
    world_id: str,
    turn_id: UUID,
    expected_revision: int,
    lease_seconds: int,
) -> Turn | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""
            UPDATE agent.turn
            SET status = 'running', revision = revision + 1,
                assistant_text = NULL, failure_code = NULL,
                attempt = attempt + 1,
                claim_expires_at = clock_timestamp() + make_interval(secs => %s),
                completed_at = NULL, updated_at = clock_timestamp()
            WHERE world_id = %s AND turn_id = %s AND revision = %s
              AND (
                    status IN ('accepted', 'failed', 'interrupted')
                    OR (
                        status = 'running'
                        AND (claim_expires_at IS NULL OR claim_expires_at <= clock_timestamp())
                    )
              )
            RETURNING {_TURN_COLS}
            """,
            (lease_seconds, world_id, turn_id, expected_revision),
        )
        row = cur.fetchone()
    return None if row is None else _turn_from_row(conn, row)


def renew_turn_claim(
    conn: psycopg.Connection,
    *,
    world_id: str,
    turn_id: UUID,
    expected_revision: int,
    lease_seconds: int,
) -> Turn | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""
            UPDATE agent.turn
            SET revision = revision + 1,
                claim_expires_at = clock_timestamp() + make_interval(secs => %s),
                updated_at = clock_timestamp()
            WHERE world_id = %s AND turn_id = %s AND status = 'running'
              AND revision = %s AND claim_expires_at > clock_timestamp()
            RETURNING {_TURN_COLS}
            """,
            (lease_seconds, world_id, turn_id, expected_revision),
        )
        row = cur.fetchone()
    return None if row is None else _turn_from_row(conn, row)


def complete_claimed_turn(
    conn: psycopg.Connection,
    *,
    world_id: str,
    turn_id: UUID,
    expected_revision: int,
    assistant_text: str,
    completion: PlanWorldGraphCompletion | None,
    graph_context_execution: PlanWorldGraphExecution | None = None,
) -> Turn | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""
            UPDATE agent.turn
            SET status = 'completed', revision = revision + 1,
                assistant_text = %s, failure_code = NULL,
                completion = %s,
                graph_context_execution = %s,
                claim_expires_at = NULL,
                completed_at = clock_timestamp(), updated_at = clock_timestamp()
            WHERE world_id = %s AND turn_id = %s AND status = 'running'
              AND revision = %s AND claim_expires_at > clock_timestamp()
            RETURNING {_TURN_COLS}
            """,
            (
                assistant_text,
                None
                if completion is None
                else Jsonb(completion.model_dump(mode="json", by_alias=True)),
                (
                    None
                    if graph_context_execution is None
                    else Jsonb(graph_context_execution.model_dump(mode="json", by_alias=True))
                ),
                world_id,
                turn_id,
                expected_revision,
            ),
        )
        row = cur.fetchone()
    return None if row is None else _turn_from_row(conn, row)


def update_graph_execution(
    conn: psycopg.Connection,
    *,
    world_id: str,
    turn_id: UUID,
    expected_revision: int,
    execution: PlanWorldGraphExecution,
) -> Turn | None:
    """Persist one validated execution append under the caller's locked row."""
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""
            UPDATE agent.turn
            SET graph_context_execution = %s, revision = revision + 1,
                updated_at = clock_timestamp()
            WHERE world_id = %s AND turn_id = %s AND status = 'running'
              AND revision = %s AND claim_expires_at > clock_timestamp()
            RETURNING {_TURN_COLS}
            """,
            (
                Jsonb(execution.model_dump(mode="json", by_alias=True)),
                world_id,
                turn_id,
                expected_revision,
            ),
        )
        row = cur.fetchone()
    return None if row is None else _turn_from_row(conn, row)


def interrupt_expired_graph_execution(
    conn: psycopg.Connection,
    *,
    world_id: str,
    turn_id: UUID,
    expected_revision: int,
    execution: PlanWorldGraphExecution,
    failure_code: str,
) -> Turn | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""
            UPDATE agent.turn
            SET graph_context_execution = %s, status = 'interrupted',
                revision = revision + 1, failure_code = %s,
                claim_expires_at = NULL, completed_at = clock_timestamp(),
                updated_at = clock_timestamp()
            WHERE world_id = %s AND turn_id = %s AND status = 'running'
              AND revision = %s AND claim_expires_at <= clock_timestamp()
            RETURNING {_TURN_COLS}
            """,
            (
                Jsonb(execution.model_dump(mode="json", by_alias=True)),
                failure_code,
                world_id,
                turn_id,
                expected_revision,
            ),
        )
        row = cur.fetchone()
    return None if row is None else _turn_from_row(conn, row)


def fail_claimed_turn(
    conn: psycopg.Connection,
    *,
    world_id: str,
    turn_id: UUID,
    expected_revision: int,
    status: str,
    failure_code: str,
) -> Turn | None:
    if status not in {"failed", "interrupted"}:
        raise ValueError("claim failure status must be failed or interrupted")
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""
            UPDATE agent.turn
            SET status = %s, revision = revision + 1,
                assistant_text = NULL, failure_code = %s,
                claim_expires_at = NULL,
                completed_at = clock_timestamp(), updated_at = clock_timestamp()
            WHERE world_id = %s AND turn_id = %s AND status = 'running'
              AND revision = %s AND claim_expires_at > clock_timestamp()
            RETURNING {_TURN_COLS}
            """,
            (status, failure_code, world_id, turn_id, expected_revision),
        )
        row = cur.fetchone()
    return None if row is None else _turn_from_row(conn, row)


def get_draft(
    conn: psycopg.Connection, world_id: str, conversation_id: UUID, draft_id: UUID
) -> tuple[Draft, str] | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""
            SELECT {_DRAFT_COLS} FROM agent.composer_draft
            WHERE world_id = %s AND conversation_id = %s AND draft_id = %s
            """,
            (world_id, conversation_id, draft_id),
        )
        row = cur.fetchone()
    if row is None:
        return None
    fingerprint = row["request_fingerprint"]
    return _draft_from_row(conn, row), fingerprint


def lock_draft(
    conn: psycopg.Connection, world_id: str, conversation_id: UUID, draft_id: UUID
) -> tuple[Draft, str] | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""
            SELECT {_DRAFT_COLS} FROM agent.composer_draft
            WHERE world_id = %s AND conversation_id = %s AND draft_id = %s FOR UPDATE
            """,
            (world_id, conversation_id, draft_id),
        )
        row = cur.fetchone()
    if row is None:
        return None
    fingerprint = row["request_fingerprint"]
    return _draft_from_row(conn, row), fingerprint


def save_draft(
    conn: psycopg.Connection,
    *,
    save: Any,
    save_fingerprint: str,
    revision: int,
    now: datetime,
    create: bool,
) -> Draft:
    provenance: TurnProvenance = save.provenance
    primary = provenance.primary_work
    selected = provenance.selected_object
    values = (
        save.world_id,
        save.conversation_id,
        save.draft_id,
        revision,
        save.body,
        save_fingerprint,
        provenance.surface_resolution,
        provenance.surface_id,
        provenance.surface_instance_id,
        primary.resolution,
        primary.kind,
        primary.object_id,
        primary.revision,
        primary.content_sha256,
        primary.object_revision,
        primary.work_revision_id,
        primary.revision_n,
        selected.resolution,
        selected.kind,
        selected.object_id,
        selected.revision,
        selected.content_sha256,
        selected.object_revision,
        selected.work_revision_id,
        selected.revision_n,
        model_fingerprint(provenance),
        None,
        now,
        now,
    )
    with conn.cursor(row_factory=dict_row) as cur:
        if create:
            cur.execute(
                f"""
                INSERT INTO agent.composer_draft (
                    world_id, conversation_id, draft_id, revision, body, request_fingerprint,
                    surface_resolution, surface_id, surface_instance_id,
                    primary_resolution, primary_kind,
                    primary_object_id, primary_revision, primary_content_sha256,
                    primary_object_revision, primary_work_revision_id, primary_revision_n,
                    selected_resolution, selected_kind, selected_object_id, selected_revision,
                    selected_content_sha256, selected_object_revision,
                    selected_work_revision_id, selected_revision_n,
                    source_fingerprint, retired_at, created_at, updated_at
                ) VALUES ({", ".join(["%s"] * len(values))}) RETURNING {_DRAFT_COLS}
                """,
                values,
            )
        else:
            cur.execute(
                f"""
                UPDATE agent.composer_draft
                SET revision = %s, body = %s, request_fingerprint = %s,
                    surface_resolution = %s, surface_id = %s,
                    surface_instance_id = %s,
                    primary_resolution = %s, primary_kind = %s, primary_object_id = %s,
                    primary_revision = %s, primary_content_sha256 = %s,
                    primary_object_revision = %s, primary_work_revision_id = %s,
                    primary_revision_n = %s,
                    selected_resolution = %s, selected_kind = %s, selected_object_id = %s,
                    selected_revision = %s, selected_content_sha256 = %s,
                    selected_object_revision = %s, selected_work_revision_id = %s,
                    selected_revision_n = %s,
                    source_fingerprint = %s, updated_at = %s
                WHERE world_id = %s AND conversation_id = %s AND draft_id = %s
                RETURNING {_DRAFT_COLS}
                """,
                (
                    revision,
                    save.body,
                    save_fingerprint,
                    provenance.surface_resolution,
                    provenance.surface_id,
                    provenance.surface_instance_id,
                    primary.resolution,
                    primary.kind,
                    primary.object_id,
                    primary.revision,
                    primary.content_sha256,
                    primary.object_revision,
                    primary.work_revision_id,
                    primary.revision_n,
                    selected.resolution,
                    selected.kind,
                    selected.object_id,
                    selected.revision,
                    selected.content_sha256,
                    selected.object_revision,
                    selected.work_revision_id,
                    selected.revision_n,
                    model_fingerprint(provenance),
                    now,
                    save.world_id,
                    save.conversation_id,
                    save.draft_id,
                ),
            )
        row = cur.fetchone()
    _replace_draft_references(conn, save.draft_id, provenance.supporting_work)
    if row is None:
        raise ApplicationStateIntegrityError("draft save did not persist")
    return _draft_from_row(conn, row)


def _replace_draft_references(
    conn: psycopg.Connection, draft_id: UUID, references: list[HistoricalReference]
) -> None:
    conn.execute("DELETE FROM agent.draft_reference WHERE draft_id = %s", (draft_id,))
    for ordinal, reference in enumerate(references):
        conn.execute(
            """
            INSERT INTO agent.draft_reference (
                draft_id, ordinal, resolution, kind, object_id, revision,
                content_sha256, object_revision, work_revision_id, revision_n
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (draft_id, ordinal, *_reference_values(reference)),
        )


def retire_draft(
    conn: psycopg.Connection,
    *,
    world_id: str,
    conversation_id: UUID,
    draft_id: UUID,
    expected_revision: int,
    retired_at: datetime,
) -> Draft | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""
            UPDATE agent.composer_draft SET retired_at = %s, updated_at = %s
            WHERE world_id = %s AND conversation_id = %s AND draft_id = %s
              AND revision = %s AND retired_at IS NULL
            RETURNING {_DRAFT_COLS}
            """,
            (
                retired_at,
                retired_at,
                world_id,
                conversation_id,
                draft_id,
                expected_revision,
            ),
        )
        row = cur.fetchone()
    return None if row is None else _draft_from_row(conn, row)


def get_import_receipt(
    conn: psycopg.Connection, world_id: str, source_import_key: str
) -> tuple[LegacyImportReceipt, str] | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT world_id, source_import_key, conversation_id,
                   active_conversation_id, pointer_revision, imported_turn_count,
                   recorded_at, request_fingerprint
            FROM agent.import_receipt WHERE world_id = %s AND source_import_key = %s
            """,
            (world_id, source_import_key),
        )
        row = cur.fetchone()
    if row is None:
        return None
    fingerprint = row.pop("request_fingerprint")
    return LegacyImportReceipt.model_validate(row), fingerprint


def insert_import_receipt(
    conn: psycopg.Connection,
    *,
    world_id: str,
    source_import_key: str,
    source_thread_id: str,
    request_fingerprint: str,
    conversation_id: UUID,
    active_conversation_id: UUID | None,
    pointer_revision: int,
    imported_turn_count: int,
    recorded_at: datetime,
) -> LegacyImportReceipt:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            INSERT INTO agent.import_receipt (
                world_id, source_import_key, source_thread_id, request_fingerprint,
                conversation_id, active_conversation_id, pointer_revision,
                imported_turn_count, recorded_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING world_id, source_import_key, conversation_id,
                      active_conversation_id, pointer_revision, imported_turn_count, recorded_at
            """,
            (
                world_id,
                source_import_key,
                source_thread_id,
                request_fingerprint,
                conversation_id,
                active_conversation_id,
                pointer_revision,
                imported_turn_count,
                recorded_at,
            ),
        )
        row = cur.fetchone()
    if row is None:
        raise ApplicationStateIntegrityError("legacy import receipt did not persist")
    return LegacyImportReceipt.model_validate(row)


def insert_legacy_turn(
    conn: psycopg.Connection,
    *,
    turn_id: UUID,
    conversation_id: UUID,
    world_id: str,
    idempotency_key: UUID,
    sequence: int,
    request_fingerprint: str,
    legacy_turn: Any,
    now: datetime,
) -> Turn:
    provenance: TurnProvenance = legacy_turn.provenance
    assistant_text = legacy_turn.assistant_text
    status = "interrupted" if assistant_text is None else "completed"
    submission = type(
        "LegacySubmission",
        (),
        {
            "world_id": world_id,
            "conversation_id": conversation_id,
            "idempotency_key": idempotency_key,
            "user_text": legacy_turn.user_text,
            "provenance": provenance,
        },
    )
    return insert_turn(
        conn,
        turn_id=turn_id,
        request_fingerprint=request_fingerprint,
        idempotency_fingerprint=turn_idempotency_fingerprint(
            world_id, legacy_turn.user_text, provenance
        ),
        submission=submission,
        sequence=sequence,
        now=now,
        status=status,
        assistant_text=assistant_text,
        failure_code="legacy_unanswered" if assistant_text is None else None,
    )



def _resolution_row(row: dict[str, Any] | None) -> CommandResolutionRecordV1 | None:
    if row is None:
        return None
    try:
        record = CommandResolutionRecordV1.model_validate(row["record"])
    except ValidationError as exc:
        raise ApplicationStateIntegrityError("stored command resolution is invalid") from exc
    command = record.request.original_command
    if (row["world_id"] != command.world_id or row["resolution_operation_id"] != record.request.resolution_operation_id
        or row["original_command_id"] != command.command_id or row["outcome"] != record.outcome
        or row["original_request_fingerprint"] != record.original_request_fingerprint
        or row["resolution_request_fingerprint"] != record.resolution_request_fingerprint
        or row["occupied_command_id"] != (None if record.outcome == "retired" else command.command_id)):
        raise ApplicationStateIntegrityError("stored command resolution columns disagree")
    return record


def get_command_resolution(conn: psycopg.Connection, world_id: str, operation_id: UUID) -> CommandResolutionRecordV1 | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT * FROM agent.command_resolution WHERE world_id=%s AND resolution_operation_id=%s", (world_id, operation_id))
        return _resolution_row(cur.fetchone())


def get_command_retirement(conn: psycopg.Connection, world_id: str, command_id: UUID) -> CommandResolutionRecordV1 | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT * FROM agent.command_resolution WHERE world_id=%s AND original_command_id=%s AND outcome='retired'", (world_id, command_id))
        return _resolution_row(cur.fetchone())


def insert_command_resolution(conn: psycopg.Connection, record: CommandResolutionRecordV1) -> CommandResolutionRecordV1:
    command = record.request.original_command
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("""INSERT INTO agent.command_resolution(world_id,resolution_operation_id,original_command_id,
            original_request_fingerprint,resolution_request_fingerprint,outcome,occupied_command_id,record)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING *""", (command.world_id, record.request.resolution_operation_id,
            command.command_id, record.original_request_fingerprint, record.resolution_request_fingerprint, record.outcome,
            None if record.outcome == "retired" else command.command_id, Jsonb(record.model_dump(mode="json", by_alias=True))))
        result = _resolution_row(cur.fetchone())
    if result is None:
        raise ApplicationStateIntegrityError("command resolution did not persist")
    return result
