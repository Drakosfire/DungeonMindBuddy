"""Admit versioned exact native source citations without changing old answers."""
from importlib import import_module
from alembic import op

revision = '20261023_0057'
down_revision = '20261022_0056'
branch_labels = None
depends_on = None
_m48 = import_module('application_state.migrations.versions.20261022_0048_authored_excerpt_blocks')
_m53 = import_module('application_state.migrations.versions.20261022_0053_native_source_navigation')
_OLD = f"({_m48._OLD}) OR COALESCE(({_m48._BLOCKS}),FALSE)"
_NATIVE = _m48._BLOCKS.replace('dmb_surface_evidence_completion_v2','dmb_surface_evidence_completion_v3').replace("'source_citations']","'source_citations','native_source_citations']")
_NATIVE += f" AND COALESCE(({_m53._CAP}),FALSE) AND jsonb_typeof(completion->'native_source_citations')='array' AND CASE WHEN jsonb_typeof(completion->'native_source_citations')='array' THEN jsonb_array_length(completion->'native_source_citations') BETWEEN 0 AND 16384 ELSE FALSE END"


def upgrade():
    _m48._m46._previous._m42._replace('agent_turn_graph_completion_check',f"({_OLD}) OR COALESCE(({_NATIVE}),FALSE)")


def downgrade():
    op.execute('LOCK TABLE agent.turn IN ACCESS EXCLUSIVE MODE')
    if op.get_bind().exec_driver_sql("SELECT EXISTS(SELECT 1 FROM agent.turn WHERE completion->>'schema'='dmb_surface_evidence_completion_v3')").scalar_one():
        raise RuntimeError('Cannot discard retained native source citations')
    _m48._m46._previous._m42._replace('agent_turn_graph_completion_check',_OLD)
