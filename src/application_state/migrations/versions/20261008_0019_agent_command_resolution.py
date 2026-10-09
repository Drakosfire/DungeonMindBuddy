"""Immutable request-bound reset resolution records and retirement fences."""
from alembic import op

revision = "20261008_0019"
down_revision = "20261007_0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE agent.command_resolution (
            world_id TEXT NOT NULL REFERENCES agent.world_state(world_id) ON DELETE RESTRICT,
            resolution_operation_id UUID NOT NULL,
            original_command_id UUID NOT NULL,
            original_request_fingerprint TEXT NOT NULL CHECK (original_request_fingerprint ~ '^[0-9a-f]{64}$'),
            resolution_request_fingerprint TEXT NOT NULL CHECK (resolution_request_fingerprint ~ '^[0-9a-f]{64}$'),
            outcome TEXT NOT NULL CHECK (outcome IN ('confirmed', 'retired', 'submitted_binding_blocked')),
            occupied_command_id UUID NULL,
            record JSONB NOT NULL CHECK (jsonb_typeof(record) = 'object'),
            PRIMARY KEY (world_id, resolution_operation_id),
            FOREIGN KEY (world_id, occupied_command_id) REFERENCES agent.command_receipt(world_id, command_id) ON DELETE RESTRICT,
            CHECK ((outcome = 'retired' AND occupied_command_id IS NULL) OR
                (outcome <> 'retired' AND occupied_command_id IS NOT NULL AND occupied_command_id = original_command_id)),
            CHECK (record ?& ARRAY['schema','request','original_command_kind','original_request_fingerprint',
                'resolution_request_fingerprint','observed_pointer','outcome','actor','recorded_at',
                'record_serializer_version','confirmed_receipt','occupied_receipt','retirement_operation_id','record_sha256']),
            CHECK (jsonb_typeof(record->'request') = 'object'),
            CHECK ((record->'request') ?& ARRAY['schema','resolution_operation_id','original_command',
                'expected_current_pointer_revision','expected_current_active_conversation_id']),
            CHECK (jsonb_typeof(record->'request'->'original_command') = 'object'),
            CHECK ((record->'request'->'original_command') ?& ARRAY['world_id','command_id',
                'expected_pointer_revision','expected_active_conversation_id']),
            CHECK (record->>'schema' = 'dmb_agent_new_conversation_resolution_record_v1'),
            CHECK (record->'request'->'original_command'->>'world_id' = world_id),
            CHECK ((record->'request'->'original_command'->>'command_id')::uuid = original_command_id),
            CHECK (record->>'outcome' = outcome),
            CHECK ((record->'request'->>'resolution_operation_id')::uuid = resolution_operation_id),
            CHECK (record->>'original_request_fingerprint' = original_request_fingerprint),
            CHECK (record->>'resolution_request_fingerprint' = resolution_request_fingerprint)
        )
    """)
    op.execute("CREATE UNIQUE INDEX agent_command_retirement_fence ON agent.command_resolution(world_id, original_command_id) WHERE outcome = 'retired'")
    op.execute("""
        CREATE FUNCTION agent.reject_command_resolution_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN RAISE EXCEPTION 'terminal command resolution records are immutable'; END $$;
        CREATE TRIGGER command_resolution_immutable BEFORE UPDATE OR DELETE ON agent.command_resolution
            FOR EACH ROW EXECUTE FUNCTION agent.reject_command_resolution_mutation();
        CREATE FUNCTION agent.protect_resolved_command_receipt() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF EXISTS (SELECT 1 FROM agent.command_resolution WHERE world_id=OLD.world_id AND occupied_command_id=OLD.command_id) THEN
                RAISE EXCEPTION 'occupied command receipt is immutable while terminal proof is retained';
            END IF;
            IF TG_OP = 'DELETE' THEN RETURN OLD; ELSE RETURN NEW; END IF;
        END $$;
        CREATE TRIGGER resolved_command_receipt_immutable BEFORE UPDATE OR DELETE ON agent.command_receipt
            FOR EACH ROW EXECUTE FUNCTION agent.protect_resolved_command_receipt();
    """)


def downgrade() -> None:
    op.execute("""
        LOCK TABLE agent.command_resolution IN ACCESS EXCLUSIVE MODE;
        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM agent.command_resolution) THEN
                RAISE EXCEPTION 'terminal command resolution records must be retained; downgrade refused';
            END IF;
        END $$;
        DROP TRIGGER resolved_command_receipt_immutable ON agent.command_receipt;
        DROP FUNCTION agent.protect_resolved_command_receipt();
        DROP TABLE agent.command_resolution;
        DROP FUNCTION agent.reject_command_resolution_mutation();
    """)
