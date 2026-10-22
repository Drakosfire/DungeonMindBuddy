"""Admit distinct Plan/Play source-backed answers without Graph claim authority."""

from importlib import import_module
from alembic import op

revision = "20261022_0045"
down_revision = "20261022_0044"
branch_labels = None
depends_on = None

_m42 = import_module(
    "application_state.migrations.versions.20261020_0042_native_play_graph"
)
_OLD = (
    f"CASE WHEN COALESCE(({_m42._NATIVE}),FALSE) THEN "
    f"COALESCE(({_m42._NEW['agent_turn_graph_completion_check']}),FALSE) "
    f"ELSE ({_m42._OLD['agent_turn_graph_completion_check']}) END"
)
_SOURCE = """
    surface_resolution='resolved' AND surface_id IN ('plan','play')
    AND completion->>'schema'='dmb_surface_source_completion_v1'
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
    AND completion->>'answer_basis'='opened_source_passages'
    AND completion->>'answer_context_status' IN ('source_grounded','source_grounded_partial')
    AND completion->'citation_map'='null'::jsonb
    AND jsonb_typeof(completion->'answer_segments')='array'
    AND CASE WHEN jsonb_typeof(completion->'answer_segments')='array'
        THEN jsonb_array_length(completion->'answer_segments') BETWEEN 1 AND 128 ELSE FALSE END
    AND jsonb_path_exists(completion,'$.answer_segments[*] ? (@.kind == "source_passage_claim")')
    AND NOT jsonb_path_exists(completion,'$.answer_segments[*] ? (!exists(@.kind) || (@.kind != "source_passage_claim" && @.kind != "connective" && @.kind != "proposal"))')
    AND jsonb_typeof(completion->'source_citations')='array'
    AND CASE WHEN jsonb_typeof(completion->'source_citations')='array'
        THEN jsonb_array_length(completion->'source_citations') BETWEEN 1 AND 16384 ELSE FALSE END
    AND octet_length(completion::text)<=1048576
"""


def upgrade():
    _m42._replace(
        "agent_turn_graph_completion_check", f"({_OLD}) OR COALESCE(({_SOURCE}),FALSE)"
    )


def downgrade():
    op.execute("LOCK TABLE agent.turn IN ACCESS EXCLUSIVE MODE")
    if (
        op.get_bind()
        .exec_driver_sql(
            "SELECT EXISTS(SELECT 1 FROM agent.turn WHERE completion->>'schema'='dmb_surface_source_completion_v1')"
        )
        .scalar_one()
    ):
        raise RuntimeError("Cannot discard retained surface source-answer records")
    _m42._replace("agent_turn_graph_completion_check", _OLD)
