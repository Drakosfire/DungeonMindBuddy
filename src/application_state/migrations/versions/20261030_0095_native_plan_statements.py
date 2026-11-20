"""Admit native Plan query/read/producer records without rewriting retained rows."""
from alembic import op
from sqlalchemy import text

revision = '20261030_0095'
down_revision = '20261029_0094'
branch_labels = None
depends_on = None

_NATIVE = """
submitted_intent_fingerprint_v2 IS NOT NULL AND submitted_intent_fingerprint_v1 IS NULL
AND surface_id='plan' AND surface_resolution='resolved' AND surface_instance_id IS NOT NULL
AND play_context_receipt IS NULL
AND jsonb_typeof(graph_context_receipt)='object'
AND graph_context_receipt ?& ARRAY['schema','receipt_serializer_version','context_receipt_sha256','plan_context_policy','plan_basis','playable_target','source_authority','graph_capability','assembled_input','native_query']
AND graph_context_receipt - ARRAY['schema','receipt_serializer_version','context_receipt_sha256','plan_context_policy','plan_basis','playable_target','source_authority','graph_capability','assembled_input','native_query']='{}'::jsonb
AND graph_context_receipt->>'schema'='dmb_plan_native_context_receipt_v1'
AND graph_context_receipt->>'receipt_serializer_version'='canonical-json-utf8-v1'
AND graph_context_receipt->>'context_receipt_sha256' ~ '^[a-f0-9]{64}$'
AND graph_context_receipt#>>'{plan_basis,world_id}'=world_id
AND graph_context_receipt#>>'{plan_context_policy,policy}'='auto_plan_world'
AND graph_context_receipt#>>'{source_authority,managed_world_id}'=world_id
AND (
 (graph_context_receipt#>>'{source_authority,schema_version}'='dmb_native_corpus_authority_v1'
  AND graph_context_receipt#>>'{source_authority,role}'='gm'
  AND graph_context_receipt#>>'{source_authority,scope}'='gm_world_cross_campaign_source_inspection'
  AND length(graph_context_receipt#>>'{source_authority,revision_id}')>0)
 OR (graph_context_receipt#>>'{source_authority,schema}'='dmb_native_corpus_unavailable_v1'
  AND NOT (graph_context_receipt->'source_authority' ? 'revision_id'))
)
AND (graph_context_receipt->'graph_capability'='null'::jsonb OR
 (graph_context_receipt#>>'{graph_capability,schema}'='dmb_agent_plan_world_graph_context_receipt_v1'
  AND graph_context_receipt#>'{graph_capability,plan_basis}'=graph_context_receipt->'plan_basis'))
AND graph_context_receipt#>>'{assembled_input,assembler_version}'='plan_source_jev_initial_v1'
AND jsonb_typeof(graph_context_execution)='object'
AND graph_context_execution ?& ARRAY['schema','context_receipt_sha256','policy','execution_policy_sha256','events']
AND graph_context_execution - ARRAY['schema','context_receipt_sha256','policy','execution_policy_sha256','events']='{}'::jsonb
AND graph_context_execution->>'schema'='dmb_plan_native_execution_v1'
AND graph_context_execution->>'context_receipt_sha256'=graph_context_receipt->>'context_receipt_sha256'
AND graph_context_execution->>'execution_policy_sha256' ~ '^[a-f0-9]{64}$'
AND graph_context_execution#>>'{policy,policy_version}'='plan_native_execution_uncapped_v1'
AND graph_context_execution#>>'{policy,driver_schema}'='dmb_plan_native_jev_retrieval_v1'
AND graph_context_execution#>>'{policy,corpus_source_policy}'='native_admitted_body_sections_v1'
AND graph_context_execution#>>'{policy,source_authority_sha256}' ~ '^[a-f0-9]{64}$'
AND jsonb_typeof(graph_context_execution->'events')='array'
AND NOT jsonb_path_exists(graph_context_execution,'$.events[*] ? (@.kind != "completion_binding" && @.kind != "native_plan_statement_read_authorized_v1" && @.kind != "native_plan_statement_read_observed_v1" && @.kind != "plan_native_writer_authorized_v1" && @.kind != "native_body_provider_included_v1" && @.kind != "native_body_read_authorized_v1" && @.kind != "native_body_read_observed_v1" && @.kind != "native_body_search_authorized_v1" && @.kind != "native_body_search_observed_v1" && @.kind != "plan_jev_provider_authorized_v1" && @.kind != "plan_jev_retrieval_selected_v1" && @.kind != "plan_jev_writer_authorized_v1" && @.kind != "plan_jev_writer_authorized_v2" && @.kind != "plan_requested_work_authorized_v1" && @.kind != "plan_requested_work_authorized_v2" && @.kind != "plan_requested_work_selected_v1" && @.kind != "plan_requested_work_selected_v2" && @.kind != "provider_outcome" && @.kind != "related_recap_context_authorized_v2" && @.kind != "related_recap_context_provider_inclusion_v2" && @.kind != "source_passage_reused_v1" && @.kind != "source_read_authorized_v2" && @.kind != "source_scope_extension_v3" && @.kind != "validated_graph_operation_v3" && @.kind != "validated_related_recap_context_v2" && @.kind != "validated_source_read_v2")')
AND (
 (status<>'completed' AND completion IS NULL AND assistant_text IS NULL)
 OR (status='completed' AND completed_at IS NOT NULL AND assistant_text IS NOT NULL
  AND answer_composition_kind='rules_mixed_v1' AND completion IS NULL
  AND NOT jsonb_path_exists(graph_context_execution,'$.events[*] ? (@.kind == "completion_binding")'))
 OR (status='completed' AND completed_at IS NOT NULL AND assistant_text IS NOT NULL
  AND jsonb_typeof(completion)='object'
  AND completion ?& ARRAY['schema','surface_id','context_receipt_sha256','answer_basis','answer_context_status','answer_segments','citation_map','source_citations','native_source_citations','native_body_citations','native_clause_citations']
  AND completion - ARRAY['schema','surface_id','context_receipt_sha256','answer_basis','answer_context_status','answer_segments','citation_map','source_citations','native_source_citations','native_body_citations','native_clause_citations']='{}'::jsonb
  AND completion->>'schema'='dmb_surface_evidence_completion_v6'
  AND completion->>'surface_id'='plan' AND completion->>'answer_basis'='mixed_evidence'
  AND completion->>'context_receipt_sha256'=graph_context_receipt->>'context_receipt_sha256'
  AND jsonb_typeof(completion->'answer_segments')='array' AND jsonb_array_length(completion->'answer_segments')>0
  AND jsonb_typeof(completion->'source_citations')='array'
  AND completion->'native_source_citations'='[]'::jsonb
  AND jsonb_typeof(completion->'native_body_citations')='array'
  AND jsonb_path_exists(graph_context_execution,'$.events[*] ? (@.kind == "completion_binding")'))
)

AND graph_context_receipt->'graph_capability'='null'::jsonb
AND jsonb_typeof(graph_context_receipt->'native_query')='object'
AND graph_context_receipt#>>'{native_query,schema}' IN ('dmb_native_plan_query_v1','dmb_native_plan_query_unavailable_v1')
AND graph_context_execution#>>'{policy,native_query_sha256}' ~ '^[a-f0-9]{64}$'
AND (completion IS NULL OR jsonb_typeof(completion->'native_clause_citations')='array')
"""

def upgrade():
    bind = op.get_bind()
    for name in (
        "agent_turn_graph_context_receipt_check",
        "agent_turn_graph_context_execution_check",
        "agent_turn_graph_completion_check",
    ):
        definition = bind.execute(text(
            "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
            "WHERE conrelid='agent.turn'::regclass AND conname=:name"), {"name": name}).scalar_one()
        if not definition.startswith("CHECK (") or not definition.endswith(")"):
            raise RuntimeError("Expected owning turn CHECK predicate is unavailable")
        previous = definition[len("CHECK ("):-1]
        op.execute(f'ALTER TABLE agent.turn DROP CONSTRAINT "{name}"')
        op.execute(f"""ALTER TABLE agent.turn ADD CONSTRAINT "{name}" CHECK (
          CASE WHEN graph_context_receipt->>'schema'='dmb_plan_native_context_receipt_v1'
            OR graph_context_execution->>'schema'='dmb_plan_native_execution_v1'
          THEN COALESCE(({_NATIVE}),FALSE) ELSE ({previous}) END)""")


def downgrade():
    raise RuntimeError("Retained native Plan statement records require recovery forward")
