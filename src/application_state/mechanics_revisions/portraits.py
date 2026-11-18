"""Immutable portrait snapshots for saved mechanics revisions."""
from application_state.config import load_runtime_dsn
from application_state.errors import ApplicationStateConflictError
from application_state.unit_of_work import unit_of_work


def read_portrait(*, world_id, draft_id, revision_id):
    with unit_of_work(load_runtime_dsn()) as conn:
        row = conn.execute(
            """SELECT jpeg_base64 FROM world_mechanics.saved_portrait
               WHERE world_id = %s AND draft_id = %s AND revision_id = %s""",
            (world_id, draft_id, revision_id),
        ).fetchone()
    return row[0] if row else None


def retain_portrait(*, world_id, draft_id, revision_id, jpeg_base64):
    with unit_of_work(load_runtime_dsn()) as conn:
        conn.execute(
            """INSERT INTO world_mechanics.saved_portrait
               (world_id, draft_id, revision_id, jpeg_base64) VALUES (%s, %s, %s, %s)
               ON CONFLICT DO NOTHING""",
            (world_id, draft_id, revision_id, jpeg_base64),
        )
        row = conn.execute(
            """SELECT jpeg_base64 FROM world_mechanics.saved_portrait
               WHERE world_id = %s AND draft_id = %s AND revision_id = %s""",
            (world_id, draft_id, revision_id),
        ).fetchone()
        if row is None or row[0] != jpeg_base64:
            raise ApplicationStateConflictError("The saved revision already has a different portrait")
