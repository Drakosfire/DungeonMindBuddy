"""Persist the confirmed request before calling the statblock service."""

from uuid import uuid4

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from application_state.agent_conversation.conversation_drafts import edit_draft, open_draft
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


def store_correction(conn, *, world_id, conversation_id, turn_id, review_id, expected_revision, definition, markdown):
    scope = dict(world_id=world_id, conversation_id=conversation_id, turn_id=turn_id)
    # This is the same lock used by the existing save claim and draft edit.
    locked = conn.execute(
        "SELECT turn_id FROM agent.turn WHERE world_id=%s AND conversation_id=%s AND turn_id=%s FOR UPDATE",
        (world_id, conversation_id, turn_id),
    ).fetchone()
    if locked is None:
        raise ApplicationStateNotFoundError("Conversation draft not found")
    prior = open_review(conn, **scope, review_id=review_id)
    draft = open_draft(conn, **scope)
    if prior["revision"] != expected_revision or draft["revision"] != expected_revision:
        raise ApplicationStateConflictError("The reviewed draft changed. Reopen it before editing.")
    save = conn.execute(
        "SELECT 1 FROM agent.conversation_variant_save WHERE turn_id=%s AND revision=%s",
        (turn_id, expected_revision),
    ).fetchone()
    if save is not None:
        raise ApplicationStateConflictError("A save for this reviewed revision has already started.")
    updated = edit_draft(conn, **scope, expected_revision=expected_revision, markdown=markdown)
    if updated["revision"] == expected_revision:
        raise ApplicationStateConflictError("The correction did not change the editable mechanics.")
    new_id = uuid4()
    store_review(conn, **scope, revision=updated["revision"], review_id=new_id,
                 definition=definition, base_locator=prior["base_locator"])
    return {"revision": updated["revision"], "review_id": new_id}


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


def approval_handoff(conn, *, world_id, conversation_id, prior_to, accepted_at, page_id, page_kind):
    """Find an exact current review on the same Build page, without choosing among reviews."""
    with conn.cursor(row_factory=dict_row) as cursor:
        candidates = cursor.execute(
            """
            SELECT review.turn_id, review.review_id, review.revision,
                   current_draft.revision = review.revision AS is_current
            FROM agent.conversation_variant_review AS review
            JOIN agent.turn AS producer USING (turn_id)
            JOIN agent.turn_reference AS origin ON origin.turn_id = producer.turn_id
            JOIN LATERAL (
                SELECT revision FROM agent.conversation_draft_revision AS draft
                WHERE draft.world_id = producer.world_id
                  AND draft.conversation_id = producer.conversation_id
                  AND draft.turn_id = producer.turn_id
                ORDER BY revision DESC LIMIT 1
            ) AS current_draft ON true
            WHERE producer.world_id = %s AND producer.conversation_id = %s
              AND producer.sequence < %s AND producer.status = 'completed'
              AND producer.surface_id = 'build'
              AND origin.reference_role = 'primary' AND origin.resolution = 'resolved'
              AND origin.object_id = %s AND origin.kind = %s
              AND review.revision = (
                  SELECT max(at_approval.revision)
                  FROM agent.conversation_draft_revision AS at_approval
                  JOIN agent.conversation_variant_review AS reviewed_at_approval
                    ON reviewed_at_approval.turn_id = at_approval.turn_id
                   AND reviewed_at_approval.revision = at_approval.revision
                  WHERE at_approval.turn_id = producer.turn_id AND at_approval.created_at <= %s
              )
            LIMIT 2
            """,
            (world_id, conversation_id, prior_to, page_id, page_kind, accepted_at),
        ).fetchall()
    if len(candidates) > 1:
        return {"status": "ambiguous"}
    if not candidates:
        return {"status": "unavailable"}
    candidate, = candidates
    if not candidate.pop("is_current"):
        return {"status": "stale"}
    return {"status": "ready", **candidate}


def requested_approval(turn):
    """Recognize only the durable, explicit Build review action."""
    from .rules_authority_reads import MixedCompletedTurnV1
    from .types import BuildRequestedWorkResolutionV1

    record = turn.envelope if isinstance(turn, MixedCompletedTurnV1) else turn
    if record.status != "completed" or record.provenance.surface_id != "build":
        return False
    execution = (
        turn.base_projection.graph_context_execution
        if isinstance(turn, MixedCompletedTurnV1) else getattr(turn, "graph_context_execution", None)
    )
    choices = [
        event for event in execution.events if isinstance(event, BuildRequestedWorkResolutionV1)
    ] if execution is not None else []
    return len(choices) == 1 and choices[0].requested_work == "review_variant_approval"
