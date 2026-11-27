"""Keep historical conversation references independent of conversation content."""

from alembic import op

revision = "20261126_0214"
down_revision = "20261125_0213"
branch_labels = None
depends_on = None

_RECEIPT_REFERENCES = {
    "command_receipt": (
        "conversation_id",
        "expected_active_conversation_id",
        "result_active_conversation_id",
    ),
    "import_receipt": (
        "conversation_id",
        "active_conversation_id",
    ),
}


def upgrade() -> None:
    # Hold the source stable until the backfill and the insert trigger are in place.
    op.execute("LOCK TABLE agent.conversation IN SHARE ROW EXCLUSIVE MODE")
    op.execute("""
        CREATE TABLE agent.conversation_identity (
            conversation_id uuid PRIMARY KEY,
            world_id text NOT NULL,
            UNIQUE (conversation_id, world_id)
        );
        INSERT INTO agent.conversation_identity (conversation_id, world_id)
        SELECT conversation_id, world_id FROM agent.conversation;

        CREATE FUNCTION agent.record_conversation_identity() RETURNS trigger
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog AS $$
        BEGIN
            INSERT INTO agent.conversation_identity (conversation_id, world_id)
            VALUES (NEW.conversation_id, NEW.world_id);
            RETURN NEW;
        END;
        $$;
        REVOKE EXECUTE ON FUNCTION agent.record_conversation_identity() FROM PUBLIC;
        CREATE TRIGGER conversation_retain_identity
            AFTER INSERT ON agent.conversation
            FOR EACH ROW EXECUTE FUNCTION agent.record_conversation_identity();
    """)
    for table, columns in _RECEIPT_REFERENCES.items():
        for column in columns:
            # These are the default names of the five original inline FKs.
            foreign_key = f"{table}_{column}_world_id_fkey"
            op.execute(f"""
                ALTER TABLE agent.{table}
                    DROP CONSTRAINT {foreign_key},
                    ADD CONSTRAINT {foreign_key} FOREIGN KEY ({column}, world_id)
                    REFERENCES agent.conversation_identity (conversation_id, world_id)
                    ON DELETE RESTRICT
            """)

    op.execute("""
        ALTER TABLE agent.command_receipt
            DROP CONSTRAINT command_receipt_command_kind_check,
            ADD CONSTRAINT command_receipt_command_kind_check
                CHECK (command_kind IN ('new', 'archive', 'reopen', 'trash', 'restore', 'delete'));

        CREATE FUNCTION agent.drop_guest_conversation_identity() RETURNS trigger
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog AS $$
        BEGIN
            -- The expired-guest sweeper removes its receipts first.
            DELETE FROM agent.conversation_identity
            WHERE conversation_id = OLD.conversation_id AND world_id = OLD.world_id;
            RETURN OLD;
        END;
        $$;
        REVOKE EXECUTE ON FUNCTION agent.drop_guest_conversation_identity() FROM PUBLIC;
        CREATE TRIGGER guest_conversation_forget_identity
            AFTER DELETE ON agent.conversation
            FOR EACH ROW WHEN (OLD.world_id LIKE 'guest-%')
            EXECUTE FUNCTION agent.drop_guest_conversation_identity();
    """)


def downgrade() -> None:
    raise RuntimeError("Use forward recovery to preserve historical conversation identities.")
