"""Save a portrait append intent under its authorized conversation review."""

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from application_state.errors import ApplicationStateConflictError
from .conversation_variant_save import open_saved_receipt


def _read(conn, *, review_id, operation_id):
    with conn.cursor(row_factory=dict_row) as cursor:
        return cursor.execute(
            """
            SELECT intent, append_request, receipt, refusal
            FROM agent.conversation_variant_portrait
            WHERE review_id = %s AND operation_id = %s
            """,
            (review_id, operation_id),
        ).fetchone()


def read(conn, *, operation_id, **scope):
    original = open_saved_receipt(conn, **scope)
    return original, _read(conn, review_id=scope["review_id"], operation_id=operation_id)


def claim(conn, *, operation_id, intent, append_request, **scope):
    review_id = scope["review_id"]
    open_saved_receipt(conn, **scope)
    conn.execute(
        "SELECT review_id FROM agent.conversation_variant_review WHERE review_id = %s FOR UPDATE",
        (review_id,),
    )
    existing = _read(conn, review_id=review_id, operation_id=operation_id)
    if existing is not None:
        if existing["intent"] != intent:
            raise ApplicationStateConflictError("This Save key belongs to a different portrait selection.")
        return existing
    if conn.execute(
        """
        SELECT 1 FROM agent.conversation_variant_portrait
        WHERE review_id = %s AND receipt IS NULL AND refusal IS NULL
        """,
        (review_id,),
    ).fetchone():
        raise ApplicationStateConflictError("Retry the pending portrait Save before making another revision.")
    created = conn.execute(
        """
        INSERT INTO agent.conversation_variant_portrait
            (operation_id, review_id, intent, append_request)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (operation_id) DO NOTHING
        RETURNING operation_id
        """,
        (operation_id, review_id, Jsonb(intent), Jsonb(append_request)),
    ).fetchone()
    if created is None:
        raise ApplicationStateConflictError("This Save key belongs to another review.")
    return _read(conn, review_id=review_id, operation_id=operation_id)


def settle(conn, *, operation_id, receipt=None, refusal=None, **scope):
    open_saved_receipt(conn, **scope)
    updated = conn.execute(
        """
        UPDATE agent.conversation_variant_portrait
        SET receipt = %s, refusal = %s
        WHERE review_id = %s AND operation_id = %s
          AND ((receipt IS NULL AND refusal IS NULL)
               OR (receipt IS NOT DISTINCT FROM %s AND refusal IS NOT DISTINCT FROM %s))
        RETURNING operation_id
        """,
        (Jsonb(receipt) if receipt else None, refusal, scope["review_id"], operation_id,
         Jsonb(receipt) if receipt else None, refusal),
    ).fetchone()
    if updated is None:
        raise ApplicationStateConflictError("Portrait Save already has a different outcome.")
