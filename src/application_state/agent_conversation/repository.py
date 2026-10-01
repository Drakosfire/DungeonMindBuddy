"""SQL repository for the typed Agent Conversation domain."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

import psycopg
from psycopg.rows import dict_row

from application_state.agent_conversation.types import (
    Conversation,
    ConversationCommandReceipt,
    Draft,
    HistoricalReference,
    LegacyImportReceipt,
    Turn,
    TurnProvenance,
    WorldPointer,
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
    surface_id, attempt, accepted_at, completed_at, updated_at
"""
_DRAFT_COLS = """
    world_id, conversation_id, draft_id, revision, body, request_fingerprint,
    surface_resolution, surface_id, primary_resolution, primary_kind,
    primary_object_id, primary_revision, primary_content_sha256,
    selected_resolution, selected_kind, selected_object_id, selected_revision,
    selected_content_sha256, source_fingerprint, retired_at, created_at, updated_at
"""


def _reference_from_row(row: dict[str, Any]) -> HistoricalReference:
    return HistoricalReference(
        resolution=row["resolution"],
        kind=row["kind"],
        object_id=row["object_id"],
        revision=row["revision"],
        content_sha256=row["content_sha256"],
    )


def _reference_values(reference: HistoricalReference) -> tuple[Any, ...]:
    return (
        reference.resolution,
        reference.kind,
        reference.object_id,
        reference.revision,
        reference.content_sha256,
    )


def _turn_references(conn: psycopg.Connection, turn_id: UUID) -> tuple[HistoricalReference, list[HistoricalReference], HistoricalReference]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT reference_role, ordinal, resolution, kind, object_id, revision, content_sha256
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
        raise ApplicationStateIntegrityError("turn is missing typed primary/selected provenance")
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
        primary_work=primary,
        supporting_work=supporting,
        selected_object=selected,
    )
    return Turn(
        **{key: row[key] for key in row if key not in {"surface_resolution", "surface_id"}},
        provenance=provenance,
    )


def _draft_references(conn: psycopg.Connection, draft_id: UUID) -> list[HistoricalReference]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT resolution, kind, object_id, revision, content_sha256
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
        primary_work=HistoricalReference(
            resolution=row["primary_resolution"],
            kind=row["primary_kind"],
            object_id=row["primary_object_id"],
            revision=row["primary_revision"],
            content_sha256=row["primary_content_sha256"],
        ),
        supporting_work=_draft_references(conn, row["draft_id"]),
        selected_object=HistoricalReference(
            resolution=row["selected_resolution"],
            kind=row["selected_kind"],
            object_id=row["selected_object_id"],
            revision=row["selected_revision"],
            content_sha256=row["selected_content_sha256"],
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
        cur.execute(f"SELECT {_WORLD_COLS} FROM agent.world_state WHERE world_id = %s", (world_id,))
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
        raise ApplicationStateIntegrityError("conversation command receipt did not persist")
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
            (conversation_id, world_id, status, revision, next_turn_sequence, now, now, archived_at),
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
            (status, next_turn_sequence, now, archived_at, world_id, conversation_id, expected_revision),
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


def get_active_conversation(conn: psycopg.Connection, world_id: str) -> Conversation | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""
            SELECT c.{_CONVERSATION_COLS.replace(', ', ', c.')}
            FROM agent.world_state AS w
            JOIN agent.conversation AS c
              ON c.conversation_id = w.active_conversation_id AND c.world_id = w.world_id
            WHERE w.world_id = %s
            """,
            (world_id,),
        )
        row = cur.fetchone()
    return None if row is None else Conversation.model_validate(row)


def get_turn_by_key(
    conn: psycopg.Connection, world_id: str, conversation_id: UUID, idempotency_key: UUID
) -> tuple[Turn, str] | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""
            SELECT {_TURN_COLS}, request_fingerprint
            FROM agent.turn WHERE world_id = %s AND conversation_id = %s AND idempotency_key = %s
            """,
            (world_id, conversation_id, idempotency_key),
        )
        row = cur.fetchone()
    if row is None:
        return None
    fingerprint = row.pop("request_fingerprint")
    return _turn_from_row(conn, row), fingerprint


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
    conn: psycopg.Connection, world_id: str, conversation_id: UUID, *, limit: int, before_sequence: int | None
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
            WHERE {' AND '.join(clauses)} ORDER BY sequence DESC LIMIT %s
            """,
            params,
        )
        rows = cur.fetchall()
    return [_turn_from_row(conn, row) for row in reversed(rows)]


def insert_turn(
    conn: psycopg.Connection,
    *,
    turn_id: UUID,
    request_fingerprint: str,
    submission: Any,
    sequence: int,
    now: datetime,
    status: str = "accepted",
    assistant_text: str | None = None,
    failure_code: str | None = None,
    attempt: int = 0,
) -> Turn:
    provenance: TurnProvenance = submission.provenance
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""
            INSERT INTO agent.turn (
                turn_id, conversation_id, world_id, idempotency_key, sequence,
                revision, status, request_fingerprint, user_text, assistant_text,
                failure_code, surface_resolution, surface_id, attempt, accepted_at,
                completed_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, 1, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                      %s, %s)
            RETURNING {_TURN_COLS}
            """,
            (
                turn_id,
                submission.conversation_id,
                submission.world_id,
                submission.idempotency_key,
                sequence,
                status,
                request_fingerprint,
                submission.user_text,
                assistant_text,
                failure_code,
                provenance.surface_resolution,
                provenance.surface_id,
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
            turn_id, reference_role, ordinal, resolution, kind, object_id, revision, content_sha256
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (turn_id, role, ordinal, *_reference_values(reference)),
    )


