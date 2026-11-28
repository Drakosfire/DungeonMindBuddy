"""Retain identifier-only receipts for World statblock deletion."""

from alembic import op

revision = "20261128_0216"
down_revision = "20261126_0215"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE mechanics_revision.purge (
            statblock_id text PRIMARY KEY CHECK (statblock_id ~ '^sb_[a-z0-9]+$'),
            world_id text NOT NULL,
            draft_id uuid NOT NULL UNIQUE,
            draft_version integer NOT NULL CHECK (draft_version > 0),
            expected_revision_id text NOT NULL CHECK (expected_revision_id ~ '^rev_[a-z0-9]+$'),
            complete boolean NOT NULL DEFAULT false
        )
    """)
    op.execute("""
        CREATE FUNCTION mechanics_revision.complete_statblock_purge(text, text, uuid, integer, text)
        RETURNS boolean LANGUAGE sql SECURITY DEFINER SET search_path = pg_catalog AS $$
            WITH exact_receipt AS (
                UPDATE mechanics_revision.purge SET complete=true
                WHERE statblock_id=$1 AND world_id=$2 AND draft_id=$3
                  AND draft_version=$4 AND expected_revision_id=$5
                RETURNING statblock_id, world_id, draft_id
            ), removed AS (
                DELETE FROM mechanics_revision.operation AS operation USING exact_receipt AS receipt
                WHERE operation.statblock_id=receipt.statblock_id AND operation.world_id=receipt.world_id
                  AND operation.draft_id=receipt.draft_id
            )
            SELECT EXISTS (SELECT FROM exact_receipt)
        $$;
        REVOKE EXECUTE ON FUNCTION mechanics_revision.complete_statblock_purge(text, text, uuid, integer, text)
            FROM PUBLIC;
    """)
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'dmb_app_runtime') THEN
                GRANT SELECT ON mechanics_revision.purge TO dmb_app_runtime;
                GRANT INSERT (statblock_id, world_id, draft_id, draft_version, expected_revision_id)
                    ON mechanics_revision.purge TO dmb_app_runtime;
                GRANT EXECUTE ON FUNCTION mechanics_revision.complete_statblock_purge(text, text, uuid, integer, text)
                    TO dmb_app_runtime;
            END IF;
        END $$
    """)


def downgrade():
    op.execute("LOCK TABLE mechanics_revision.purge IN ACCESS EXCLUSIVE MODE")
    if op.get_bind().exec_driver_sql(
        "SELECT EXISTS (SELECT FROM mechanics_revision.purge)"
    ).scalar_one():
        raise RuntimeError("Cannot discard statblock deletion receipts")
    op.execute("DROP FUNCTION mechanics_revision.complete_statblock_purge(text, text, uuid, integer, text)")
    op.execute("DROP TABLE mechanics_revision.purge")
