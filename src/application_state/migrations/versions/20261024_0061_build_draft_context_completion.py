"""Admit working-draft answers with separate source citations; never rewrite history."""
from importlib import import_module
from alembic import op

revision = "20261024_0061"
down_revision = "20261023_0060"
branch_labels = None
depends_on = None
_named = import_module("application_state.migrations.versions.20261023_0058_build_named_source_citations")
_OLD = f"({_named._OLD}) OR COALESCE(({_named._NAMED}),FALSE)"
_DRAFT = """
 graph_context_receipt->>'schema'='dmb_build_graph_context_receipt_v1'
 AND graph_context_execution->'policy'->>'working_draft_context_policy'='captured_build_working_draft_context_v1'
 AND completion->>'schema'='dmb_build_draft_context_completion_v1'
 AND completion ?& ARRAY['context_receipt_sha256','answer_basis','answer_context_status','answer_segments','citation_map','source_citations']
 AND (completion - ARRAY['schema','context_receipt_sha256','answer_basis','answer_context_status','answer_segments','citation_map','source_citations'])='{}'::jsonb
 AND completion->>'context_receipt_sha256'=graph_context_receipt->>'context_receipt_sha256'
 AND completion->>'answer_basis'='working_draft_context'
 AND completion->>'answer_context_status' IN ('authored_grounded','authored_grounded_partial','source_grounded','source_grounded_partial','creative_proposal','insufficient_evidence')
 AND completion->'citation_map'='null'::jsonb
 AND jsonb_typeof(completion->'answer_segments')='array'
 AND CASE WHEN jsonb_typeof(completion->'answer_segments')='array' THEN jsonb_array_length(completion->'answer_segments') BETWEEN 1 AND 128 ELSE FALSE END
 AND NOT jsonb_path_exists(completion, '$.answer_segments[*] ? (!exists(@.kind) || (@.kind != "draft_reference_claim" && @.kind != "saved_source_claim" && @.kind != "source_passage_claim" && @.kind != "connective"))')
 AND ((completion->>'answer_context_status' IN ('authored_grounded','authored_grounded_partial'))=jsonb_path_exists(completion, '$.answer_segments[*] ? (@.kind == "draft_reference_claim")'))
 AND NOT jsonb_path_exists(completion, '$.answer_segments[*] ? (@.kind == "saved_source_claim" && (!exists(@.content_sha256) || @.content_sha256 != $hash))',jsonb_build_object('hash',graph_context_receipt->'source_basis'->'content_sha256'))
 AND jsonb_typeof(completion->'source_citations')='array'
 AND NOT jsonb_path_exists(completion, '$.source_citations[*] ? (!exists(@.source_name) || @.source_name.type() != "string" || @.source_name == "")')
 AND octet_length(completion::text)<=1048576
"""


def upgrade():
    _named._build._predecessor._replace("agent_turn_graph_completion_check", f"({_OLD}) OR COALESCE(({_DRAFT}),FALSE)")


def downgrade():
    op.execute("LOCK TABLE agent.turn IN ACCESS EXCLUSIVE MODE")
    if op.get_bind().exec_driver_sql("SELECT EXISTS(SELECT 1 FROM agent.turn WHERE completion->>'schema'='dmb_build_draft_context_completion_v1')").scalar_one():
        raise RuntimeError("Cannot discard retained working-draft answer authority; recover forward")
    _named._build._predecessor._replace("agent_turn_graph_completion_check", _OLD)
