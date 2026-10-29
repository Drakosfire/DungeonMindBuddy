"""Admit native source-only turn shapes; fence incompatible historical readers."""

from alembic import op
from sqlalchemy import text

revision = "20261029_0091"
down_revision = "20261029_0090"
branch_labels = None
depends_on = None

_NATIVE = """
submitted_intent_fingerprint_v1 IS NOT NULL AND submitted_intent_fingerprint_v2 IS NULL
AND surface_id='plan' AND surface_resolution='resolved'
AND jsonb_typeof(graph_context_receipt)='object'
AND graph_context_receipt ?& ARRAY['schema','selection','frame','user_text','provenance_sha256','context_receipt_sha256']
AND graph_context_receipt - ARRAY['schema','selection','frame','user_text','provenance_sha256','context_receipt_sha256']='{}'::jsonb
AND graph_context_receipt->>'user_text'=user_text
AND graph_context_receipt->>'context_receipt_sha256' ~ '^[a-f0-9]{64}$'
AND graph_context_receipt->>'provenance_sha256' ~ '^[a-f0-9]{64}$'
AND graph_context_receipt->'selection'->>'schema'='dmb_native_statement_selection_v1'
AND graph_context_receipt->'selection'->>'managedWorldId'=world_id
AND graph_context_receipt->'frame'->>'schema'='dmb_native_statement_frame_v1'
AND graph_context_receipt->'frame'->>'authority'='native_vnext'
AND graph_context_receipt->'frame'->>'managed_world_id'=world_id
AND graph_context_receipt->'frame'->>'universal_absence_claimed'='false'
AND jsonb_typeof(graph_context_receipt->'frame'->'supports')='array'
AND jsonb_typeof(graph_context_execution)='object'
AND graph_context_execution ?& ARRAY['schema','context_receipt_sha256','policy','execution_policy_sha256','events']
AND graph_context_execution - ARRAY['schema','context_receipt_sha256','policy','execution_policy_sha256','events']='{}'::jsonb
AND graph_context_execution->>'schema'='dmb_native_statement_execution_v1'
AND graph_context_execution->>'context_receipt_sha256'=graph_context_receipt->>'context_receipt_sha256'
AND graph_context_execution->>'execution_policy_sha256' ~ '^[a-f0-9]{64}$'
AND graph_context_execution->'policy'->>'policy_version'='native_statement_writer_v1'
AND graph_context_execution->'policy'->>'requires_native_output_proof'='true'
AND jsonb_typeof(graph_context_execution->'events')='array'
AND NOT jsonb_path_exists(graph_context_execution,'$.events[*] ? (@.kind != "provider_attempt_authorized" && @.kind != "native_statement_input_v1" && @.kind != "provider_outcome" && @.kind != "native_statement_output_captured_v1" && @.kind != "completion_binding")')
AND (
 (status <> 'completed' AND completion IS NULL)
 OR (status='completed' AND jsonb_typeof(completion)='object'
 AND completion ?& ARRAY['schema','surface_id','context_receipt_sha256','answer_context_status','answer_segments','native_clause_citations']
 AND completion - ARRAY['schema','surface_id','context_receipt_sha256','answer_context_status','answer_segments','native_clause_citations']='{}'::jsonb
 AND completion->>'schema'='dmb_native_statement_completion_v1'
 AND completion->>'surface_id'='plan'
 AND completion->>'context_receipt_sha256'=graph_context_receipt->>'context_receipt_sha256'
 AND completion->>'answer_context_status' IN ('source_attributed','source_attributed_partial','insufficient_evidence')
 AND jsonb_typeof(completion->'answer_segments')='array'
 AND CASE WHEN jsonb_typeof(completion->'answer_segments')='array' THEN jsonb_array_length(completion->'answer_segments')>0 ELSE FALSE END
 AND jsonb_typeof(completion->'native_clause_citations')='array'
 AND NOT jsonb_path_exists(completion,'$.answer_segments[*] ? (@.kind != "source_report" && @.kind != "proposal" && @.kind != "limitation")')
 AND jsonb_path_exists(graph_context_execution,'$.events[*] ? (@.kind == "native_statement_input_v1")')
 AND jsonb_path_exists(graph_context_execution,'$.events[*] ? (@.kind == "native_statement_output_captured_v1")')
 AND jsonb_path_exists(graph_context_execution,'$.events[*] ? (@.kind == "completion_binding")')))
"""


def upgrade():
    bind = op.get_bind()
    # Preserve each historical predicate exactly; native rows choose one explicit
    # new contract rather than falling through an OR with nullable legacy checks.
    for name in (
        "agent_turn_graph_context_receipt_check",
        "agent_turn_graph_context_execution_check",
        "agent_turn_graph_completion_check",
    ):
        definition = bind.execute(
            text(
                "SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conrelid='agent.turn'::regclass AND conname=:name"
            ),
            {"name": name},
        ).scalar_one()
        if not definition.startswith("CHECK (") or not definition.endswith(")"):
            raise RuntimeError("Expected owning turn CHECK predicate is unavailable")
        previous = definition[len("CHECK (") : -1]
        op.execute(f'ALTER TABLE agent.turn DROP CONSTRAINT "{name}"')
        op.execute(f'''ALTER TABLE agent.turn ADD CONSTRAINT "{name}" CHECK (
          CASE WHEN graph_context_receipt->>'schema'='dmb_native_statement_context_receipt_v1'
          THEN COALESCE(({_NATIVE}),FALSE) ELSE ({previous}) END)''')


def downgrade():
    raise RuntimeError("Retained native statement contexts require recovery forward")
