"""Persist explicit corpus source capability; preserve old frozen event meanings."""
from importlib import import_module
from alembic import op

revision = '20261027_0079'
down_revision = '20261026_0078'
branch_labels = None
depends_on = None
_m42 = import_module('application_state.migrations.versions.20261020_0042_native_play_graph')
_m53 = import_module('application_state.migrations.versions.20261022_0053_native_source_navigation')
_m55 = import_module('application_state.migrations.versions.20261022_0055_native_source_sections')
_m56 = import_module('application_state.migrations.versions.20261022_0056_native_source_input')
_CAP = "graph_context_execution->'policy'->>'corpus_source_policy'='registered_corpus_sections_v1'"
_KINDS = (*_m56._KINDS, 'corpus_source_search_authorized_v1', 'corpus_source_search_observed_v1',
          'native_source_navigation_authorized_v2', 'native_source_section_observed_v2')
_INVALID = '$[*] ? (!exists(@.kind) || ('+' && '.join('@.kind != "'+kind+'"' for kind in _KINDS)+'))'
_EXTRA = "jsonb_path_exists(graph_context_execution,'$.events[*] ? (@.kind == \"corpus_source_search_authorized_v1\" || @.kind == \"corpus_source_search_observed_v1\" || @.kind == \"native_source_navigation_authorized_v2\" || @.kind == \"native_source_section_observed_v2\")')"
_CURRENT = _m56._NEW.replace(_m56._INVALID, _INVALID).replace(
    _m42._closed(_m42.POL, _m53._POLICY_KEYS + ' native_source_section_policy'),
    _m42._closed(_m42.POL, _m53._POLICY_KEYS + ' native_source_section_policy corpus_source_policy'))
_CURRENT = _CURRENT.replace(_m55._SECTIONS, _m55._SECTIONS.replace(
    '@.kind == "native_source_section_observed_v1"',
    '@.kind == "native_source_section_observed_v1" || @.kind == "native_source_section_observed_v2"'))
_CURRENT = _CURRENT.replace(_m53._NAV, _m53._NAV.replace(
    '@.kind == "native_source_navigation_authorized_v1"',
    '@.kind == "native_source_navigation_authorized_v1" || @.kind == "native_source_navigation_authorized_v2"'))
_NEW = f"(CASE WHEN COALESCE(({_CAP}),FALSE) THEN ({_CURRENT}) ELSE ({_m56._NEW}) END) AND (NOT COALESCE(({_EXTRA}),FALSE) OR COALESCE(({_CAP}),FALSE))"


def upgrade():
    _m42._replace('agent_turn_graph_context_execution_check', _NEW)


def downgrade():
    op.execute('LOCK TABLE agent.turn IN ACCESS EXCLUSIVE MODE')
    if op.get_bind().exec_driver_sql(f"SELECT EXISTS(SELECT 1 FROM agent.turn WHERE {_CAP} OR {_EXTRA})").scalar_one():
        raise RuntimeError('Cannot discard retained corpus source authority; recover forward')
    _m42._replace('agent_turn_graph_context_execution_check', _m56._NEW)
