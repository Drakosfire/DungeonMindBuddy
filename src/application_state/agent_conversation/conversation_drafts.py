"""Persist editable assistant drafts without rewriting their producing turns."""

from psycopg.rows import dict_row

from application_state.errors import (
    ApplicationStateConflictError,
    ApplicationStateNotFoundError,
)


def open_draft(conn, *, world_id, conversation_id, turn_id):
    with conn.cursor(row_factory=dict_row) as cursor:
        row = cursor.execute(
            """
            SELECT revision, markdown FROM agent.conversation_draft_revision
            WHERE world_id = %s AND conversation_id = %s AND turn_id = %s
            ORDER BY revision DESC LIMIT 1
            """,
            (world_id, conversation_id, turn_id),
        ).fetchone()
    if row is None:
        raise ApplicationStateNotFoundError("Conversation draft not found")
    return row


def create_draft(conn, *, world_id, conversation_id, turn_id, markdown):
    """Called by turn completion only for an explicitly requested chat draft."""
    with conn.cursor(row_factory=dict_row) as cursor:
        return cursor.execute(
            """
            INSERT INTO agent.conversation_draft_revision
                (world_id, conversation_id, turn_id, revision, markdown)
            VALUES (%s, %s, %s, 1, %s)
            RETURNING revision, markdown
            """,
            (world_id, conversation_id, turn_id, markdown),
        ).fetchone()


def edit_draft(conn, *, world_id, conversation_id, turn_id, expected_revision, markdown):
    """Serialize draft edits on the producing turn inside the caller's transaction."""
    scope = (world_id, conversation_id, turn_id)
    turn = conn.execute(
        """
        SELECT turn_id FROM agent.turn
        WHERE world_id = %s AND conversation_id = %s AND turn_id = %s
        FOR UPDATE
        """,
        scope,
    ).fetchone()
    if turn is None:
        raise ApplicationStateNotFoundError("Conversation draft not found")

    current = open_draft(
        conn, world_id=world_id, conversation_id=conversation_id, turn_id=turn_id,
    )
    if current["revision"] != expected_revision:
        raise ApplicationStateConflictError("Conversation draft changed. Reopen it before editing.")
    if current["markdown"] == markdown:
        return current

    with conn.cursor(row_factory=dict_row) as cursor:
        return cursor.execute(
            """
            INSERT INTO agent.conversation_draft_revision
                (world_id, conversation_id, turn_id, revision, markdown)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING revision, markdown
            """,
            (*scope, expected_revision + 1, markdown),
        ).fetchone()
