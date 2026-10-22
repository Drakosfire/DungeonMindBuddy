"""Admit explicit source reuse; historical read records keep their meanings."""
from importlib import import_module
from alembic import op

revision = "20261022_0047"
down_revision = "20261022_0046"
branch_labels = None
depends_on = None
_m42 = import_module("application_state.migrations.versions.20261020_0042_native_play_graph")
_OLD = f"CASE WHEN COALESCE(({_m42._NATIVE}),FALSE) THEN COALESCE(({_m42._EXECUTION}),FALSE) ELSE ({_m42._OLD['agent_turn_graph_context_execution_check']}) END"
_KINDS = (*_m42._KINDS, "source_passage_reused_v1", "provider_attempt_authorized_v4")
_INVALID_KIND = '$[*] ? (!exists(@.kind) || ('+' && '.join('@.kind != "'+kind+'"' for kind in _KINDS)+'))'
_EXECUTION = _m42._EXECUTION.replace(_m42._INVALID_KIND, _INVALID_KIND)
_NEW = f"CASE WHEN COALESCE(({_m42._NATIVE}),FALSE) THEN COALESCE(({_EXECUTION}),FALSE) ELSE ({_m42._OLD['agent_turn_graph_context_execution_check']}) END"


def upgrade():
    _m42._replace("agent_turn_graph_context_execution_check", _NEW)


def downgrade():
    op.execute("LOCK TABLE agent.turn IN ACCESS EXCLUSIVE MODE")
    if op.get_bind().exec_driver_sql("""SELECT EXISTS(SELECT 1 FROM agent.turn WHERE
        jsonb_path_exists(graph_context_execution,'$.events[*] ? (@.kind == "source_passage_reused_v1" || @.kind == "provider_attempt_authorized_v4" || @.kind == "plan_jev_writer_authorized_v2")'))""").scalar_one():
        raise RuntimeError("Cannot discard retained source reuse/provider inclusion records")
    _m42._replace("agent_turn_graph_context_execution_check", _OLD)
