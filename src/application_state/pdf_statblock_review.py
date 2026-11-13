"""World-scoped storage for editable PDF statblock review drafts."""
from psycopg.types.json import Jsonb

from application_state.cli import assert_at_head
from application_state.config import load_runtime_dsn
from application_state.errors import ApplicationStateConflictError
from application_state.unit_of_work import unit_of_work


def read_review(*, world_id, review_id):
    dsn = load_runtime_dsn()
    assert_at_head(dsn=dsn)
    with unit_of_work(dsn) as conn:
        row = conn.execute(
            "SELECT revision, payload FROM public.pdf_statblock_review WHERE world_id = %s AND review_id = %s",
            (world_id, review_id),
        ).fetchone()
    if row is None:
        return None
    return {"revision": row[0], **row[1]}


def save_review(*, world_id, review_id, expected_revision, definition, regions):
    dsn = load_runtime_dsn()
    assert_at_head(dsn=dsn)
    payload = {"definition": definition, "regions": regions}
    with unit_of_work(dsn) as conn:
        if expected_revision == 0:
            row = conn.execute(
                """INSERT INTO public.pdf_statblock_review (world_id, review_id, revision, payload)
                   VALUES (%s, %s, 1, %s) ON CONFLICT DO NOTHING RETURNING revision""",
                (world_id, review_id, Jsonb(payload)),
            ).fetchone()
        else:
            row = conn.execute(
                """UPDATE public.pdf_statblock_review
                   SET revision = revision + 1, payload = %s
                   WHERE world_id = %s AND review_id = %s AND revision = %s
                     AND payload->'regions' = %s
                   RETURNING revision""",
                (Jsonb(payload), world_id, review_id, expected_revision, Jsonb(regions)),
            ).fetchone()
        if row is None:
            raise ApplicationStateConflictError("Review changed or its source regions do not match")
    return {"revision": row[0], **payload}
