"""Retain a published portrait under its exact saved mechanics revision."""
from alembic import op

revision = "20261116_0159"
down_revision = "20261115_0158"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE world_mechanics.saved_portrait (
            world_id text NOT NULL,
            draft_id uuid NOT NULL,
            revision_id text NOT NULL,
            jpeg_base64 text NOT NULL CHECK (length(jpeg_base64) BETWEEN 1 AND 8388608),
            PRIMARY KEY (world_id, draft_id, revision_id)
        )
    """)
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'dmb_app_runtime') THEN
                GRANT SELECT, INSERT ON world_mechanics.saved_portrait TO dmb_app_runtime;
            END IF;
        END $$
    """)


def downgrade():
    raise RuntimeError("Forward recovery required to retain published statblock portraits")
