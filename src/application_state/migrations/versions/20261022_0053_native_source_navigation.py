"""Admit explicit native source navigation; never a content/citation receipt."""
from importlib import import_module
from alembic import op

revision = "20261022_0053"
down_revision = "20261022_0052"
branch_labels = None
depends_on = None
_m42 = import_module("application_state.migrations.versions.20261020_0042_native_play_graph")
_m47 = import_module("application_state.migrations.versions.20261022_0047_source_passage_reuse")
_CAP = "graph_context_execution->'policy'->>'native_source_section_policy'='exact_native_source_sections_v1'"
_NAV = "jsonb_path_exists(graph_context_execution,'$.events[*] ? (@.kind == \"native_source_navigation_authorized_v1\")')"
_POLICY_KEYS = "policy_version allowed_graph_operations max_provider_attempts max_graph_operations max_results_per_operation max_total_provider_input_tokens max_total_provider_output_tokens provider_input_accounting source_opened source_read_scope max_source_read_chars max_chars_per_source_read source_read_accounting"
_KINDS = (*_m47._KINDS, "native_source_navigation_authorized_v1")
_INVALID = '$[*] ? (!exists(@.kind) || ('+' && '.join('@.kind != "'+kind+'"' for kind in _KINDS)+'))'
_EXECUTION = _m47._EXECUTION.replace(_m47._INVALID_KIND, _INVALID).replace(
    _m42._closed(_m42.POL, _POLICY_KEYS),
    _m42._closed(_m42.POL, _POLICY_KEYS + " native_source_section_policy"))
_NEW = f"""(
 CASE WHEN COALESCE(({_m42._NATIVE}),FALSE) THEN
   CASE WHEN COALESCE(({_CAP}),FALSE) THEN COALESCE(({_EXECUTION}),FALSE)
   ELSE COALESCE(({_m47._EXECUTION}),FALSE) END
 ELSE ({_m42._OLD['agent_turn_graph_context_execution_check']}) END
 AND (NOT COALESCE(({_NAV}),FALSE) OR COALESCE(({_CAP}),FALSE))
)"""


def upgrade():
    _m42._replace("agent_turn_graph_context_execution_check", _NEW)


def downgrade():
    op.execute("LOCK TABLE agent.turn IN ACCESS EXCLUSIVE MODE")
    if op.get_bind().exec_driver_sql(f"""SELECT EXISTS(SELECT 1 FROM agent.turn WHERE
        graph_context_execution->'policy' ? 'native_source_section_policy' OR {_NAV})""").scalar_one():
        raise RuntimeError("Cannot discard retained native source navigation authority")
    _m42._replace("agent_turn_graph_context_execution_check", _m47._NEW)
