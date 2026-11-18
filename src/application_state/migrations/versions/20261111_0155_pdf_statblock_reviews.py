"""Persist extracted statblock review drafts and their exact PDF regions."""
from alembic import op

revision = "20261111_0155"
down_revision = "20261111_0154"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE public.pdf_statblock_review (
            world_id text NOT NULL,
            review_id uuid NOT NULL,
            revision integer NOT NULL CHECK (revision > 0),
            payload jsonb NOT NULL,
            PRIMARY KEY (world_id, review_id)
        )
    """)


def downgrade():
    raise RuntimeError("Use forward recovery to preserve PDF statblock review drafts.")
