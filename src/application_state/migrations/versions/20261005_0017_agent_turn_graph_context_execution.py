"""persist bounded Plan World Graph execution records

Revision ID: 20261005_0017
Revises: 20261004_0016
Create Date: 2026-10-05
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20261005_0017"
down_revision = "20261004_0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "turn",
        sa.Column(
            "graph_context_execution",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        schema="agent",
    )
    op.execute(
        """
        ALTER TABLE agent.turn
        ADD CONSTRAINT agent_turn_graph_context_execution_check CHECK (
            graph_context_execution IS NULL OR (
                graph_context_receipt IS NOT NULL
                AND jsonb_typeof(graph_context_execution) = 'object'
                AND graph_context_execution ?& ARRAY['schema', 'context_receipt_sha256', 'policy', 'events']
                AND graph_context_execution->>'schema' = 'dmb_agent_plan_world_graph_execution_v1'
                AND graph_context_execution->>'context_receipt_sha256' =
                    graph_context_receipt->>'context_receipt_sha256'
                AND jsonb_typeof(graph_context_execution->'policy') = 'object'
                AND graph_context_execution->'policy' ?& ARRAY[
                    'policy_version', 'allowed_graph_operations',
                    'max_provider_attempts', 'max_graph_operations',
                    'max_results_per_operation', 'max_total_provider_input_tokens',
                    'max_total_provider_output_tokens', 'provider_input_accounting',
                    'source_opened'
                ]
                AND CASE
                    WHEN jsonb_typeof(graph_context_execution->'policy'->'allowed_graph_operations') = 'array'
                    THEN jsonb_array_length(graph_context_execution->'policy'->'allowed_graph_operations') BETWEEN 1 AND 32
                    ELSE FALSE
                END
                AND CASE
                    WHEN jsonb_typeof(graph_context_execution->'policy'->'max_provider_attempts') = 'number'
                         AND graph_context_execution->'policy'->>'max_provider_attempts' ~ '^[0-9]+$'
                    THEN (graph_context_execution->'policy'->>'max_provider_attempts')::numeric BETWEEN 1 AND 128
                    ELSE FALSE
                END
                AND CASE
                    WHEN jsonb_typeof(graph_context_execution->'policy'->'max_graph_operations') = 'number'
                         AND graph_context_execution->'policy'->>'max_graph_operations' ~ '^[0-9]+$'
                    THEN (graph_context_execution->'policy'->>'max_graph_operations')::numeric BETWEEN 0 AND 512
                    ELSE FALSE
                END
                AND CASE
                    WHEN jsonb_typeof(graph_context_execution->'policy'->'max_results_per_operation') = 'number'
                         AND graph_context_execution->'policy'->>'max_results_per_operation' ~ '^[0-9]+$'
                    THEN (graph_context_execution->'policy'->>'max_results_per_operation')::numeric BETWEEN 0 AND 4096
                    ELSE FALSE
                END
                AND CASE
                    WHEN jsonb_typeof(graph_context_execution->'policy'->'max_total_provider_input_tokens') = 'number'
                         AND graph_context_execution->'policy'->>'max_total_provider_input_tokens' ~ '^[0-9]+$'
                    THEN (graph_context_execution->'policy'->>'max_total_provider_input_tokens')::numeric >= 1
                    ELSE FALSE
                END
                AND CASE
                    WHEN jsonb_typeof(graph_context_execution->'policy'->'max_total_provider_output_tokens') = 'number'
                         AND graph_context_execution->'policy'->>'max_total_provider_output_tokens' ~ '^[0-9]+$'
                    THEN (graph_context_execution->'policy'->>'max_total_provider_output_tokens')::numeric >= 1
                    ELSE FALSE
                END
                AND jsonb_typeof(graph_context_execution->'policy'->'provider_input_accounting') = 'object'
                AND graph_context_execution->'policy'->'provider_input_accounting' ?& ARRAY['kind', 'estimator']
                AND graph_context_execution->'policy'->'provider_input_accounting'->>'kind' IN (
                    'exact_token_count', 'conservative_upper_bound'
                )
                AND length(graph_context_execution->'policy'->'provider_input_accounting'->>'estimator') BETWEEN 1 AND 128
                AND (
                    graph_context_execution->'policy'->'provider_input_accounting'->>'kind' <> 'conservative_upper_bound'
                    OR graph_context_execution->'policy'->'provider_input_accounting'->>'estimator' = 'utf8_json_bytes_plus_64_per_node_v1'
                )
                AND graph_context_execution->'policy'->>'source_opened' = 'false'
                AND jsonb_typeof(graph_context_execution->'events') = 'array'
                AND jsonb_array_length(graph_context_execution->'events') <= 2048
                AND octet_length(graph_context_execution::text) <= 1048576
            )
        )
        """
    )


def downgrade() -> None:
    has_values = op.get_bind().execute(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM agent.turn WHERE graph_context_execution IS NOT NULL)"
        )
    ).scalar_one()
    if has_values:
        raise RuntimeError("refusing to drop non-null Agent Graph execution records")
    op.execute("ALTER TABLE agent.turn DROP CONSTRAINT agent_turn_graph_context_execution_check")
    op.drop_column("turn", "graph_context_execution", schema="agent")
