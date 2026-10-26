"""Admit explicit generated plan selections; never rewrite retained payloads."""
from importlib import import_module
from alembic import op

revision = '20261026_0075'
down_revision = '20261026_0074'
branch_labels = None
depends_on = None
_objective = import_module('application_state.migrations.versions.20261025_0072_plan_objective')
_intentional = import_module('application_state.migrations.versions.20261025_0070_intentional_build_response')
_OLD_COMPLETION = f'({_objective._OLD}) OR ({_objective._NEW})'
_OLD_LIFECYCLE = f"({_intentional._NEW_LIFECYCLE}) OR COALESCE((status='completed' AND assistant_text='' AND failure_code IS NULL AND completed_at IS NOT NULL AND completion->'answer_segments'='[]'::jsonb AND ({_objective._INTENTIONAL})),FALSE)"


def selected_branch(expression, old, new):
    needle='(@.kind != "discuss" && @.kind != "prepare_insertion")'
    assert expression.count(needle)==1
    expression=expression.replace(old,new).replace('build_plan_output_contract_v1','build_plan_output_contract_v2').replace('typed_plan_objective_v1','typed_plan_selection_v1')
    return expression.replace(needle,needle+' || !exists(@.selected) || @.selected.type() != "boolean" || exists(@.keyvalue() ? (@.key != "text" && @.key != "kind" && @.key != "selected"))')


_INTENTIONAL = selected_branch(_objective._INTENTIONAL,'dmb_build_intentional_response_completion_v2','dmb_build_intentional_response_completion_v3')
_REVIEWED = selected_branch(_objective._REVIEWED,'dmb_build_relationship_review_completion_v2','dmb_build_relationship_review_completion_v3')
# V3 is the shared selection-aware draft wrapper; these extra object kinds
# require their own policy only when that kind is actually present.
for _kind, _field, _policy in (
    ('connected_page', 'connected_page_review_policy', 'typed_connected_page_review_v1'),
    ('relationship', 'relationship_review_policy', 'typed_saved_relationship_review_v1'),
):
    _gate=f"graph_context_execution->'policy'->>'{_field}'='{_policy}'"
    assert _REVIEWED.count(_gate)==1
    _REVIEWED=_REVIEWED.replace(_gate,f"(completion->'collaboration'->>'kind' IS DISTINCT FROM '{_kind}' OR COALESCE(({_gate}),FALSE))")
_NEW = f'COALESCE(({_INTENTIONAL}),FALSE) OR COALESCE(({_REVIEWED}),FALSE)'


def upgrade():
    conn=op.get_bind()
    conn.exec_driver_sql('LOCK TABLE agent.turn IN ACCESS EXCLUSIVE MODE')
    _intentional._replace('agent_turn_graph_completion_check',f'({_OLD_COMPLETION}) OR ({_NEW})')
    _intentional._replace('agent_turn_lifecycle_check',f"({_OLD_LIFECYCLE}) OR COALESCE((status='completed' AND assistant_text='' AND failure_code IS NULL AND completed_at IS NOT NULL AND completion->'answer_segments'='[]'::jsonb AND ({_INTENTIONAL})),FALSE)")


def downgrade():
    conn=op.get_bind()
    conn.exec_driver_sql('LOCK TABLE agent.turn IN ACCESS EXCLUSIVE MODE')
    if conn.exec_driver_sql("""SELECT EXISTS(SELECT 1 FROM agent.turn WHERE
       completion->>'schema' IN ('dmb_build_intentional_response_completion_v3','dmb_build_relationship_review_completion_v3')
       OR jsonb_path_exists(graph_context_execution,'$.events[*] ? (@.kind == "build_plan_output_contract_v2")'))""").scalar_one():
        raise RuntimeError('Retained generated plan selection requires recovery forward')
    _intentional._replace('agent_turn_graph_completion_check',_OLD_COMPLETION)
    _intentional._replace('agent_turn_lifecycle_check',_OLD_LIFECYCLE)
