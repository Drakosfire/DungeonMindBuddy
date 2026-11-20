"""Separate bounded Rules authority and an explicit mixed-answer discriminator."""
from alembic import op

revision = "20261020_0041"
down_revision = "20261019_0040"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE agent.turn ADD COLUMN answer_composition_kind TEXT NOT NULL DEFAULT 'base'")
    op.execute("""
        ALTER TABLE agent.turn ADD CONSTRAINT agent_turn_answer_composition_kind_check CHECK (
            answer_composition_kind IN ('base', 'rules_mixed_v1')
            AND (answer_composition_kind <> 'rules_mixed_v1' OR status = 'completed')
        )
    """)
    op.execute("""
        CREATE TABLE agent.turn_rules_execution (
            turn_id UUID NOT NULL REFERENCES agent.turn(turn_id) ON DELETE RESTRICT,
            product_attempt INTEGER NOT NULL CHECK (product_attempt >= 1),
            revision BIGINT NOT NULL CHECK (revision >= 1),
            payload JSONB NOT NULL,
            accepted_binding JSONB NULL,
            accepted_binding_sha256 TEXT NULL,
            PRIMARY KEY (turn_id, product_attempt),
            CONSTRAINT rules_execution_payload_check CHECK (COALESCE(
                jsonb_typeof(payload) = 'object'
                AND payload->>'schema' = 'dmb_rules_execution_v1'
                AND jsonb_typeof(payload->'scope') = 'object'
                AND payload->'scope'->>'turn_id' = turn_id::text
                AND payload->'scope'->>'product_attempt' = product_attempt::text
                AND payload->>'state' IN ('active', 'unused', 'accepted', 'failed')
                AND jsonb_typeof(payload->'events') = 'array'
                AND CASE WHEN jsonb_typeof(payload->'events') = 'array'
                    THEN jsonb_array_length(payload->'events') <= 256 ELSE FALSE END
                AND jsonb_typeof(payload->'supports') = 'object'
                AND jsonb_typeof(payload->'budget_use') = 'object'
                AND octet_length(payload::text) <= 327680, FALSE)),
            CONSTRAINT rules_execution_accepted_binding_check CHECK (
                (accepted_binding IS NULL AND accepted_binding_sha256 IS NULL
                    AND payload->>'state' <> 'accepted')
                OR COALESCE(
                    jsonb_typeof(accepted_binding) = 'object'
                    AND accepted_binding->>'schema' = 'dmb_rules_accepted_binding_v1'
                    AND accepted_binding->>'turn_id' = turn_id::text
                    AND accepted_binding->>'product_attempt' = product_attempt::text
                    AND payload->>'state' = 'accepted'
                    AND accepted_binding_sha256 ~ '^[a-f0-9]{64}$'
                    AND octet_length(accepted_binding::text) <= 40960, FALSE)
            )
        )
    """)


def downgrade() -> None:
    op.execute("LOCK TABLE agent.turn, agent.turn_rules_execution IN ACCESS EXCLUSIVE MODE")
    connection = op.get_bind()
    retained = connection.exec_driver_sql("""
        SELECT EXISTS(SELECT 1 FROM agent.turn_rules_execution)
            OR EXISTS(SELECT 1 FROM agent.turn WHERE answer_composition_kind = 'rules_mixed_v1')
    """).scalar_one()
    if retained:
        raise RuntimeError("refusing to discard retained Rules authority or mixed answers")
    op.execute("DROP TABLE agent.turn_rules_execution")
    op.execute("ALTER TABLE agent.turn DROP CONSTRAINT agent_turn_answer_composition_kind_check")
    op.execute("ALTER TABLE agent.turn DROP COLUMN answer_composition_kind")
