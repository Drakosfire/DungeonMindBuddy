"""Admit selected native section authorizations/outcomes; no citation activation."""
from importlib import import_module
from alembic import op

revision = "20261022_0055"
down_revision = "20261022_0054"
branch_labels = None
depends_on = None
_m42 = import_module("application_state.migrations.versions.20261020_0042_native_play_graph")
_m53 = import_module("application_state.migrations.versions.20261022_0053_native_source_navigation")
_m54 = import_module("application_state.migrations.versions.20261022_0054_native_source_catalog")
_KINDS = (*_m54._KINDS, "native_source_section_authorized_v1", "native_source_section_observed_v1")
_INVALID = '$[*] ? (!exists(@.kind) || ('+' && '.join('@.kind != "'+kind+'"' for kind in _KINDS)+'))'
_EXECUTION = _m54._EXECUTION.replace(_m54._INVALID, _INVALID)
_SECTIONS = "jsonb_path_exists(graph_context_execution,'$.events[*] ? (@.kind == \"native_source_section_authorized_v1\" || @.kind == \"native_source_section_observed_v1\")')"
_NEW = f"(({_m54._NEW.replace(_m54._EXECUTION, _EXECUTION)}) AND (NOT COALESCE(({_SECTIONS}),FALSE) OR (COALESCE(({_m53._CAP}),FALSE) AND COALESCE(({_m54._CATALOG}),FALSE))))"


def upgrade():
    _m42._replace("agent_turn_graph_context_execution_check", _NEW)


def downgrade():
    op.execute("LOCK TABLE agent.turn IN ACCESS EXCLUSIVE MODE")
    if op.get_bind().exec_driver_sql(f"SELECT EXISTS(SELECT 1 FROM agent.turn WHERE {_SECTIONS})").scalar_one():
        raise RuntimeError("Cannot discard retained native source section authority")
    _m42._replace("agent_turn_graph_context_execution_check", _m54._NEW)
