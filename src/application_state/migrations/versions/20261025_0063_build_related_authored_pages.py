"""Admit explicit related authored-page completions without rewriting historical meanings."""

from importlib import import_module
from alembic import op

revision = "20261025_0063"
down_revision = "20261024_0062"
branch_labels = None
depends_on = None
_draft = import_module(
    "application_state.migrations.versions.20261024_0061_build_draft_context_completion"
)
_OLD = f"({_draft._OLD}) OR COALESCE(({_draft._DRAFT}),FALSE)"
_RELATED = (
    _draft._DRAFT.replace(
        "dmb_build_draft_context_completion_v1", "dmb_build_related_page_completion_v1"
    )
    .replace(
        '@.kind != "draft_reference_claim" &&',
        '@.kind != "related_page_claim" && @.kind != "draft_reference_claim" &&',
    )
    .replace(
        '@.kind == "draft_reference_claim"',
        '(@.kind == "draft_reference_claim" || @.kind == "related_page_claim")',
    )
    + " AND graph_context_execution->'policy'->>'related_page_context_policy'='selected_exact_related_authored_pages_v1'"
)


def upgrade():
    _draft._named._build._predecessor._replace(
        "agent_turn_graph_completion_check", f"({_OLD}) OR COALESCE(({_RELATED}),FALSE)"
    )


def downgrade():
    op.execute("LOCK TABLE agent.turn IN ACCESS EXCLUSIVE MODE")
    if (
        op.get_bind()
        .exec_driver_sql(
            "SELECT EXISTS(SELECT 1 FROM agent.turn WHERE completion->>'schema'='dmb_build_related_page_completion_v1' OR graph_context_execution->'policy'->>'related_page_context_policy'='selected_exact_related_authored_pages_v1')"
        )
        .scalar_one()
    ):
        raise RuntimeError(
            "Cannot discard retained related-page authoring authority; recover forward"
        )
    _draft._named._build._predecessor._replace(
        "agent_turn_graph_completion_check", _OLD
    )
