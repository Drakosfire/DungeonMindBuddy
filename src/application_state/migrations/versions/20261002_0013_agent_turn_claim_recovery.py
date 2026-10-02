"""add submitted Agent intent fingerprints and bounded turn claims

Revision ID: 20261002_0013
Revises: 20261002_0012
Create Date: 2026-10-02

"""

from __future__ import annotations

from alembic import op

revision = "20261002_0013"
down_revision = "20261002_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE agent.turn
        ADD COLUMN submitted_intent_fingerprint_v1 TEXT NULL,
        ADD COLUMN claim_expires_at TIMESTAMPTZ NULL,
        ADD CONSTRAINT agent_turn_submitted_intent_v1_digest_check
            CHECK (
                submitted_intent_fingerprint_v1 IS NULL
                OR submitted_intent_fingerprint_v1 ~ '^[0-9a-f]{64}$'
            ),
        ADD CONSTRAINT agent_turn_claim_expiry_state_check
            CHECK (status = 'running' OR claim_expires_at IS NULL)
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE agent.turn
        DROP CONSTRAINT agent_turn_claim_expiry_state_check,
        DROP CONSTRAINT agent_turn_submitted_intent_v1_digest_check,
        DROP COLUMN claim_expires_at,
        DROP COLUMN submitted_intent_fingerprint_v1
        """
    )
