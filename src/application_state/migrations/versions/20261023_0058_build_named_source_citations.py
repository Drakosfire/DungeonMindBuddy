"""Admit named Build citations without rewriting historical answers."""

from importlib import import_module
from alembic import op

revision = "20261023_0058"
down_revision = "20261023_0057"
branch_labels = None
depends_on = None
_previous = import_module(
    "application_state.migrations.versions.20261023_0057_native_source_citations"
)
_build = import_module(
    "application_state.migrations.versions.20261017_0029_build_source_passage_completion"
)
_OLD = f"({_previous._OLD}) OR COALESCE(({_previous._NATIVE}),FALSE)"
_NAMED = _build._V2.replace(
    "dmb_build_graph_completion_v2", "dmb_build_graph_completion_v3"
)
_NAMED += " AND graph_context_execution->'policy'->>'source_citation_names_policy'='build_verified_source_names_v1'"
_NAMED += ' AND NOT jsonb_path_exists(completion, \'$.source_citations[*] ? (!exists(@.source_name) || @.source_name.type() != "string" || @.source_name == "")\')'


def upgrade():
    _build._predecessor._replace(
        "agent_turn_graph_completion_check", f"({_OLD}) OR COALESCE(({_NAMED}),FALSE)"
    )


def downgrade():
    op.execute("LOCK TABLE agent.turn IN ACCESS EXCLUSIVE MODE")
    if (
        op.get_bind()
        .exec_driver_sql(
            "SELECT EXISTS(SELECT 1 FROM agent.turn WHERE completion->>'schema'='dmb_build_graph_completion_v3')"
        )
        .scalar_one()
    ):
        raise RuntimeError("Cannot discard retained named Build source citations")
    _build._predecessor._replace("agent_turn_graph_completion_check", _OLD)
