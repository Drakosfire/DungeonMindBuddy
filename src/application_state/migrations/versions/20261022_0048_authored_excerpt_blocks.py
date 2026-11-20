"""Admit versioned host-materialized authored excerpts, preserving old answers."""
from importlib import import_module
from alembic import op

revision='20261022_0048'
down_revision='20261022_0047'
branch_labels=None
depends_on=None
_m46=import_module('application_state.migrations.versions.20261022_0046_surface_evidence_answers')
_OLD=f"({_m46._OLD}) OR COALESCE(({_m46._MIXED}),FALSE)"
_BLOCKS=_m46._MIXED.replace('dmb_surface_evidence_completion_v1','dmb_surface_evidence_completion_v2').replace('authored_quote','authored_excerpt')


def upgrade():
    _m46._previous._m42._replace('agent_turn_graph_completion_check',f"({_OLD}) OR COALESCE(({_BLOCKS}),FALSE)")


def downgrade():
    op.execute('LOCK TABLE agent.turn IN ACCESS EXCLUSIVE MODE')
    if op.get_bind().exec_driver_sql("SELECT EXISTS(SELECT 1 FROM agent.turn WHERE completion->>'schema'='dmb_surface_evidence_completion_v2')").scalar_one():
        raise RuntimeError('Cannot discard retained authored block answers')
    _m46._previous._m42._replace('agent_turn_graph_completion_check',_OLD)
