"""Admit catalog outcomes only under explicit native source navigation."""
from importlib import import_module
from alembic import op

revision = "20261022_0054"
down_revision = "20261022_0053"
branch_labels = None
depends_on = None
_m42 = import_module("application_state.migrations.versions.20261020_0042_native_play_graph")
_m53 = import_module("application_state.migrations.versions.20261022_0053_native_source_navigation")
_KINDS = (*_m53._KINDS, "native_source_catalog_observed_v1")
_INVALID = '$[*] ? (!exists(@.kind) || ('+' && '.join('@.kind != "'+kind+'"' for kind in _KINDS)+'))'
_EXECUTION = _m53._EXECUTION.replace(_m53._INVALID, _INVALID)
_CATALOG = "jsonb_path_exists(graph_context_execution,'$.events[*] ? (@.kind == \"native_source_catalog_observed_v1\")')"
_NEW = f"(({_m53._NEW.replace(_m53._EXECUTION, _EXECUTION)}) AND (NOT COALESCE(({_CATALOG}),FALSE) OR (COALESCE(({_m53._CAP}),FALSE) AND COALESCE(({_m53._NAV}),FALSE))))"


def upgrade():
    _m42._replace("agent_turn_graph_context_execution_check", _NEW)


def downgrade():
    op.execute("LOCK TABLE agent.turn IN ACCESS EXCLUSIVE MODE")
    if op.get_bind().exec_driver_sql(f"SELECT EXISTS(SELECT 1 FROM agent.turn WHERE {_CATALOG})").scalar_one():
        raise RuntimeError("Cannot discard retained native source catalog outcomes")
    _m42._replace("agent_turn_graph_context_execution_check", _m53._NEW)
