"""Shared surface native Turn records and reader fence; no retained row rewrites."""
from alembic import op
from sqlalchemy import text

revision = '20261101_0103'
down_revision = '20261031_0102'
branch_labels = None
depends_on = None

# Storage shape only. The actual request, source/read, prepared input and output
# owners decide admissibility. No Graph authority is inferred by this predicate.
_NATIVE = """
submitted_intent_fingerprint_v2 IS NOT NULL AND submitted_intent_fingerprint_v1 IS NULL
AND surface_resolution='resolved' AND surface_id IN ('build','plan','play')
AND surface_instance_id IS NOT NULL
AND jsonb_typeof(graph_context_receipt)='object'
AND graph_context_receipt ?& ARRAY['schema','receipt_serializer_version','context_receipt_sha256','provenance_sha256','work_context','source_authority','native_query','assembled_input']
AND graph_context_receipt - ARRAY['schema','receipt_serializer_version','context_receipt_sha256','provenance_sha256','work_context','source_authority','native_query','assembled_input']='{}'::jsonb
AND graph_context_receipt->>'schema'='dmb_surface_native_context_receipt_v1'
AND graph_context_receipt->>'receipt_serializer_version'='canonical-json-utf8-v1'
AND graph_context_receipt->>'context_receipt_sha256' ~ '^[a-f0-9]{64}$'
AND graph_context_receipt->>'provenance_sha256' ~ '^[a-f0-9]{64}$'
AND graph_context_receipt#>>'{work_context,surface_id}'=surface_id
AND graph_context_receipt#>>'{source_authority,managed_world_id}'=world_id
AND jsonb_typeof(graph_context_execution)='object'
AND graph_context_execution ?& ARRAY['schema','context_receipt_sha256','execution_policy_sha256','policy','events']
AND graph_context_execution - ARRAY['schema','context_receipt_sha256','execution_policy_sha256','policy','events']='{}'::jsonb
AND graph_context_execution->>'schema'='dmb_surface_native_execution_v1'
AND graph_context_execution->>'context_receipt_sha256'=graph_context_receipt->>'context_receipt_sha256'
AND graph_context_execution->>'execution_policy_sha256' ~ '^[a-f0-9]{64}$'
AND graph_context_execution#>>'{policy,policy_version}'='surface_native_execution_v1'
AND graph_context_execution#>>'{policy,action,surface_id}'=surface_id
AND graph_context_execution#>>'{policy,action,intent,surface_id}'=surface_id
AND graph_context_execution#>>'{policy,action,intent,surface_instance_id}'=surface_instance_id
AND graph_context_execution#>>'{policy,action,intent,world_id}'=world_id
AND graph_context_execution#>>'{policy,action,intent,message}'=user_text
AND graph_context_execution#>>'{policy,source_authority_sha256}' ~ '^[a-f0-9]{64}$'
AND graph_context_execution#>>'{policy,native_query_sha256}' ~ '^[a-f0-9]{64}$'
AND jsonb_typeof(graph_context_execution->'events')='array'
AND CASE surface_id
 WHEN 'build' THEN play_context_receipt IS NULL AND graph_context_receipt#>>'{work_context,source_basis,world_id}'=world_id
 WHEN 'plan' THEN play_context_receipt IS NULL AND graph_context_receipt#>>'{work_context,plan_basis,world_id}'=world_id
 WHEN 'play' THEN graph_context_receipt#>'{work_context,play_basis}'=play_context_receipt
 ELSE FALSE END
AND status<>'completed' AND completion IS NULL AND assistant_text IS NULL
AND (status NOT IN ('accepted','running') OR completed_at IS NULL)
AND NOT jsonb_path_exists(graph_context_execution,'$.events[*] ? (@.kind == "completion_binding")')
"""


def upgrade():
    for name in ('agent_turn_graph_context_receipt_check',
                 'agent_turn_graph_context_execution_check', 'agent_turn_graph_completion_check'):
        definition = op.get_bind().execute(text(
            "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
            "WHERE conrelid='agent.turn'::regclass AND conname=:name"), {'name': name}).scalar_one()
        if not definition.startswith('CHECK (') or not definition.endswith(')'):
            raise RuntimeError('Owning turn CHECK predicate unavailable')
        previous = definition[len('CHECK ('):-1]
        op.execute(f'ALTER TABLE agent.turn DROP CONSTRAINT "{name}"')
        # Dispatch on either half so a shared record cannot use the historical
        # branch by replacing just its receipt or execution discriminator.
        op.execute(f'''ALTER TABLE agent.turn ADD CONSTRAINT "{name}" CHECK (
          CASE WHEN graph_context_receipt->>'schema'='dmb_surface_native_context_receipt_v1'
                 OR graph_context_execution->>'schema'='dmb_surface_native_execution_v1'
          THEN COALESCE(({_NATIVE}),FALSE) ELSE ({previous}) END)''')


def downgrade():
    raise RuntimeError('Retained shared native Turns require recovery forward')
