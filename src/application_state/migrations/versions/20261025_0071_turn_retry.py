"""Immutable, scope-bound lineage for explicit ordinary Build retries."""

from alembic import op

revision = "20261025_0071"
down_revision = "20261025_0070"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "ALTER TABLE agent.turn ADD CONSTRAINT turn_retry_scope UNIQUE(turn_id,world_id,conversation_id)"
    )
    op.execute("""CREATE TABLE agent.turn_retry (
        predecessor_id UUID PRIMARY KEY,
        successor_id UUID NOT NULL UNIQUE,
        root_id UUID NOT NULL,
        world_id TEXT NOT NULL,
        conversation_id UUID NOT NULL,
        predecessor_revision BIGINT NOT NULL CHECK(predecessor_revision>0),
        ordinal BIGINT NOT NULL CHECK(ordinal>0),
        FOREIGN KEY(predecessor_id,world_id,conversation_id) REFERENCES agent.turn(turn_id,world_id,conversation_id),
        FOREIGN KEY(successor_id,world_id,conversation_id) REFERENCES agent.turn(turn_id,world_id,conversation_id),
        FOREIGN KEY(root_id,world_id,conversation_id) REFERENCES agent.turn(turn_id,world_id,conversation_id),
        CHECK(predecessor_id<>successor_id), CHECK(root_id<>successor_id),
        UNIQUE(root_id,ordinal))""")
    op.execute("""CREATE FUNCTION agent.validate_turn_retry() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE p agent.turn; s agent.turn; incoming agent.turn_retry; BEGIN
        IF TG_OP<>'INSERT' THEN RAISE EXCEPTION 'Retry lineage is immutable'; END IF;
        SELECT * INTO p FROM agent.turn WHERE turn_id=NEW.predecessor_id;
        SELECT * INTO s FROM agent.turn WHERE turn_id=NEW.successor_id;
        SELECT * INTO incoming FROM agent.turn_retry WHERE successor_id=NEW.predecessor_id;
        IF p.status NOT IN ('failed','interrupted') OR p.completion IS NOT NULL
           OR s.status<>'accepted' OR s.attempt<>0 OR p.revision<>NEW.predecessor_revision
           OR p.sequence>=s.sequence OR p.user_text<>s.user_text
           OR p.surface_id<>'build' OR s.surface_id<>'build'
           OR NEW.root_id<>COALESCE(incoming.root_id,p.turn_id)
           OR NEW.ordinal<>COALESCE(incoming.ordinal,0)+1 THEN
            RAISE EXCEPTION 'Retry lineage differs from its predecessor';
        END IF;
        RETURN NEW;
    END $$""")
    op.execute("""CREATE TRIGGER immutable_turn_retry BEFORE INSERT OR UPDATE OR DELETE ON agent.turn_retry
        FOR EACH ROW EXECUTE FUNCTION agent.validate_turn_retry()""")


def downgrade():
    op.execute("LOCK TABLE agent.turn_retry IN ACCESS EXCLUSIVE MODE")
    if (
        op.get_bind()
        .exec_driver_sql("SELECT EXISTS(SELECT 1 FROM agent.turn_retry)")
        .scalar_one()
    ):
        raise RuntimeError("Retained retry lineage requires recovery forward")
    op.execute("DROP TABLE agent.turn_retry")
    op.execute("DROP FUNCTION agent.validate_turn_retry()")
    op.execute("ALTER TABLE agent.turn DROP CONSTRAINT turn_retry_scope")
