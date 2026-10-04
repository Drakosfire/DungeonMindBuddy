"""add nullable typed Playable target receipts to Plan actions

Revision ID: 20261004_0015
Revises: 20261003_0014
Create Date: 2026-10-04

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20261004_0015"
down_revision = "20261003_0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "action",
        sa.Column("playable_target_receipt", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        schema="plan_action",
    )
    op.execute(
        "ALTER TABLE plan_action.action DROP CONSTRAINT action_target_kind_check"
    )
    op.execute(
        "ALTER TABLE plan_action.action ADD CONSTRAINT action_target_kind_check "
        "CHECK (target_kind IN ('replace_selection', 'insert_at_caret', 'replace_playable_body'))"
    )
    op.execute(
        "ALTER TABLE plan_action.action DROP CONSTRAINT plan_action_selection_witness_check"
    )
    op.execute(
        """
        ALTER TABLE plan_action.action
        ADD CONSTRAINT plan_action_playable_target_receipt_check CHECK (
            playable_target_receipt IS NULL OR (
                jsonb_typeof(playable_target_receipt) = 'object'
                AND playable_target_receipt ?& ARRAY[
                    'schema_version', 'kind', 'id', 'marker_grammar_version',
                    'body_scope', 'range_semantics_version',
                    'body_serialization_version', 'target_body_sha256'
                ]
                AND playable_target_receipt - ARRAY[
                    'schema_version', 'kind', 'id', 'marker_grammar_version',
                    'body_scope', 'range_semantics_version',
                    'body_serialization_version', 'target_body_sha256'
                ] = '{}'::jsonb
                AND jsonb_typeof(playable_target_receipt->'schema_version') = 'string'
                AND jsonb_typeof(playable_target_receipt->'kind') = 'string'
                AND jsonb_typeof(playable_target_receipt->'id') = 'string'
                AND jsonb_typeof(playable_target_receipt->'marker_grammar_version') = 'string'
                AND jsonb_typeof(playable_target_receipt->'body_scope') = 'string'
                AND jsonb_typeof(playable_target_receipt->'range_semantics_version') = 'string'
                AND jsonb_typeof(playable_target_receipt->'body_serialization_version') = 'string'
                AND jsonb_typeof(playable_target_receipt->'target_body_sha256') = 'string'
                AND playable_target_receipt->>'schema_version' = 'dmb_plan_playable_target_receipt_v1'
                AND playable_target_receipt->>'kind' IN ('scene', 'beat', 'choice', 'option')
                AND playable_target_receipt->>'id' ~ '^(scene|beat|choice|option):[a-z0-9][a-z0-9._-]{0,127}$'
                AND split_part(playable_target_receipt->>'id', ':', 1) = playable_target_receipt->>'kind'
                AND playable_target_receipt->>'marker_grammar_version' IN ('v1', 'v2')
                AND playable_target_receipt->>'body_scope' IN ('heading_body', 'beat_direct_body', 'option_item_content')
                AND playable_target_receipt->>'range_semantics_version' = 'plan-playable-ranges-v1'
                AND playable_target_receipt->>'body_serialization_version' = 'plan-playable-body-markdown-v1'
                AND playable_target_receipt->>'target_body_sha256' ~ '^[0-9a-f]{64}$'
                AND (
                    (playable_target_receipt->>'marker_grammar_version' = 'v1'
                        AND playable_target_receipt->>'body_scope' = 'heading_body')
                    OR (playable_target_receipt->>'marker_grammar_version' = 'v2'
                        AND playable_target_receipt->>'kind' IN ('scene', 'choice')
                        AND playable_target_receipt->>'body_scope' = 'heading_body')
                    OR (playable_target_receipt->>'marker_grammar_version' = 'v2'
                        AND playable_target_receipt->>'kind' = 'beat'
                        AND playable_target_receipt->>'body_scope' = 'beat_direct_body')
                    OR (playable_target_receipt->>'marker_grammar_version' = 'v2'
                        AND playable_target_receipt->>'kind' = 'option'
                        AND playable_target_receipt->>'body_scope' = 'option_item_content')
                )
            )
        )
        """
    )
    op.execute(
        """
        ALTER TABLE plan_action.action
        ADD CONSTRAINT plan_action_selection_witness_check CHECK (
            (target_kind = 'replace_selection' AND selected_text_sha256 IS NOT NULL
                AND playable_target_receipt IS NULL)
            OR (target_kind = 'insert_at_caret' AND selected_text_sha256 IS NULL
                AND playable_target_receipt IS NULL)
            OR (target_kind = 'replace_playable_body' AND selected_text_sha256 IS NULL
                AND playable_target_receipt IS NOT NULL)
        )
        """
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE plan_action.action DROP CONSTRAINT plan_action_selection_witness_check"
    )
    op.execute(
        "ALTER TABLE plan_action.action DROP CONSTRAINT plan_action_playable_target_receipt_check"
    )
    op.execute(
        "ALTER TABLE plan_action.action DROP CONSTRAINT action_target_kind_check"
    )
    op.execute(
        "ALTER TABLE plan_action.action ADD CONSTRAINT action_target_kind_check "
        "CHECK (target_kind IN ('replace_selection', 'insert_at_caret'))"
    )
    op.execute(
        """
        ALTER TABLE plan_action.action
        ADD CONSTRAINT plan_action_selection_witness_check CHECK (
            (target_kind = 'replace_selection' AND selected_text_sha256 IS NOT NULL)
            OR (target_kind = 'insert_at_caret' AND selected_text_sha256 IS NULL)
        )
        """
    )
    op.drop_column("action", "playable_target_receipt", schema="plan_action")
