"""Admit explicitly source-attributed Build writer completions."""

from importlib import import_module
from alembic import op
import sqlalchemy as sa

revision = "20261017_0029"
down_revision = "20261016_0027"
branch_labels = None
depends_on = None

_predecessor = import_module(
    "application_state.migrations.versions.20261016_0024_build_graph_turns"
)
_OLD = (
    "((completion IS NULL OR graph_context_receipt->>'schema' = 'dmb_agent_plan_world_graph_context_receipt_v1') "
    f"AND ({_predecessor._PLAN_COMPLETION})) OR COALESCE(({_predecessor._BUILD_COMPLETION}), FALSE)"
)
_V2 = """
    graph_context_receipt->>'schema' = 'dmb_build_graph_context_receipt_v1'
    AND completion->>'schema' = 'dmb_build_graph_completion_v2'
    AND completion ?& ARRAY['context_receipt_sha256', 'answer_basis', 'answer_context_status',
        'answer_segments', 'citation_map', 'source_citations']
    AND (completion - ARRAY['schema', 'context_receipt_sha256', 'answer_basis', 'answer_context_status',
        'answer_segments', 'citation_map', 'source_citations']) = '{}'::jsonb
    AND completion->>'context_receipt_sha256' = graph_context_receipt->>'context_receipt_sha256'
    AND completion->>'answer_basis' IN ('opened_source_passages', 'saved_source_and_opened_passages')
    AND completion->>'answer_context_status' IN ('source_grounded', 'source_grounded_partial', 'source_insufficient_evidence')
    AND completion->'citation_map' = 'null'::jsonb
    AND jsonb_typeof(completion->'answer_segments') = 'array'
    AND CASE WHEN jsonb_typeof(completion->'answer_segments') = 'array'
        THEN jsonb_array_length(completion->'answer_segments') BETWEEN 1 AND 128 ELSE FALSE END
    AND NOT jsonb_path_exists(completion, '$.answer_segments[*] ? (!exists(@.kind) || (@.kind != "saved_source_claim" && @.kind != "source_passage_claim" && @.kind != "connective"))')
    AND ((completion->>'answer_basis' = 'saved_source_and_opened_passages') =
        jsonb_path_exists(completion, '$.answer_segments[*] ? (@.kind == "saved_source_claim")'))
    AND NOT jsonb_path_exists(completion, '$.answer_segments[*] ? (@.kind == "saved_source_claim" && (!exists(@.content_sha256) || @.content_sha256 != $hash))', jsonb_build_object('hash', graph_context_receipt->'source_basis'->'content_sha256'))
    AND jsonb_typeof(completion->'source_citations') = 'array'
    AND CASE WHEN jsonb_typeof(completion->'source_citations') = 'array'
        THEN jsonb_array_length(completion->'source_citations') BETWEEN 0 AND 16384 ELSE FALSE END
    AND ((completion->>'answer_context_status' = 'source_insufficient_evidence'
        AND completion->'source_citations' = '[]'::jsonb
        AND NOT jsonb_path_exists(completion, '$.answer_segments[*] ? (@.kind != "connective")'))
      OR (completion->>'answer_context_status' IN ('source_grounded', 'source_grounded_partial')
        AND jsonb_path_exists(completion, '$.answer_segments[*] ? (@.kind == "source_passage_claim")')
        AND completion->'source_citations' != '[]'::jsonb))
    AND octet_length(completion::text) <= 1048576
"""


def upgrade():
    _predecessor._replace(
        "agent_turn_graph_completion_check", f"({_OLD}) OR COALESCE(({_V2}), FALSE)"
    )


def downgrade():
    if (
        op.get_bind()
        .execute(
            sa.text(
                "SELECT EXISTS (SELECT 1 FROM agent.turn WHERE completion->>'schema' = 'dmb_build_graph_completion_v2')"
            )
        )
        .scalar()
    ):
        raise RuntimeError(
            "Cannot downgrade while retained source-passage Build completions exist"
        )
    _predecessor._replace("agent_turn_graph_completion_check", _OLD)
