"""Admit distinct host Build proposal completions; never Graph grounding."""

from importlib import import_module
from alembic import op
import sqlalchemy as sa

revision = "20261017_0030"
down_revision = "20261017_0029"
branch_labels = None
depends_on = None

_previous = import_module(
    "application_state.migrations.versions.20261017_0029_build_source_passage_completion"
)
_OLD = f"({_previous._OLD}) OR COALESCE(({_previous._V2}), FALSE)"
_AUTHORING = """
    graph_context_receipt->>'schema' = 'dmb_build_graph_context_receipt_v1'
    AND completion->>'schema' = 'dmb_build_authoring_completion_v1'
    AND completion ?& ARRAY['context_receipt_sha256', 'answer_basis', 'answer_context_status',
        'answer_segments', 'citation_map', 'action_id', 'reservation_sha256', 'proposal_result_sha256',
        'provider_attempt_id', 'envelope_sha256']
    AND (completion - ARRAY['schema', 'context_receipt_sha256', 'answer_basis', 'answer_context_status',
        'answer_segments', 'citation_map', 'action_id', 'reservation_sha256', 'proposal_result_sha256',
        'provider_attempt_id', 'envelope_sha256']) = '{}'::jsonb
    AND completion->>'context_receipt_sha256' = graph_context_receipt->>'context_receipt_sha256'
    AND completion->>'answer_basis' = 'prepared_page_proposal'
    AND completion->>'answer_context_status' = 'proposal_ready'
    AND completion->'citation_map' = 'null'::jsonb
    AND jsonb_typeof(completion->'answer_segments') = 'array'
    AND CASE WHEN jsonb_typeof(completion->'answer_segments') = 'array'
        THEN jsonb_array_length(completion->'answer_segments') = 1 ELSE FALSE END
    AND completion->'answer_segments'->0->>'kind' = 'connective'
    AND completion->'answer_segments'->0->>'text' = 'A preview is ready. Review it before inserting it into the page. Nothing has been saved or published.'
    AND completion->>'reservation_sha256' ~ '^[a-f0-9]{64}$'
    AND completion->>'proposal_result_sha256' ~ '^[a-f0-9]{64}$'
    AND completion->>'envelope_sha256' ~ '^[a-f0-9]{64}$'
    AND completion->>'action_id' ~ '^[a-f0-9-]{36}$'
    AND completion->>'provider_attempt_id' ~ '^[a-f0-9-]{36}$'
    AND octet_length(completion::text) <= 16384
"""


def upgrade():
    _previous._predecessor._replace(
        "agent_turn_graph_completion_check",
        f"({_OLD}) OR COALESCE(({_AUTHORING}), FALSE)",
    )


def downgrade():
    if (
        op.get_bind()
        .execute(
            sa.text(
                "SELECT EXISTS (SELECT 1 FROM agent.turn WHERE completion->>'schema' = 'dmb_build_authoring_completion_v1')"
            )
        )
        .scalar()
    ):
        raise RuntimeError(
            "Cannot downgrade while retained Build authoring completions exist"
        )
    _previous._predecessor._replace("agent_turn_graph_completion_check", _OLD)
