"""Persist exact append intent for portraits on saved conversation variants."""

from alembic import op

revision = "20261122_0190"
down_revision = "20261122_0189"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE agent.conversation_variant_portrait (
            operation_id uuid PRIMARY KEY,
            review_id uuid NOT NULL REFERENCES agent.conversation_variant_review(review_id),
            intent jsonb NOT NULL,
            append_request jsonb NOT NULL,
            receipt jsonb,
            refusal text,
            CHECK (receipt IS NULL OR refusal IS NULL)
        )
    """)
    op.execute("""
        CREATE UNIQUE INDEX conversation_variant_portrait_pending
        ON agent.conversation_variant_portrait (review_id)
        WHERE receipt IS NULL AND refusal IS NULL
    """)


def downgrade():
    raise RuntimeError("Use forward recovery to preserve confirmed portrait appends.")
