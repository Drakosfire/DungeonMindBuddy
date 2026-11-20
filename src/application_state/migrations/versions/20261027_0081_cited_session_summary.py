"""Admit cited session synthesis without changing retained completion bytes."""
from importlib import import_module
from alembic import op

revision = "20261027_0081"
down_revision = "20261027_0080"
branch_labels = None
depends_on = None
_prior = import_module("application_state.migrations.versions.20261026_0075_plan_proposal_selection")
_native = import_module("application_state.migrations.versions.20261023_0057_native_source_citations")
_OLD = f"({_prior._OLD_COMPLETION}) OR ({_prior._NEW})"
_NEW = _native._NATIVE.replace("dmb_surface_evidence_completion_v3", "dmb_surface_evidence_completion_v4")
assert _NEW.count('@.kind != "authored_excerpt"') == 1
_NEW = _NEW.replace('@.kind != "authored_excerpt"', '@.kind != "authored_excerpt" && @.kind != "session_summary"')
_NEW += " AND surface_id='plan'"


def upgrade():
    op.execute("LOCK TABLE agent.turn IN ACCESS EXCLUSIVE MODE")
    _prior._intentional._replace("agent_turn_graph_completion_check", f"({_OLD}) OR COALESCE(({_NEW}),FALSE)")


def downgrade():
    op.execute("LOCK TABLE agent.turn IN ACCESS EXCLUSIVE MODE")
    if op.get_bind().exec_driver_sql("SELECT EXISTS(SELECT 1 FROM agent.turn WHERE completion->>'schema'='dmb_surface_evidence_completion_v4')").scalar_one():
        raise RuntimeError("Retained cited session summaries require recovery forward")
    _prior._intentional._replace("agent_turn_graph_completion_check", _OLD)
