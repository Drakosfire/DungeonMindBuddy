"""Durable Build Compose reservations with genuine workspace source basis."""
from alembic import op

revision = "20261016_0026"
down_revision = "20261016_0025"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE agent.build_proposal (
            action_id UUID PRIMARY KEY,
            world_id TEXT NOT NULL CHECK (btrim(world_id) <> ''),
            conversation_id UUID NOT NULL,
            idempotency_key UUID NOT NULL,
            revision BIGINT NOT NULL CHECK (revision > 0),
            payload JSONB NOT NULL,
            UNIQUE (world_id, idempotency_key),
            FOREIGN KEY (conversation_id, world_id) REFERENCES agent.conversation(conversation_id, world_id),
            CHECK (jsonb_typeof(payload) = 'object' AND octet_length(payload::text) <= 262144),
            CHECK (payload ?& ARRAY['schema_version','action_id','reservation','revision','state','request_fingerprint']),
            CHECK (payload->>'schema_version' = 'dmb_build_document_proposal_v1'),
            CHECK (payload->>'action_id' = action_id::text),
            CHECK (payload->'reservation'->'basis'->>'world_id' = world_id),
            CHECK (payload->'reservation'->>'conversation_id' = conversation_id::text),
            CHECK (payload->'reservation'->>'idempotency_key' = idempotency_key::text),
            CHECK ((payload->>'revision')::bigint = revision)
        )
    """)
    op.execute("CREATE INDEX build_proposal_conversation ON agent.build_proposal(world_id, conversation_id)")


def downgrade():
    if op.get_bind().exec_driver_sql("SELECT EXISTS(SELECT 1 FROM agent.build_proposal)").scalar_one():
        raise RuntimeError("refusing to discard retained Build proposal receipts")
    op.execute("DROP TABLE agent.build_proposal")
