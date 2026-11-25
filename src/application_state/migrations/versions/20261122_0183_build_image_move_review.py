"""Persist typed Build image move Reviews under a forward reader fence."""

from alembic import op

revision = "20261122_0183"
down_revision = "20261122_0182"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE agent.build_image_move_review (
            action_id UUID PRIMARY KEY,
            world_id TEXT NOT NULL CHECK (btrim(world_id) <> ''),
            conversation_id UUID NOT NULL,
            revision BIGINT NOT NULL CHECK (revision > 0),
            payload JSONB NOT NULL,
            FOREIGN KEY (conversation_id, world_id)
                REFERENCES agent.conversation(conversation_id, world_id),
            CHECK (COALESCE(
                jsonb_typeof(payload) = 'object'
                AND octet_length(payload::text) <= 32768
                AND payload->>'schema' = 'dmb_build_image_move_review_v1'
                AND payload->>'action_id' = action_id::text
                AND payload->>'conversation_id' = conversation_id::text
                AND payload->'placement'->'basis'->>'world_id' = world_id
                AND (payload->>'revision')::bigint = revision
                AND payload->>'state' IN ('editing', 'claimed', 'saved'),
                FALSE))
        )
    """)
    op.execute("""
        CREATE INDEX build_image_move_review_conversation
        ON agent.build_image_move_review(world_id, conversation_id)
    """)


def downgrade():
    raise RuntimeError("Use forward recovery. Older Build readers cannot retain typed image move Reviews.")
