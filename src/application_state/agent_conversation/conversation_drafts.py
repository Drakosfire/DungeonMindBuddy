"""Persist editable assistant drafts without rewriting their producing turns."""

from psycopg.rows import dict_row

from application_state.errors import (
    ApplicationStateConflictError,
    ApplicationStateNotFoundError,
)


# Legacy initial drafts copied assistant_text verbatim. Later reviewed
# corrections are written from their validated mechanics as new revisions.
CANONICAL_REVIEWED_DRAFT = """
EXISTS (
    SELECT 1 FROM agent.conversation_draft_revision d
    JOIN agent.conversation_variant_review r
        ON r.turn_id = d.turn_id AND r.revision = d.revision
    WHERE d.turn_id = t.turn_id AND d.world_id = t.world_id
      AND d.conversation_id = t.conversation_id
      AND (d.revision > 1 OR d.markdown IS DISTINCT FROM t.assistant_text)
      AND NOT EXISTS (
          SELECT 1 FROM agent.conversation_draft_revision later
          WHERE later.turn_id = d.turn_id AND later.revision > d.revision
      )
)
"""


def open_draft(conn, *, world_id, conversation_id, turn_id):
    with conn.cursor(row_factory=dict_row) as cursor:
        row = cursor.execute(
            """
            SELECT draft.revision, draft.markdown, (
                SELECT array_agg(review.review_id ORDER BY review.review_id)
                FROM agent.conversation_variant_review AS review
                WHERE review.turn_id = draft.turn_id AND review.revision = draft.revision
            ) AS variant_review_ids
            FROM agent.conversation_draft_revision AS draft
            WHERE draft.world_id = %s AND draft.conversation_id = %s AND draft.turn_id = %s
            ORDER BY draft.revision DESC LIMIT 1
            """,
            (world_id, conversation_id, turn_id),
        ).fetchone()
    if row is None:
        raise ApplicationStateNotFoundError("Conversation draft not found")
    if row["variant_review_ids"] is None:
        del row["variant_review_ids"]
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
                (world_id, conversation_id, turn_id, revision, markdown, created_at)
            VALUES (%s, %s, %s, %s, %s, clock_timestamp())
            RETURNING revision, markdown
            """,
            (*scope, expected_revision + 1, markdown),
        ).fetchone()
