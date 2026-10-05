"""persist immutable Plan World Graph context and completion receipts

Revision ID: 20261004_0016
Revises: 20261004_0015
Create Date: 2026-10-05

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20261004_0016"
down_revision = "20261004_0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "turn",
        sa.Column(
            "graph_context_receipt",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        schema="agent",
    )
    op.add_column(
        "turn",
        sa.Column("completion", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        schema="agent",
    )
    op.add_column(
        "turn",
        sa.Column("submitted_intent_fingerprint_v2", sa.Text(), nullable=True),
        schema="agent",
    )
    op.execute(
        """
        ALTER TABLE agent.turn
        ADD CONSTRAINT agent_turn_graph_context_v2_fingerprint_check CHECK (
            submitted_intent_fingerprint_v2 IS NULL
            OR submitted_intent_fingerprint_v2 ~ '^[0-9a-f]{64}$'
        )
        """
    )
    op.execute(
        """
        ALTER TABLE agent.turn
        ADD CONSTRAINT agent_turn_graph_context_receipt_check CHECK (
            graph_context_receipt IS NULL OR (
                submitted_intent_fingerprint_v2 IS NOT NULL
                AND jsonb_typeof(graph_context_receipt) = 'object'
                AND graph_context_receipt ?& ARRAY[
                    'schema', 'receipt_serializer_version', 'context_receipt_sha256',
                    'plan_context_policy', 'plan_basis', 'playable_target',
                    'graph_authority', 'graph_packet', 'assembled_input',
                    'evidence_mode', 'source_opened'
                ]
                AND graph_context_receipt->>'schema' = 'dmb_agent_plan_world_graph_context_receipt_v1'
                AND graph_context_receipt->>'receipt_serializer_version' = 'canonical-json-utf8-v1'
                AND graph_context_receipt->>'context_receipt_sha256' ~ '^[0-9a-f]{64}$'
                AND graph_context_receipt->>'evidence_mode' = 'metadata_only'
                AND graph_context_receipt->>'source_opened' = 'false'
                AND jsonb_typeof(graph_context_receipt->'plan_basis') = 'object'
                AND jsonb_typeof(graph_context_receipt->'graph_authority') = 'object'
                AND jsonb_typeof(graph_context_receipt->'graph_packet') = 'object'
                AND jsonb_typeof(graph_context_receipt->'assembled_input') = 'object'
            )
        )
        """
    )
    op.execute(
        """
        ALTER TABLE agent.turn
        ADD CONSTRAINT agent_turn_graph_completion_check CHECK (
            completion IS NULL OR (
                graph_context_receipt IS NOT NULL
                AND jsonb_typeof(completion) = 'object'
                AND completion ?& ARRAY[
                    'schema', 'context_receipt_sha256', 'answer_basis',
                    'answer_context_status', 'answer_segments', 'citation_map'
                ]
                AND completion->>'schema' = 'dmb_plan_world_graph_completion_v1'
                AND completion->>'context_receipt_sha256' =
                    graph_context_receipt->>'context_receipt_sha256'
                AND completion->>'answer_context_status' IN (
                    'graph_grounded', 'graph_grounded_partial',
                    'plan_only_insufficient_evidence', 'plan_only_graph_unused'
                )
                AND jsonb_typeof(completion->'answer_segments') = 'array'
                AND jsonb_array_length(completion->'answer_segments') > 0
                AND (
                    (completion->>'answer_context_status' IN (
                        'plan_only_insufficient_evidence', 'plan_only_graph_unused'
                    )
                        AND completion->>'answer_basis' = 'committed_plan'
                        AND jsonb_typeof(completion->'citation_map') = 'null'
                        AND NOT jsonb_path_exists(
                            completion->'answer_segments',
                            '$[*] ? (@.kind == "graph_claim")'
                        ))
                    OR
                    (completion->>'answer_context_status' IN (
                        'graph_grounded', 'graph_grounded_partial'
                    )
                        AND completion->>'answer_basis' = 'committed_plan_plus_world_graph'
                        AND jsonb_typeof(completion->'citation_map') = 'object'
                        AND jsonb_typeof(completion->'citation_map'->'entries') = 'array'
                        AND jsonb_array_length(completion->'citation_map'->'entries') > 0
                        AND jsonb_path_exists(
                            completion->'answer_segments',
                            '$[*] ? (@.kind == "graph_claim")'
                        ))
                )
            )
        )
        """
    )


def downgrade() -> None:
    bind = op.get_bind()
    has_values = bind.execute(
        sa.text(
            """
            SELECT EXISTS (
                SELECT 1 FROM agent.turn
                WHERE graph_context_receipt IS NOT NULL
                   OR completion IS NOT NULL
                   OR submitted_intent_fingerprint_v2 IS NOT NULL
            )
            """
        )
    ).scalar_one()
    if has_values:
        raise RuntimeError(
            "refusing to drop non-null Agent Graph context receipts, completions, or v2 intent fingerprints"
        )
    op.execute("ALTER TABLE agent.turn DROP CONSTRAINT agent_turn_graph_completion_check")
    op.execute("ALTER TABLE agent.turn DROP CONSTRAINT agent_turn_graph_context_receipt_check")
    op.execute("ALTER TABLE agent.turn DROP CONSTRAINT agent_turn_graph_context_v2_fingerprint_check")
    op.drop_column("turn", "submitted_intent_fingerprint_v2", schema="agent")
    op.drop_column("turn", "completion", schema="agent")
    op.drop_column("turn", "graph_context_receipt", schema="agent")
