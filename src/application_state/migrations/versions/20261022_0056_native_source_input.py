"""Admit exact native section provider input witnesses; no output activation."""
from importlib import import_module
from alembic import op

revision = "20261022_0056"
down_revision = "20261022_0055"
branch_labels = None
depends_on = None
_m42 = import_module("application_state.migrations.versions.20261020_0042_native_play_graph")
_m53 = import_module("application_state.migrations.versions.20261022_0053_native_source_navigation")
_m55 = import_module("application_state.migrations.versions.20261022_0055_native_source_sections")
_KINDS = (*_m55._KINDS, "native_source_provider_inclusion_v1")
_INVALID = '$[*] ? (!exists(@.kind) || ('+' && '.join('@.kind != "'+kind+'"' for kind in _KINDS)+'))'
_EXECUTION = _m55._EXECUTION.replace(_m55._INVALID, _INVALID)
_INCLUSION = "jsonb_path_exists(graph_context_execution,'$.events[*] ? (@.kind == \"native_source_provider_inclusion_v1\")')"
_NEW = f"(({_m55._NEW.replace(_m55._EXECUTION, _EXECUTION)}) AND (NOT COALESCE(({_INCLUSION}),FALSE) OR (COALESCE(({_m53._CAP}),FALSE) AND COALESCE(({_m55._SECTIONS}),FALSE))))"


def upgrade():
    _m42._replace("agent_turn_graph_context_execution_check", _NEW)


def downgrade():
    op.execute("LOCK TABLE agent.turn IN ACCESS EXCLUSIVE MODE")
    if op.get_bind().exec_driver_sql(f"SELECT EXISTS(SELECT 1 FROM agent.turn WHERE {_INCLUSION})").scalar_one():
        raise RuntimeError("Cannot discard retained native source input authority")
    _m42._replace("agent_turn_graph_context_execution_check", _m55._NEW)
