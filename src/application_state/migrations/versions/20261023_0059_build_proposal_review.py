"""Durable mutable review and client-observed insertion receipts, not source Save."""

from alembic import op

revision = "20261023_0059"
down_revision = "20261023_0058"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "ALTER TABLE agent.build_proposal ADD CONSTRAINT build_proposal_action_world UNIQUE(action_id,world_id)"
    )
    op.execute("""CREATE TABLE agent.build_proposal_review (
        action_id UUID PRIMARY KEY,
        world_id TEXT NOT NULL,
        revision BIGINT NOT NULL CHECK(revision > 0),
        payload JSONB NOT NULL,
        FOREIGN KEY(action_id,world_id) REFERENCES agent.build_proposal(action_id,world_id),
        CHECK(jsonb_typeof(payload)='object' AND payload ?& ARRAY['schema','action_id','world_id','revision','state','markdown','markdown_sha256','reservation_sha256']),
        CHECK(payload->>'schema'='dmb_build_proposal_review_v1'),
        CHECK(payload->>'action_id'=action_id::text),
        CHECK(payload->>'world_id'=world_id),
        CHECK((payload->>'revision')::bigint=revision)
    )""")


def downgrade():
    if (
        op.get_bind()
        .exec_driver_sql("SELECT EXISTS(SELECT 1 FROM agent.build_proposal_review)")
        .scalar_one()
    ):
        raise RuntimeError("Refusing to discard retained author review")
    op.execute("DROP TABLE agent.build_proposal_review")

    op.execute(
        "ALTER TABLE agent.build_proposal DROP CONSTRAINT build_proposal_action_world"
    )
