"""Durable author-reviewed work plans, separate from transcript and execution truth."""

from alembic import op

revision = "20261025_0064"
down_revision = "20261025_0063"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""CREATE TABLE agent.work_plan (
        world_id TEXT NOT NULL, conversation_id UUID NOT NULL, source_turn_id UUID NOT NULL,
        revision BIGINT NOT NULL CHECK(revision>0),payload JSONB NOT NULL,
        PRIMARY KEY(world_id,conversation_id,source_turn_id),
        FOREIGN KEY(conversation_id,world_id) REFERENCES agent.conversation(conversation_id,world_id),
        FOREIGN KEY(source_turn_id) REFERENCES agent.turn(turn_id),
        CHECK(payload->>'schema'='dmb_reviewed_work_plan_v1'),
        CHECK(payload->>'world_id'=world_id),
        CHECK(payload->>'conversation_id'=conversation_id::text),
        CHECK(payload->>'source_turn_id'=source_turn_id::text),
        CHECK((payload->>'revision')::bigint=revision))""")


def downgrade():
    op.execute("LOCK TABLE agent.work_plan IN ACCESS EXCLUSIVE MODE")
    if (
        op.get_bind()
        .exec_driver_sql("SELECT EXISTS(SELECT 1 FROM agent.work_plan)")
        .scalar_one()
    ):
        raise RuntimeError("Retained reviewed work plans require recovery forward")
    op.execute("DROP TABLE agent.work_plan")
