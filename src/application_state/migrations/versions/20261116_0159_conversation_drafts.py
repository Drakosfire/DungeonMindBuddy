"""Store assistant draft edits independently of the delivered conversation."""

from alembic import op

revision = "20261116_0159"
down_revision = "20261115_0158"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE agent.conversation_draft_revision (
            world_id text NOT NULL,
            conversation_id uuid NOT NULL,
            turn_id uuid NOT NULL,
            revision bigint NOT NULL CHECK (revision > 0),
            markdown text NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (turn_id, revision),
            FOREIGN KEY (turn_id, world_id, conversation_id)
                REFERENCES agent.turn(turn_id, world_id, conversation_id)
                ON DELETE RESTRICT
        )
    """)


def downgrade():
    op.execute("""
        DO $$
        BEGIN
            LOCK TABLE agent.conversation_draft_revision IN ACCESS EXCLUSIVE MODE;
            IF EXISTS (SELECT 1 FROM agent.conversation_draft_revision) THEN
                RAISE EXCEPTION 'Downgrade would discard conversation draft revisions';
            END IF;
        END
        $$;
    """)
    op.drop_table("conversation_draft_revision", schema="agent")
