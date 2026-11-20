"""Durable author names, independent of turn/pointer concurrency revisions."""

from alembic import op

revision = "20261024_0062"
down_revision = "20261024_0061"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""CREATE TABLE agent.conversation_name (
        conversation_id UUID NOT NULL, world_id TEXT NOT NULL,
        title TEXT NOT NULL CHECK (title=btrim(title) AND char_length(title) BETWEEN 1 AND 160 AND title !~ '[[:cntrl:]]'),
        revision BIGINT NOT NULL CHECK (revision>0), updated_at TIMESTAMPTZ NOT NULL,
        PRIMARY KEY(conversation_id,world_id),
        FOREIGN KEY(conversation_id,world_id) REFERENCES agent.conversation(conversation_id,world_id)
    )""")


def downgrade():
    op.execute("LOCK TABLE agent.conversation_name IN ACCESS EXCLUSIVE MODE")
    if (
        op.get_bind()
        .exec_driver_sql("SELECT EXISTS(SELECT 1 FROM agent.conversation_name)")
        .scalar_one()
    ):
        raise RuntimeError("Retained conversation names require recovery forward")
    op.execute("DROP TABLE agent.conversation_name")
