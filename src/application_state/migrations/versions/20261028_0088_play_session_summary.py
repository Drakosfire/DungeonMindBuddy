"""Admit the shared session summary contract on Play; retain all prior bytes."""
from importlib import import_module
from alembic import op

revision = "20261028_0088"
down_revision = "20261028_0087"
branch_labels = None
depends_on = None
_prior = import_module("application_state.migrations.versions.20261027_0081_cited_session_summary")
_NEW = _prior._NEW.replace("surface_id='plan'", "surface_id IN ('plan','play')")


def upgrade():
    op.execute("LOCK TABLE agent.turn IN ACCESS EXCLUSIVE MODE")
    _prior._prior._intentional._replace("agent_turn_graph_completion_check", f"({_prior._OLD}) OR COALESCE(({_NEW}),FALSE)")


def downgrade():
    # Also fences literal-only v4 and interrupted v6 inputs with no completion.
    raise RuntimeError("Retained Play session carriers require recovery forward")
