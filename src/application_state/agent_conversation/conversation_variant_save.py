"""Persist the confirmed request before calling the statblock service."""

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from application_state.agent_conversation.conversation_drafts import open_draft
from application_state.errors import (
    ApplicationStateConflictError,
    ApplicationStateNotFoundError,
)


def find_save(conn, *, world_id, conversation_id, turn_id, revision, create_request):
    with conn.cursor(row_factory=dict_row) as cursor:
        row = cursor.execute(
            """
            SELECT save.create_request, save.receipt
            FROM agent.conversation_variant_save AS save
            JOIN agent.turn AS turn ON turn.turn_id = save.turn_id
            WHERE turn.world_id = %s AND turn.conversation_id = %s
              AND save.turn_id = %s AND save.revision = %s
            """,
            (world_id, conversation_id, turn_id, revision),
        ).fetchone()
    if row is not None and row["create_request"] != create_request:
        raise ApplicationStateConflictError("This revision already has a different confirmed save.")
    return row


def claim_save(conn, *, world_id, conversation_id, turn_id, revision, create_request):
    # Share the draft edit lock so confirmation and edits have a definite order.
    turn = conn.execute(
        """
        SELECT turn_id FROM agent.turn
        WHERE world_id = %s AND conversation_id = %s AND turn_id = %s
        FOR UPDATE
        """,
        (world_id, conversation_id, turn_id),
    ).fetchone()
    if turn is None:
        raise ApplicationStateNotFoundError("Conversation draft not found")

    existing = find_save(
        conn, world_id=world_id, conversation_id=conversation_id, turn_id=turn_id,
        revision=revision, create_request=create_request,
    )
    if existing is not None:
        return existing["receipt"]

    draft = open_draft(conn, world_id=world_id, conversation_id=conversation_id, turn_id=turn_id)
    if draft["revision"] != revision:
        raise ApplicationStateConflictError("Conversation draft changed. Reopen it before saving.")

    conn.execute(
        """
        INSERT INTO agent.conversation_variant_save (turn_id, revision, create_request)
        VALUES (%s, %s, %s)
        """,
        (turn_id, revision, Jsonb(create_request)),
    )
    return None


def record_receipt(conn, *, world_id, conversation_id, turn_id, revision, receipt):
    row = conn.execute(
        """
        UPDATE agent.conversation_variant_save AS save
        SET receipt = COALESCE(save.receipt, %(receipt)s)
        FROM agent.turn AS turn
        WHERE save.turn_id = turn.turn_id AND save.turn_id = %(turn_id)s
          AND save.revision = %(revision)s AND turn.world_id = %(world_id)s
          AND turn.conversation_id = %(conversation_id)s
          AND (save.receipt IS NULL OR save.receipt = %(receipt)s)
        RETURNING save.receipt
        """,
        dict(
            world_id=world_id, conversation_id=conversation_id, turn_id=turn_id,
            revision=revision, receipt=Jsonb(receipt),
        ),
    ).fetchone()
    if row is None:
        raise ApplicationStateConflictError("Confirmed save is missing or has a different receipt.")
    return receipt


def store_review(conn, *, world_id, conversation_id, turn_id, revision, review_id, definition, base_locator):
    row = conn.execute(
        """
        INSERT INTO agent.conversation_variant_review
            (review_id, turn_id, revision, definition, base_locator)
        SELECT %s, draft.turn_id, draft.revision, %s, %s
        FROM agent.conversation_draft_revision AS draft
        WHERE draft.world_id = %s AND draft.conversation_id = %s
          AND draft.turn_id = %s AND draft.revision = %s
        RETURNING review_id
        """,
        (review_id, Jsonb(definition), Jsonb(base_locator), world_id, conversation_id, turn_id, revision),
    ).fetchone()
    if row is None:
        raise ApplicationStateNotFoundError("Conversation draft revision not found")


def open_review(conn, *, world_id, conversation_id, turn_id, review_id):
    with conn.cursor(row_factory=dict_row) as cursor:
        row = cursor.execute(
            """
            SELECT review.revision, review.definition, review.base_locator,
                   EXISTS (
                       SELECT 1 FROM agent.conversation_variant_save AS save
                       WHERE save.turn_id = review.turn_id AND save.revision = review.revision
                         AND save.create_request #>> '{accepted_through,conversation_variant_review}' = review.review_id::text
                         AND save.receipt IS NOT NULL
                   ) AS saved
            FROM agent.conversation_variant_review AS review
            JOIN agent.turn AS turn ON turn.turn_id = review.turn_id
            WHERE turn.world_id = %s AND turn.conversation_id = %s
              AND review.turn_id = %s AND review.review_id = %s
            """,
            (world_id, conversation_id, turn_id, review_id),
        ).fetchone()
    if row is None:
        raise ApplicationStateNotFoundError("Conversation variant review not found")
    return row


def open_saved_receipt(conn, *, world_id, conversation_id, turn_id, review_id):
    row = conn.execute(
        """
        SELECT save.receipt
        FROM agent.conversation_variant_review AS review
        JOIN agent.turn AS turn ON turn.turn_id = review.turn_id
        JOIN agent.conversation_variant_save AS save
          ON save.turn_id = review.turn_id AND save.revision = review.revision
        WHERE turn.world_id = %s AND turn.conversation_id = %s
          AND review.turn_id = %s AND review.review_id = %s
          AND save.create_request #>> '{accepted_through,conversation_variant_review}' = %s
          AND save.receipt IS NOT NULL
        """,
        (world_id, conversation_id, turn_id, review_id, str(review_id)),
    ).fetchone()
    if row is None:
        raise ApplicationStateNotFoundError("Saved conversation variant not found")
    return row[0]
