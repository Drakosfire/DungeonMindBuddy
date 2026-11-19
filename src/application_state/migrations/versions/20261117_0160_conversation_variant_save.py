"""Bind a confirmed statblock create to an immutable conversation draft revision."""

from alembic import op

revision = "20261117_0160"
down_revision = "20261116_0159"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE agent.conversation_variant_review (
            review_id uuid PRIMARY KEY,
            turn_id uuid NOT NULL,
            revision bigint NOT NULL,
            definition jsonb NOT NULL,
            base_locator jsonb NOT NULL,
            FOREIGN KEY (turn_id, revision)
                REFERENCES agent.conversation_draft_revision(turn_id, revision)
                ON DELETE RESTRICT
        )
    """)
    op.execute("""
        CREATE TABLE agent.conversation_variant_save (
            turn_id uuid NOT NULL,
            revision bigint NOT NULL,
            create_request jsonb NOT NULL,
            receipt jsonb,
            PRIMARY KEY (turn_id, revision),
            FOREIGN KEY (turn_id, revision)
                REFERENCES agent.conversation_draft_revision(turn_id, revision)
                ON DELETE RESTRICT
        )
    """)


def downgrade():
    op.execute("""
        DO $$
        BEGIN
            LOCK TABLE agent.conversation_variant_save, agent.conversation_variant_review IN ACCESS EXCLUSIVE MODE;
            IF EXISTS (SELECT 1 FROM agent.conversation_variant_save)
               OR EXISTS (SELECT 1 FROM agent.conversation_variant_review) THEN
                RAISE EXCEPTION 'Downgrade would discard confirmed variant saves';
            END IF;
        END
        $$;
    """)
    op.drop_table("conversation_variant_save", schema="agent")
    op.drop_table("conversation_variant_review", schema="agent")
