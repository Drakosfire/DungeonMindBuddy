"""Add optional bounded per-attempt context trace observations."""

from alembic import op

revision = "20261013_0022"
down_revision = "20261012_0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE agent.turn_context_trace (
            turn_id UUID NOT NULL REFERENCES agent.turn(turn_id) ON DELETE RESTRICT,
            attempt INTEGER NOT NULL CHECK (attempt BETWEEN 1 AND 2147483647),
            trace_id UUID NOT NULL UNIQUE,
            payload JSONB NOT NULL,
            PRIMARY KEY (turn_id, attempt),
            CHECK (jsonb_typeof(payload) = 'object'
                AND payload->>'schema' = 'dmb_turn_context_trace_v1'
                AND payload->>'turn_id' = turn_id::text
                AND payload->>'trace_id' = trace_id::text
                AND jsonb_typeof(payload->'attempt') = 'number'
                AND payload->>'attempt' = attempt::text
                AND jsonb_typeof(payload->'world_id') = 'string'
                AND jsonb_typeof(payload->'conversation_id') = 'string'
                AND CASE WHEN jsonb_typeof(payload->'execution_start_sequence') = 'number'
                    AND payload->>'execution_start_sequence' ~ '^(0|[1-9][0-9]{0,3})$'
                    THEN (payload->>'execution_start_sequence')::integer BETWEEN 0 AND 2048
                    ELSE FALSE END
                AND jsonb_typeof(payload->'observations') = 'array'
                AND jsonb_array_length(payload->'observations') <= 2048
                AND payload->>'capture_status' IN ('recording', 'complete', 'incomplete')
                AND octet_length(payload::text) <= 1048576)
        )
    """)


def downgrade() -> None:
    if op.get_bind().exec_driver_sql(
        "SELECT EXISTS (SELECT 1 FROM agent.turn_context_trace)"
    ).scalar_one():
        raise RuntimeError("refusing to discard recorded context traces")
    op.execute("DROP TABLE agent.turn_context_trace")
