"""Admit V3 ordered source-origin extensions; preserve V1/V2 rows."""
from alembic import op

revision = "20261013_0023"
down_revision = "20261013_0022"
branch_labels = None
depends_on = None

_LEGACY_CHECK = """(
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
        ) OR ((graph_context_execution IS NULL) OR (graph_context_receipt IS NOT NULL AND (
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
)))
"""
_V3_CHECK = """
graph_context_execution IS NOT NULL
AND jsonb_typeof(graph_context_execution) = 'object'
AND graph_context_execution ?& ARRAY['schema','context_receipt_sha256','execution_policy_sha256','policy','events']
AND graph_context_execution->>'schema' = 'dmb_agent_plan_world_graph_execution_v3'
AND graph_context_execution->>'context_receipt_sha256' = graph_context_receipt->>'context_receipt_sha256'
AND graph_context_execution->>'context_receipt_sha256' ~ '^[0-9a-f]{64}$'
AND graph_context_execution->>'execution_policy_sha256' ~ '^[0-9a-f]{64}$'
AND jsonb_typeof(graph_context_execution->'policy') = 'object'
AND graph_context_execution->'policy' ?& ARRAY[
 'policy_version','allowed_graph_operations','max_provider_attempts','max_graph_operations',
 'max_results_per_operation','max_total_provider_input_tokens','max_total_provider_output_tokens',
 'provider_input_accounting','source_opened','source_read_scope','max_source_read_chars','max_chars_per_source_read'
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
AND CASE WHEN jsonb_typeof(graph_context_execution->'policy'->'max_source_read_chars')='number' AND graph_context_execution->'policy'->>'max_source_read_chars' ~ '^[0-9]+$' THEN (graph_context_execution->'policy'->>'max_source_read_chars')::numeric BETWEEN 0 AND 96000 ELSE FALSE END
AND CASE WHEN jsonb_typeof(graph_context_execution->'policy'->'max_chars_per_source_read')='number' AND graph_context_execution->'policy'->>'max_chars_per_source_read' ~ '^[0-9]+$' THEN (graph_context_execution->'policy'->>'max_chars_per_source_read')::numeric BETWEEN 1 AND 12000 ELSE FALSE END
"""


_LEGACY_CONSULTATION_CHECK = """
        ALTER TABLE plan_action.action ADD CONSTRAINT plan_action_consultation_check CHECK (
          consultation IS NULL OR (
            jsonb_typeof(consultation) = 'object'
            AND consultation->>'schema_version' = 'dmb_plan_action_consultation_v1'
            AND octet_length(consultation::text) <= 1048576
            AND jsonb_typeof(consultation->'receipt') = 'object'
            AND consultation->'receipt'->>'schema_version' = 'dmb_plan_action_consultation_receipt_v1'
            AND consultation->'receipt'->>'action_id' = action_id::text
            AND consultation->'receipt'->>'request_fingerprint' = request_fingerprint
            AND consultation->'receipt'->'basis'->>'world_id' = world_id
            AND consultation->'receipt'->'basis'->>'document_id' = document_id
            AND consultation->'receipt'->'basis'->>'work_revision_id' = work_revision_id::text
            AND consultation->'receipt'->>'draft_sha256' = draft_sha256
            AND consultation->'receipt'->>'selected_text_sha256' = selected_text_sha256
            AND target_kind = 'replace_selection' AND action_type = 'revise'
            AND (
              (consultation->'receipt'->>'authority_status' = 'unavailable'
                AND consultation->'receipt'->'graph_authority' = 'null'::jsonb
                AND consultation->'receipt'->'graph_packet' = 'null'::jsonb
                AND consultation->'receipt'->'assembled_input' = 'null'::jsonb
                AND consultation->'execution' = 'null'::jsonb
                AND status IN ('pending','failed','indeterminate'))
              OR (consultation->'receipt'->>'authority_status' = 'resolved'
                AND jsonb_typeof(consultation->'receipt'->'graph_authority') = 'object'
                AND jsonb_typeof(consultation->'receipt'->'graph_packet') = 'object'
                AND jsonb_typeof(consultation->'receipt'->'assembled_input') = 'object'
                AND jsonb_typeof(consultation->'execution') = 'object'
                AND consultation->'execution'->>'schema' = 'dmb_agent_plan_world_graph_execution_v2'
                AND consultation->'execution'->>'context_receipt_sha256' =
                    consultation->'receipt'->>'consultation_receipt_sha256'
                AND jsonb_typeof(consultation->'execution'->'events') = 'array'
                AND jsonb_array_length(consultation->'execution'->'events') <= 2048)
            )
            AND (
              (status = 'completed' AND consultation->'result'->>'kind' IN ('clarification','proposal'))
              OR (status = 'failed' AND (consultation->'result' = 'null'::jsonb
                    OR consultation->'result'->>'kind' = 'context_unavailable'))
              OR (status IN ('pending','indeterminate') AND consultation->'result' = 'null'::jsonb)
            )
          ) IS TRUE
        )
    """


def upgrade() -> None:
    op.execute("ALTER TABLE plan_action.action DROP CONSTRAINT plan_action_consultation_check")
    op.execute(_LEGACY_CONSULTATION_CHECK.replace(
        "consultation->'execution'->>'schema' = 'dmb_agent_plan_world_graph_execution_v2'",
        "consultation->'execution'->>'schema' IN ('dmb_agent_plan_world_graph_execution_v2', 'dmb_agent_plan_world_graph_execution_v3')",
    ))
    op.execute("ALTER TABLE agent.turn DROP CONSTRAINT agent_turn_graph_context_execution_check")
    op.execute(f"ALTER TABLE agent.turn ADD CONSTRAINT agent_turn_graph_context_execution_check CHECK (({_LEGACY_CHECK}) OR COALESCE((graph_context_receipt IS NOT NULL AND ({_V3_CHECK})), FALSE))")


def downgrade() -> None:
    if op.get_bind().exec_driver_sql("SELECT EXISTS (SELECT 1 FROM agent.turn WHERE graph_context_execution->>'schema'='dmb_agent_plan_world_graph_execution_v3') OR EXISTS (SELECT 1 FROM plan_action.action WHERE consultation->'execution'->>'schema'='dmb_agent_plan_world_graph_execution_v3')").scalar_one():
        raise RuntimeError("refusing to discard V3 Graph source admission records")
    op.execute("ALTER TABLE agent.turn DROP CONSTRAINT agent_turn_graph_context_execution_check")
    op.execute(f"ALTER TABLE agent.turn ADD CONSTRAINT agent_turn_graph_context_execution_check CHECK ({_LEGACY_CHECK})")
    op.execute("ALTER TABLE plan_action.action DROP CONSTRAINT plan_action_consultation_check")
    op.execute(_LEGACY_CONSULTATION_CHECK)
