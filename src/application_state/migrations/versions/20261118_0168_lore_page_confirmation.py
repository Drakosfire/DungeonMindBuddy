"""Retain the atomic receipt for a confirmed lore draft."""

from alembic import op

revision = "20261118_0168"
down_revision = "20261118_0167"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE agent.lore_page_save_review (
            turn_id uuid NOT NULL REFERENCES agent.turn(turn_id) ON DELETE RESTRICT,
            principal_subject text NOT NULL CHECK (length(principal_subject) > 0),
            review_sha256 text NOT NULL CHECK (review_sha256 ~ '^[0-9a-f]{64}$'),
            PRIMARY KEY (turn_id, principal_subject)
        )
    """)
    op.execute("""
        CREATE TABLE agent.lore_page_confirmation (
            turn_id uuid PRIMARY KEY REFERENCES agent.turn(turn_id) ON DELETE RESTRICT,
            review_sha256 text NOT NULL CHECK (review_sha256 ~ '^[0-9a-f]{64}$'),
            principal_subject text NOT NULL CHECK (length(principal_subject) > 0),
            document_id uuid NOT NULL UNIQUE,
            revision_id uuid NOT NULL
        )
    """)


def downgrade():
    raise RuntimeError("Use forward recovery. Downgrade would discard lore save receipts.")
