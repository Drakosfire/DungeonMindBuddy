"""Admit private Action-owned prompt references without rewriting historical rows."""
from alembic import op

revision = "20261018_0033"
down_revision = "20261017_0032"
branch_labels = None
depends_on = None

_PREVIOUS_CHECK = """
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
                AND consultation->'execution'->>'schema' IN ('dmb_agent_plan_world_graph_execution_v2', 'dmb_agent_plan_world_graph_execution_v3')
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
_CAPTURE_CHECK = """
        ALTER TABLE plan_action.action ADD CONSTRAINT plan_action_consultation_check CHECK (
          consultation IS NULL OR (
            jsonb_typeof(consultation) = 'object'
            AND consultation->>'schema_version' IN ('dmb_plan_action_consultation_v1', 'dmb_plan_action_consultation_v2')
            AND CASE WHEN consultation->>'schema_version' = 'dmb_plan_action_consultation_v2'
                THEN CASE WHEN jsonb_typeof(consultation->'prompt_references') = 'array'
                    THEN jsonb_array_length(consultation->'prompt_references') <= 512
                    ELSE FALSE END
                ELSE TRUE END
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
                AND consultation->'execution'->>'schema' IN ('dmb_agent_plan_world_graph_execution_v2', 'dmb_agent_plan_world_graph_execution_v3')
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
    op.execute(_CAPTURE_CHECK)


def downgrade() -> None:
    # Exclude writers before checking: no concurrent V2 insert can race the guard.
    op.execute("LOCK TABLE plan_action.action IN ACCESS EXCLUSIVE MODE")
    if op.get_bind().exec_driver_sql(
        "SELECT EXISTS (SELECT 1 FROM plan_action.action WHERE "
        "consultation->>'schema_version' = 'dmb_plan_action_consultation_v2')"
    ).scalar_one():
        raise RuntimeError("refusing to discard Action prompt capture records")
    op.execute("ALTER TABLE plan_action.action DROP CONSTRAINT plan_action_consultation_check")
    op.execute(_PREVIOUS_CHECK)
