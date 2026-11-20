"""admit strict V2 Graph source-read execution receipts

Revision ID: 20261007_0018
Revises: 20261005_0017
Create Date: 2026-10-07
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20261007_0018"
down_revision = "20261005_0017"
branch_labels = None
depends_on = None

_V1_EXECUTION_CHECK = "\n            graph_context_execution IS NULL OR (\n                graph_context_receipt IS NOT NULL\n                AND jsonb_typeof(graph_context_execution) = 'object'\n                AND graph_context_execution ?& ARRAY['schema', 'context_receipt_sha256', 'policy', 'events']\n                AND graph_context_execution->>'schema' = 'dmb_agent_plan_world_graph_execution_v1'\n                AND graph_context_execution->>'context_receipt_sha256' =\n                    graph_context_receipt->>'context_receipt_sha256'\n                AND jsonb_typeof(graph_context_execution->'policy') = 'object'\n                AND graph_context_execution->'policy' ?& ARRAY[\n                    'policy_version', 'allowed_graph_operations',\n                    'max_provider_attempts', 'max_graph_operations',\n                    'max_results_per_operation', 'max_total_provider_input_tokens',\n                    'max_total_provider_output_tokens', 'provider_input_accounting',\n                    'source_opened'\n                ]\n                AND CASE\n                    WHEN jsonb_typeof(graph_context_execution->'policy'->'allowed_graph_operations') = 'array'\n                    THEN jsonb_array_length(graph_context_execution->'policy'->'allowed_graph_operations') BETWEEN 1 AND 32\n                    ELSE FALSE\n                END\n                AND CASE\n                    WHEN jsonb_typeof(graph_context_execution->'policy'->'max_provider_attempts') = 'number'\n                         AND graph_context_execution->'policy'->>'max_provider_attempts' ~ '^[0-9]+$'\n                    THEN (graph_context_execution->'policy'->>'max_provider_attempts')::numeric BETWEEN 1 AND 128\n                    ELSE FALSE\n                END\n                AND CASE\n                    WHEN jsonb_typeof(graph_context_execution->'policy'->'max_graph_operations') = 'number'\n                         AND graph_context_execution->'policy'->>'max_graph_operations' ~ '^[0-9]+$'\n                    THEN (graph_context_execution->'policy'->>'max_graph_operations')::numeric BETWEEN 0 AND 512\n                    ELSE FALSE\n                END\n                AND CASE\n                    WHEN jsonb_typeof(graph_context_execution->'policy'->'max_results_per_operation') = 'number'\n                         AND graph_context_execution->'policy'->>'max_results_per_operation' ~ '^[0-9]+$'\n                    THEN (graph_context_execution->'policy'->>'max_results_per_operation')::numeric BETWEEN 0 AND 4096\n                    ELSE FALSE\n                END\n                AND CASE\n                    WHEN jsonb_typeof(graph_context_execution->'policy'->'max_total_provider_input_tokens') = 'number'\n                         AND graph_context_execution->'policy'->>'max_total_provider_input_tokens' ~ '^[0-9]+$'\n                    THEN (graph_context_execution->'policy'->>'max_total_provider_input_tokens')::numeric >= 1\n                    ELSE FALSE\n                END\n                AND CASE\n                    WHEN jsonb_typeof(graph_context_execution->'policy'->'max_total_provider_output_tokens') = 'number'\n                         AND graph_context_execution->'policy'->>'max_total_provider_output_tokens' ~ '^[0-9]+$'\n                    THEN (graph_context_execution->'policy'->>'max_total_provider_output_tokens')::numeric >= 1\n                    ELSE FALSE\n                END\n                AND jsonb_typeof(graph_context_execution->'policy'->'provider_input_accounting') = 'object'\n                AND graph_context_execution->'policy'->'provider_input_accounting' ?& ARRAY['kind', 'estimator']\n                AND graph_context_execution->'policy'->'provider_input_accounting'->>'kind' IN (\n                    'exact_token_count', 'conservative_upper_bound'\n                )\n                AND length(graph_context_execution->'policy'->'provider_input_accounting'->>'estimator') BETWEEN 1 AND 128\n                AND (\n                    graph_context_execution->'policy'->'provider_input_accounting'->>'kind' <> 'conservative_upper_bound'\n                    OR graph_context_execution->'policy'->'provider_input_accounting'->>'estimator' = 'utf8_json_bytes_plus_64_per_node_v1'\n                )\n                AND graph_context_execution->'policy'->>'source_opened' = 'false'\n                AND jsonb_typeof(graph_context_execution->'events') = 'array'\n                AND jsonb_array_length(graph_context_execution->'events') <= 2048\n                AND octet_length(graph_context_execution::text) <= 1048576\n            )\n        "
_V1_COMPLETION_CHECK = "\n            completion IS NULL OR (\n                graph_context_receipt IS NOT NULL\n                AND jsonb_typeof(completion) = 'object'\n                AND completion ?& ARRAY[\n                    'schema', 'context_receipt_sha256', 'answer_basis',\n                    'answer_context_status', 'answer_segments', 'citation_map'\n                ]\n                AND completion->>'schema' = 'dmb_plan_world_graph_completion_v1'\n                AND completion->>'context_receipt_sha256' =\n                    graph_context_receipt->>'context_receipt_sha256'\n                AND completion->>'answer_context_status' IN (\n                    'graph_grounded', 'graph_grounded_partial',\n                    'plan_only_insufficient_evidence', 'plan_only_graph_unused'\n                )\n                AND jsonb_typeof(completion->'answer_segments') = 'array'\n                AND jsonb_array_length(completion->'answer_segments') > 0\n                AND (\n                    (completion->>'answer_context_status' IN (\n                        'plan_only_insufficient_evidence', 'plan_only_graph_unused'\n                    )\n                        AND completion->>'answer_basis' = 'committed_plan'\n                        AND jsonb_typeof(completion->'citation_map') = 'null'\n                        AND NOT jsonb_path_exists(\n                            completion->'answer_segments',\n                            '$[*] ? (@.kind == \"graph_claim\")'\n                        ))\n                    OR\n                    (completion->>'answer_context_status' IN (\n                        'graph_grounded', 'graph_grounded_partial'\n                    )\n                        AND completion->>'answer_basis' = 'committed_plan_plus_world_graph'\n                        AND jsonb_typeof(completion->'citation_map') = 'object'\n                        AND jsonb_typeof(completion->'citation_map'->'entries') = 'array'\n                        AND jsonb_array_length(completion->'citation_map'->'entries') > 0\n                        AND jsonb_path_exists(\n                            completion->'answer_segments',\n                            '$[*] ? (@.kind == \"graph_claim\")'\n                        ))\n                )\n            )\n        "

_V2_EXECUTION_CHECK = """
graph_context_execution IS NOT NULL
AND jsonb_typeof(graph_context_execution) = 'object'
AND graph_context_execution ?& ARRAY['schema','context_receipt_sha256','execution_policy_sha256','policy','events']
AND graph_context_execution->>'schema' = 'dmb_agent_plan_world_graph_execution_v2'
AND graph_context_execution->>'context_receipt_sha256' = graph_context_receipt->>'context_receipt_sha256'
AND graph_context_execution->>'context_receipt_sha256' ~ '^[0-9a-f]{64}$'
AND graph_context_execution->>'execution_policy_sha256' ~ '^[0-9a-f]{64}$'
AND jsonb_typeof(graph_context_execution->'policy') = 'object'
AND graph_context_execution->'policy' ?& ARRAY[
 'policy_version','allowed_graph_operations','max_provider_attempts','max_graph_operations',
 'max_results_per_operation','max_total_provider_input_tokens','max_total_provider_output_tokens',
 'provider_input_accounting','source_opened','source_read_scope','max_source_read_calls',
 'max_source_read_anchors','max_source_read_chars','max_chars_per_source_read'
]
AND graph_context_execution->'policy'->>'source_opened' = 'false'
AND CASE WHEN jsonb_typeof(graph_context_execution->'policy'->'allowed_graph_operations')='array' THEN jsonb_array_length(graph_context_execution->'policy'->'allowed_graph_operations') BETWEEN 1 AND 32 ELSE FALSE END
AND CASE WHEN jsonb_typeof(graph_context_execution->'policy'->'max_provider_attempts')='number' AND graph_context_execution->'policy'->>'max_provider_attempts' ~ '^[0-9]+$' THEN (graph_context_execution->'policy'->>'max_provider_attempts')::numeric BETWEEN 1 AND 128 ELSE FALSE END
AND CASE WHEN jsonb_typeof(graph_context_execution->'policy'->'max_graph_operations')='number' AND graph_context_execution->'policy'->>'max_graph_operations' ~ '^[0-9]+$' THEN (graph_context_execution->'policy'->>'max_graph_operations')::numeric BETWEEN 0 AND 512 ELSE FALSE END
AND CASE WHEN jsonb_typeof(graph_context_execution->'policy'->'max_results_per_operation')='number' AND graph_context_execution->'policy'->>'max_results_per_operation' ~ '^[0-9]+$' THEN (graph_context_execution->'policy'->>'max_results_per_operation')::numeric BETWEEN 0 AND 4096 ELSE FALSE END
AND CASE WHEN jsonb_typeof(graph_context_execution->'policy'->'max_total_provider_input_tokens')='number' AND graph_context_execution->'policy'->>'max_total_provider_input_tokens' ~ '^[0-9]+$' THEN (graph_context_execution->'policy'->>'max_total_provider_input_tokens')::numeric >= 1 ELSE FALSE END
AND CASE WHEN jsonb_typeof(graph_context_execution->'policy'->'max_total_provider_output_tokens')='number' AND graph_context_execution->'policy'->>'max_total_provider_output_tokens' ~ '^[0-9]+$' THEN (graph_context_execution->'policy'->>'max_total_provider_output_tokens')::numeric >= 1 ELSE FALSE END
AND jsonb_typeof(graph_context_execution->'policy'->'provider_input_accounting')='object'
AND graph_context_execution->'policy'->'provider_input_accounting' ?& ARRAY['kind','estimator']
AND graph_context_execution->'policy'->'provider_input_accounting'->>'kind' IN ('exact_token_count','conservative_upper_bound')
AND length(graph_context_execution->'policy'->'provider_input_accounting'->>'estimator') BETWEEN 1 AND 128
AND (graph_context_execution->'policy'->'provider_input_accounting'->>'kind' <> 'conservative_upper_bound' OR graph_context_execution->'policy'->'provider_input_accounting'->>'estimator' = 'utf8_json_bytes_plus_64_per_node_v1')
AND jsonb_typeof(graph_context_execution->'policy'->'allowed_graph_operations')='array'
AND jsonb_typeof(graph_context_execution->'policy'->'source_read_scope') = 'object'
AND graph_context_execution->'policy'->'source_read_scope' ?& ARRAY[
 'schema','retrieval_session_id','world_id','campaign_id','graph_revision','admitted_anchors'
]
AND graph_context_execution->'policy'->'source_read_scope'->>'schema' = 'dmb_graph_source_read_scope_v2'
AND jsonb_typeof(graph_context_execution->'policy'->'source_read_scope'->'admitted_anchors') = 'array'
AND jsonb_array_length(graph_context_execution->'policy'->'source_read_scope'->'admitted_anchors') <= 512
AND jsonb_typeof(graph_context_execution->'events') = 'array'
AND jsonb_array_length(graph_context_execution->'events') <= 2048
AND octet_length(graph_context_execution::text) <= 1048576
AND CASE WHEN jsonb_typeof(graph_context_execution->'policy'->'max_source_read_calls')='number' AND graph_context_execution->'policy'->>'max_source_read_calls' ~ '^[0-9]+$' THEN (graph_context_execution->'policy'->>'max_source_read_calls')::numeric BETWEEN 0 AND 8 ELSE FALSE END
AND CASE WHEN jsonb_typeof(graph_context_execution->'policy'->'max_source_read_anchors')='number' AND graph_context_execution->'policy'->>'max_source_read_anchors' ~ '^[0-9]+$' THEN (graph_context_execution->'policy'->>'max_source_read_anchors')::numeric BETWEEN 0 AND 8 ELSE FALSE END
AND CASE WHEN jsonb_typeof(graph_context_execution->'policy'->'max_source_read_chars')='number' AND graph_context_execution->'policy'->>'max_source_read_chars' ~ '^[0-9]+$' THEN (graph_context_execution->'policy'->>'max_source_read_chars')::numeric BETWEEN 0 AND 96000 ELSE FALSE END
AND CASE WHEN jsonb_typeof(graph_context_execution->'policy'->'max_chars_per_source_read')='number' AND graph_context_execution->'policy'->>'max_chars_per_source_read' ~ '^[0-9]+$' THEN (graph_context_execution->'policy'->>'max_chars_per_source_read')::numeric BETWEEN 1 AND 12000 ELSE FALSE END
"""

_V2_COMPLETION_CHECK = """
completion IS NOT NULL
AND graph_context_receipt IS NOT NULL
AND jsonb_typeof(completion) = 'object'
AND completion ?& ARRAY['schema','context_receipt_sha256','answer_basis','answer_context_status','answer_segments','citation_map']
AND completion->>'schema' = 'dmb_plan_world_graph_completion_v2'
AND completion->>'context_receipt_sha256' = graph_context_receipt->>'context_receipt_sha256'
AND completion->>'context_receipt_sha256' ~ '^[0-9a-f]{64}$'
AND completion->>'answer_context_status' IN ('graph_grounded','graph_grounded_partial','plan_only_insufficient_evidence','plan_only_graph_unused')
AND jsonb_typeof(completion->'answer_segments') = 'array'
AND jsonb_array_length(completion->'answer_segments') BETWEEN 1 AND 128
AND octet_length(completion::text) <= 1048576
AND (
 (completion->>'answer_context_status' IN ('plan_only_insufficient_evidence','plan_only_graph_unused')
  AND completion->>'answer_basis'='committed_plan'
  AND jsonb_typeof(completion->'citation_map')='null'
  AND NOT jsonb_path_exists(completion->'answer_segments','$[*] ? (@.kind == "graph_claim")'))
 OR
 (completion->>'answer_context_status' IN ('graph_grounded','graph_grounded_partial')
  AND completion->>'answer_basis'='committed_plan_plus_world_graph'
  AND jsonb_typeof(completion->'citation_map')='object'
  AND completion->'citation_map'->>'schema'='dmb_graph_citation_map_v2'
  AND completion->'citation_map'->>'context_receipt_sha256'=completion->>'context_receipt_sha256'
  AND jsonb_typeof(completion->'citation_map'->'entries')='array'
  AND jsonb_array_length(completion->'citation_map'->'entries')>0
  AND jsonb_path_exists(completion->'answer_segments','$[*] ? (@.kind == "graph_claim")'))
)
"""


def upgrade() -> None:
    op.execute(
        "ALTER TABLE agent.turn DROP CONSTRAINT agent_turn_graph_context_execution_check"
    )
    op.execute(
        f"ALTER TABLE agent.turn ADD CONSTRAINT agent_turn_graph_context_execution_check CHECK (({_V1_EXECUTION_CHECK}) OR ((graph_context_execution IS NULL) OR (graph_context_receipt IS NOT NULL AND ({_V2_EXECUTION_CHECK}))))"
    )
    op.execute(
        "ALTER TABLE agent.turn DROP CONSTRAINT agent_turn_graph_completion_check"
    )
    op.execute(
        f"ALTER TABLE agent.turn ADD CONSTRAINT agent_turn_graph_completion_check CHECK (({_V1_COMPLETION_CHECK}) OR ((completion IS NULL) OR (graph_context_receipt IS NOT NULL AND ({_V2_COMPLETION_CHECK}))))"
    )


def downgrade() -> None:
    has_v2 = (
        op.get_bind()
        .execute(
            sa.text("""
        SELECT EXISTS (SELECT 1 FROM agent.turn
         WHERE graph_context_execution->>'schema'='dmb_agent_plan_world_graph_execution_v2'
            OR completion->>'schema'='dmb_plan_world_graph_completion_v2')
    """)
        )
        .scalar_one()
    )
    if has_v2:
        raise RuntimeError(
            "refusing to downgrade while V2 Graph execution or completion records exist"
        )
    op.execute(
        "ALTER TABLE agent.turn DROP CONSTRAINT agent_turn_graph_context_execution_check"
    )
    op.execute(
        f"ALTER TABLE agent.turn ADD CONSTRAINT agent_turn_graph_context_execution_check CHECK ({_V1_EXECUTION_CHECK})"
    )
    op.execute(
        "ALTER TABLE agent.turn DROP CONSTRAINT agent_turn_graph_completion_check"
    )
    op.execute(
        f"ALTER TABLE agent.turn ADD CONSTRAINT agent_turn_graph_completion_check CHECK ({_V1_COMPLETION_CHECK})"
    )
