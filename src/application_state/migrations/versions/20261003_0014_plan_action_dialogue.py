"""add Plan-owned durable action reservations and safe projections

Revision ID: 20261003_0014
Revises: 20261002_0013
Create Date: 2026-10-03

"""

from __future__ import annotations

from alembic import op

revision = "20261003_0014"
down_revision = "20261002_0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS plan_action")
    op.execute(
        """
        CREATE TABLE plan_action.action (
            action_id UUID PRIMARY KEY,
            idempotency_key UUID NOT NULL,
            request_fingerprint TEXT NOT NULL CHECK (request_fingerprint ~ '^[0-9a-f]{64}$'),
            action_type TEXT NOT NULL CHECK (action_type IN ('compose', 'revise')),
            world_id TEXT NOT NULL CHECK (btrim(world_id) <> ''),
            document_id TEXT NOT NULL CHECK (btrim(document_id) <> ''),
            object_revision BIGINT NOT NULL CHECK (object_revision > 0),
            work_revision_id UUID NOT NULL,
            revision_n BIGINT NOT NULL CHECK (revision_n > 0),
            content_sha256 TEXT NOT NULL CHECK (content_sha256 ~ '^[0-9a-f]{64}$'),
            draft_matches_basis BOOLEAN NOT NULL,
            draft_sha256 TEXT NOT NULL CHECK (draft_sha256 ~ '^[0-9a-f]{64}$'),
            target_kind TEXT NOT NULL CHECK (target_kind IN ('replace_selection', 'insert_at_caret')),
            selected_text_sha256 TEXT NULL CHECK (
                selected_text_sha256 IS NULL OR selected_text_sha256 ~ '^[0-9a-f]{64}$'
            ),
            instruction TEXT NOT NULL CHECK (btrim(instruction) <> ''),
            status TEXT NOT NULL CHECK (status IN ('pending', 'completed', 'failed', 'indeterminate')),
            assistant_summary TEXT NULL,
            failure_code TEXT NULL,
            dispatch_token UUID NULL,
            fence BIGINT NOT NULL CHECK (fence > 0),
            action_sequence BIGSERIAL NOT NULL UNIQUE,
            accepted_at TIMESTAMPTZ NOT NULL,
            completed_at TIMESTAMPTZ NULL,
            lease_expires_at TIMESTAMPTZ NULL,
            updated_at TIMESTAMPTZ NOT NULL,
            CONSTRAINT plan_action_world_idempotency_key_unique
                UNIQUE (world_id, idempotency_key),
            CONSTRAINT plan_action_state_fields_check CHECK (
                (status = 'pending' AND dispatch_token IS NOT NULL AND lease_expires_at IS NOT NULL
                    AND assistant_summary IS NULL AND failure_code IS NULL AND completed_at IS NULL)
                OR (status = 'completed' AND dispatch_token IS NULL AND lease_expires_at IS NULL
                    AND assistant_summary IS NOT NULL AND btrim(assistant_summary) <> ''
                    AND failure_code IS NULL AND completed_at IS NOT NULL)
                OR (status = 'failed' AND dispatch_token IS NULL AND lease_expires_at IS NULL
                    AND assistant_summary IS NULL AND failure_code IS NOT NULL AND completed_at IS NULL)
                OR (status = 'indeterminate' AND dispatch_token IS NULL AND lease_expires_at IS NULL
                    AND assistant_summary IS NULL AND failure_code IS NOT NULL AND completed_at IS NULL)
            ),
            CONSTRAINT plan_action_selection_witness_check CHECK (
                (target_kind = 'replace_selection' AND selected_text_sha256 IS NOT NULL)
                OR (target_kind = 'insert_at_caret' AND selected_text_sha256 IS NULL)
            )
        )
        """
    )
    op.execute(
        """
        CREATE INDEX plan_action_exact_basis_order
        ON plan_action.action (
            world_id, document_id, object_revision, work_revision_id,
            revision_n, content_sha256, accepted_at, action_sequence
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE plan_action.action")
    op.execute("DROP SCHEMA plan_action")
