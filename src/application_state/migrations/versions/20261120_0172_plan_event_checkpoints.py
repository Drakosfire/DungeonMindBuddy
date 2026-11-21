"""Store the ordered suffix of an open readonly Plan session."""

from alembic import op

revision = "20261120_0172"
down_revision = "20261120_0171"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE agent.plan_execution_checkpoint (
            turn_id uuid PRIMARY KEY REFERENCES agent.turn(turn_id) ON DELETE CASCADE,
            attempt integer NOT NULL CHECK (attempt > 0),
            base_revision bigint NOT NULL CHECK (base_revision > 0),
            revision bigint NOT NULL CHECK (revision >= base_revision),
            first_sequence integer NOT NULL CHECK (first_sequence >= 0),
            next_sequence integer NOT NULL CHECK (next_sequence >= first_sequence),
            prefix_sha256 text NOT NULL CHECK (prefix_sha256 ~ '^[a-f0-9]{64}$'),
            UNIQUE (turn_id, attempt)
        )
    """)
    op.execute("""
        CREATE TABLE agent.plan_execution_checkpoint_group (
            turn_id uuid NOT NULL,
            attempt integer NOT NULL,
            first_sequence integer NOT NULL CHECK (first_sequence >= 0),
            after_sequence integer NOT NULL CHECK (after_sequence > first_sequence),
            append_revision bigint NOT NULL CHECK (append_revision > 0),
            events jsonb NOT NULL,
            events_sha256 text NOT NULL CHECK (events_sha256 ~ '^[a-f0-9]{64}$'),
            PRIMARY KEY (turn_id, attempt, first_sequence),
            UNIQUE (turn_id, attempt, append_revision),
            FOREIGN KEY (turn_id, attempt)
                REFERENCES agent.plan_execution_checkpoint(turn_id, attempt) ON DELETE CASCADE,
            CHECK (CASE WHEN jsonb_typeof(events) = 'array'
                 THEN jsonb_array_length(events) = after_sequence - first_sequence ELSE false END)
        )
    """)


def downgrade():
    raise RuntimeError("Use forward recovery to materialize open Plan checkpoints before removal.")
