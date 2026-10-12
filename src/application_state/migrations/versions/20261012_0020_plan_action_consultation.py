"""Bounded nullable action-owned consultation; legacy actions remain null."""

from alembic import op
import sqlalchemy as sa

revision = "20261012_0020"
down_revision = "20261008_0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE plan_action.action ADD COLUMN consultation JSONB NULL")
    op.execute("""
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
    """)
    op.execute("""
        CREATE UNIQUE INDEX plan_action_consultation_predecessor_unique
        ON plan_action.action ((consultation->'receipt'->'continuation'->>'continuation_of_action_id'))
        WHERE consultation->'receipt'->'continuation'->>'continuation_of_action_id' IS NOT NULL
    """)


def downgrade() -> None:
    if op.get_bind().execute(sa.text(
        "SELECT EXISTS (SELECT 1 FROM plan_action.action WHERE consultation IS NOT NULL)"
    )).scalar_one():
        raise RuntimeError("refusing to downgrade while action consultation receipts exist")
    op.execute("DROP INDEX plan_action.plan_action_consultation_predecessor_unique")
    op.execute("ALTER TABLE plan_action.action DROP CONSTRAINT plan_action_consultation_check")
    op.execute("ALTER TABLE plan_action.action DROP COLUMN consultation")
