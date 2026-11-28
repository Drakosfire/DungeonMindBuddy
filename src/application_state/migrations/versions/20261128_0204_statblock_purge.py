"""Retain identifier-only receipts for World statblock deletion."""

from alembic import op

revision = "20261128_0204"
down_revision = "20261128_0203"
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
        DO $$ BEGIN
            IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'dmb_app_runtime') THEN
                GRANT SELECT, INSERT ON mechanics_revision.purge TO dmb_app_runtime;
                GRANT UPDATE (complete) ON mechanics_revision.purge TO dmb_app_runtime;
                GRANT DELETE ON mechanics_revision.operation TO dmb_app_runtime;
            END IF;
        END $$
    """)


def downgrade():
    op.execute("LOCK TABLE mechanics_revision.purge IN ACCESS EXCLUSIVE MODE")
    if op.get_bind().exec_driver_sql(
        "SELECT EXISTS (SELECT FROM mechanics_revision.purge)"
    ).scalar_one():
        raise RuntimeError("Cannot discard statblock deletion receipts")
    op.execute("DROP TABLE mechanics_revision.purge")