def update_turn_state(
    conn: psycopg.Connection,
    *,
    turn_id: UUID,
    world_id: str,
    expected_revision: int,
    status: str,
    assistant_text: str | None,
    failure_code: str | None,
    attempt: int,
    completed_at: datetime | None,
    updated_at: datetime,
) -> Turn | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""
            UPDATE agent.turn
            SET status = %s, revision = revision + 1, assistant_text = %s,
                failure_code = %s, attempt = %s, completed_at = %s, updated_at = %s
            WHERE world_id = %s AND turn_id = %s AND revision = %s
            RETURNING {_TURN_COLS}
            """,
            (
                status,
                assistant_text,
                failure_code,
                attempt,
                completed_at,
                updated_at,
                world_id,
                turn_id,
                expected_revision,
            ),
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
        primary.resolution,
        primary.kind,
        primary.object_id,
        primary.revision,
        primary.content_sha256,
        selected.resolution,
        selected.kind,
        selected.object_id,
        selected.revision,
        selected.content_sha256,
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
                    surface_resolution, surface_id, primary_resolution, primary_kind,
                    primary_object_id, primary_revision, primary_content_sha256,
                    selected_resolution, selected_kind, selected_object_id, selected_revision,
                    selected_content_sha256, source_fingerprint, retired_at, created_at, updated_at
                ) VALUES ({', '.join(['%s'] * 22)}) RETURNING {_DRAFT_COLS}
                """,
                values,
            )
        else:
            cur.execute(
                f"""
                UPDATE agent.composer_draft
                SET revision = %s, body = %s, request_fingerprint = %s,
                    surface_resolution = %s, surface_id = %s,
                    primary_resolution = %s, primary_kind = %s, primary_object_id = %s,
                    primary_revision = %s, primary_content_sha256 = %s,
                    selected_resolution = %s, selected_kind = %s, selected_object_id = %s,
                    selected_revision = %s, selected_content_sha256 = %s,
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
                    primary.resolution,
                    primary.kind,
                    primary.object_id,
                    primary.revision,
                    primary.content_sha256,
                    selected.resolution,
                    selected.kind,
                    selected.object_id,
                    selected.revision,
                    selected.content_sha256,
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
                draft_id, ordinal, resolution, kind, object_id, revision, content_sha256
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
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
            (retired_at, retired_at, world_id, conversation_id, draft_id, expected_revision),
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
        submission=submission,
        sequence=sequence,
        now=now,
        status=status,
        assistant_text=assistant_text,
        failure_code="legacy_unanswered" if assistant_text is None else None,
    )
