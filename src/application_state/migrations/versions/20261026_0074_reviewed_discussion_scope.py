"""Admit immutable Discuss task snapshots; historical payload bytes are unchanged."""
from alembic import op

revision = '20261026_0074'
down_revision = '20261025_0073'
branch_labels = None
depends_on = None


def upgrade():
    # The vocabulary lives in existing JSON payloads. Advancing the schema head
    # fences readers whose preflight knows only unscoped dispatch/binding shapes.
    pass


def downgrade():
    conn = op.get_bind()
    conn.exec_driver_sql('LOCK TABLE agent.work_plan,agent.turn_reviewed_action,agent.turn IN ACCESS EXCLUSIVE MODE')
    if conn.exec_driver_sql("""SELECT
 EXISTS(SELECT 1 FROM agent.work_plan WHERE jsonb_path_exists(payload,'$.dispatches[*] ? (@.schema == "dmb_work_plan_dispatch_v3")'))
 OR EXISTS(SELECT 1 FROM agent.turn_reviewed_action WHERE intent->'reviewed_step'->>'schema'='dmb_reviewed_step_binding_v3')
 OR EXISTS(SELECT 1 FROM agent.turn WHERE jsonb_path_exists(graph_context_execution,'$.events[*].intent.reviewed_step ? (@.schema == "dmb_reviewed_step_binding_v3")'))
 """).scalar_one():
        raise RuntimeError('Retained scoped Discuss dispatches require recovery forward')
