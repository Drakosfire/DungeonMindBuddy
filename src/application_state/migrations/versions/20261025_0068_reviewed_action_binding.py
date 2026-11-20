"""Guard retained author-reviewed action vocabulary against older runtimes."""
from alembic import op
revision = "20261025_0068"
down_revision = "20261025_0067"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""CREATE TABLE agent.turn_reviewed_action (
        turn_id UUID PRIMARY KEY REFERENCES agent.turn(turn_id) ON DELETE RESTRICT,
        intent JSONB NOT NULL,
        CHECK(intent->>'schema'='dmb_build_graph_intent_v1'),
        CHECK(jsonb_typeof(intent->'reviewed_step')='object'))""")


def downgrade():
    op.execute("LOCK TABLE agent.turn IN ACCESS EXCLUSIVE MODE")
    op.execute("LOCK TABLE agent.turn_reviewed_action IN ACCESS EXCLUSIVE MODE")
    if op.get_bind().exec_driver_sql("""SELECT EXISTS(SELECT 1 FROM agent.turn_reviewed_action)
        OR EXISTS(SELECT 1 FROM agent.turn WHERE jsonb_path_exists(graph_context_execution,
        '$.events[*] ? (@.kind == "build_reviewed_action_selected_v1")'))""").scalar_one():
        raise RuntimeError("Retained reviewed action bindings require recovery forward")
    op.execute("DROP TABLE agent.turn_reviewed_action")
