"""Admit mixed native evidence while retaining historical answer records."""
from importlib import import_module
from alembic import op

revision = "20261022_0046"
down_revision = "20261022_0045"
branch_labels = None
depends_on = None
_previous = import_module("application_state.migrations.versions.20261022_0045_surface_source_answers")
_OLD = f"({_previous._OLD}) OR COALESCE(({_previous._SOURCE}),FALSE)"
_MIXED = r'''
    surface_resolution='resolved' AND surface_id IN ('plan','play')
    AND completion->>'schema'='dmb_surface_evidence_completion_v1'
    AND completion ?& ARRAY['schema','surface_id','context_receipt_sha256','answer_basis',
        'answer_context_status','answer_segments','citation_map','source_citations']
    AND completion - ARRAY['schema','surface_id','context_receipt_sha256','answer_basis',
        'answer_context_status','answer_segments','citation_map','source_citations']='{}'::jsonb
    AND completion->>'surface_id'=surface_id
    AND completion->>'context_receipt_sha256'=graph_context_receipt->>'context_receipt_sha256'
    AND ((surface_id='plan' AND graph_context_receipt->>'schema'='dmb_agent_plan_world_graph_context_receipt_v1')
      OR (surface_id='play' AND graph_context_receipt->>'schema'='dmb_play_world_graph_context_receipt_v1'))
    AND graph_context_execution IS NOT NULL
    AND graph_context_execution->'events'->-1->>'kind'='completion_binding'
    AND completion->>'answer_basis'='mixed_evidence'
    AND completion->>'answer_context_status' IN ('graph_grounded','graph_grounded_partial',
        'source_grounded','source_grounded_partial','authored_grounded','authored_grounded_partial',
        'insufficient_evidence','creative_proposal')
    AND jsonb_typeof(completion->'citation_map') IN ('null','object')
    AND jsonb_typeof(completion->'answer_segments')='array'
    AND CASE WHEN jsonb_typeof(completion->'answer_segments')='array'
        THEN jsonb_array_length(completion->'answer_segments') BETWEEN 1 AND 128 ELSE FALSE END
    AND NOT jsonb_path_exists(completion,'$.answer_segments[*] ? (!exists(@.kind) || (@.kind != "graph_claim" && @.kind != "source_passage_claim" && @.kind != "authored_quote" && @.kind != "proposal" && @.kind != "limitation"))')
    AND jsonb_typeof(completion->'source_citations')='array'
    AND CASE WHEN jsonb_typeof(completion->'source_citations')='array'
        THEN jsonb_array_length(completion->'source_citations') BETWEEN 0 AND 16384 ELSE FALSE END
    AND octet_length(completion::text)<=1048576
'''


def upgrade():
    _previous._m42._replace("agent_turn_graph_completion_check",
        f"({_OLD}) OR COALESCE(({_MIXED}),FALSE)")


def downgrade():
    op.execute("LOCK TABLE agent.turn IN ACCESS EXCLUSIVE MODE")
    if op.get_bind().exec_driver_sql(
        "SELECT EXISTS(SELECT 1 FROM agent.turn WHERE completion->>'schema'='dmb_surface_evidence_completion_v1')"
    ).scalar_one():
        raise RuntimeError("Cannot discard retained mixed evidence answers")
    _previous._m42._replace("agent_turn_graph_completion_check", _OLD)
