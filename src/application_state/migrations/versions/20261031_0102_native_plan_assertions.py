"""Native assertion Plan records; reader fence, no retained turn rewrites."""
from importlib import import_module
from alembic import op
from sqlalchemy import text

revision = '20261031_0102'
down_revision = '20261031_0101'
branch_labels = None
depends_on = None


def upgrade():
    # Extend the owning closed turn branch, preserving the original branch exactly.
    native = import_module('application_state.migrations.versions.20261030_0095_native_plan_statements')._NATIVE
    native = native.replace("IN ('dmb_native_plan_query_v1','dmb_native_plan_query_unavailable_v1')", "='dmb_native_plan_query_v2'")
    native = native.replace('@.kind != "completion_binding"', '@.kind != "native_plan_assertion_read_authorized_v1" && @.kind != "native_plan_assertion_read_observed_v1" && @.kind != "plan_native_writer_authorized_v2" && @.kind != "completion_binding"')
    native = native.replace("'native_clause_citations']", "'native_clause_citations','native_assertion_citations']")
    native = native.replace("completion->>'schema'='dmb_surface_evidence_completion_v6'", "completion->>'schema'='dmb_surface_evidence_completion_v7'")
    native += " AND (completion IS NULL OR jsonb_typeof(completion->'native_assertion_citations')='array')"
    for name in ('agent_turn_graph_context_receipt_check', 'agent_turn_graph_context_execution_check', 'agent_turn_graph_completion_check'):
        definition = op.get_bind().execute(text(
            "SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conrelid='agent.turn'::regclass AND conname=:name"), {'name': name}).scalar_one()
        if not definition.startswith('CHECK (') or not definition.endswith(')'):
            raise RuntimeError('Owning turn CHECK predicate unavailable')
        previous = definition[len('CHECK ('):-1]
        op.execute(f'ALTER TABLE agent.turn DROP CONSTRAINT "{name}"')
        op.execute(f'''ALTER TABLE agent.turn ADD CONSTRAINT "{name}" CHECK (
          CASE WHEN graph_context_receipt#>>'{{native_query,schema}}'='dmb_native_plan_query_v2'
          THEN COALESCE(({native}),FALSE) ELSE ({previous}) END)''')


def downgrade():
    raise RuntimeError('Retained native assertion records require recovery forward')
