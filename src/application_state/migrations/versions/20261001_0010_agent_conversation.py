"""add typed World-scoped Agent conversations, turns, drafts and receipts

Revision ID: 20261001_0010
Revises: 20260930_0009
Create Date: 2026-10-01

"""

from __future__ import annotations

from alembic import op

revision = "20261001_0010"
down_revision = "20260930_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS agent")
    op.execute(
        """
        CREATE TABLE agent.conversation (
            conversation_id UUID PRIMARY KEY,
            world_id TEXT NOT NULL CHECK (btrim(world_id) <> ''),
            status TEXT NOT NULL CHECK (status IN ('active', 'archived')),
            revision BIGINT NOT NULL CHECK (revision > 0),
            next_turn_sequence BIGINT NOT NULL CHECK (next_turn_sequence > 0),
            created_at TIMESTAMPTZ NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL,
            archived_at TIMESTAMPTZ NULL,
            CONSTRAINT agent_conversation_status_time_check CHECK (
                (status = 'active' AND archived_at IS NULL)
                OR (status = 'archived' AND archived_at IS NOT NULL)
            ),
            CONSTRAINT agent_conversation_id_world_unique UNIQUE (conversation_id, world_id)
        )
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX agent_conversation_one_active_per_world
            ON agent.conversation (world_id)
            WHERE status = 'active'
        """
    )
    op.execute(
        """
        CREATE TABLE agent.world_state (
            world_id TEXT PRIMARY KEY CHECK (btrim(world_id) <> ''),
            active_conversation_id UUID NULL,
            pointer_revision BIGINT NOT NULL DEFAULT 0 CHECK (pointer_revision >= 0),
            updated_at TIMESTAMPTZ NOT NULL,
            CONSTRAINT agent_world_active_conversation_fk
                FOREIGN KEY (active_conversation_id, world_id)
                REFERENCES agent.conversation (conversation_id, world_id)
                DEFERRABLE INITIALLY DEFERRED
        )
        """
    )
    op.execute(
        """
        CREATE TABLE agent.command_receipt (
            world_id TEXT NOT NULL REFERENCES agent.world_state(world_id) ON DELETE RESTRICT,
            command_id UUID NOT NULL,
            command_kind TEXT NOT NULL CHECK (command_kind IN ('new', 'archive', 'reopen')),
            request_fingerprint TEXT NOT NULL CHECK (request_fingerprint ~ '^[0-9a-f]{64}$'),
            expected_pointer_revision BIGINT NOT NULL CHECK (expected_pointer_revision >= 0),
            expected_active_conversation_id UUID NULL,
            conversation_id UUID NOT NULL,
            result_active_conversation_id UUID NULL,
            result_pointer_revision BIGINT NOT NULL CHECK (result_pointer_revision >= 0),
            recorded_at TIMESTAMPTZ NOT NULL,
            PRIMARY KEY (world_id, command_id),
            FOREIGN KEY (conversation_id, world_id)
                REFERENCES agent.conversation(conversation_id, world_id) ON DELETE RESTRICT,
            FOREIGN KEY (expected_active_conversation_id, world_id)
                REFERENCES agent.conversation(conversation_id, world_id) ON DELETE RESTRICT,
            FOREIGN KEY (result_active_conversation_id, world_id)
                REFERENCES agent.conversation(conversation_id, world_id) ON DELETE RESTRICT
        )
        """
    )
    op.execute(
        """
        CREATE TABLE agent.turn (
            turn_id UUID PRIMARY KEY,
            conversation_id UUID NOT NULL,
            world_id TEXT NOT NULL,
            idempotency_key UUID NOT NULL,
            sequence BIGINT NOT NULL CHECK (sequence > 0),
            revision BIGINT NOT NULL CHECK (revision > 0),
            status TEXT NOT NULL CHECK (
                status IN ('accepted', 'running', 'completed', 'failed', 'interrupted')
            ),
            request_fingerprint TEXT NOT NULL CHECK (request_fingerprint ~ '^[0-9a-f]{64}$'),
            user_text TEXT NOT NULL CHECK (btrim(user_text) <> ''),
            assistant_text TEXT NULL,
            failure_code TEXT NULL,
            surface_resolution TEXT NOT NULL CHECK (
                surface_resolution IN ('resolved', 'absent', 'unresolved', 'unavailable')
            ),
            surface_id TEXT NULL,
            attempt INTEGER NOT NULL DEFAULT 0 CHECK (attempt >= 0),
            accepted_at TIMESTAMPTZ NOT NULL,
            completed_at TIMESTAMPTZ NULL,
            updated_at TIMESTAMPTZ NOT NULL,
            FOREIGN KEY (conversation_id, world_id)
                REFERENCES agent.conversation(conversation_id, world_id) ON DELETE RESTRICT,
            UNIQUE (conversation_id, idempotency_key),
            UNIQUE (conversation_id, sequence),
            CHECK (
                (surface_resolution = 'resolved' AND surface_id IS NOT NULL AND btrim(surface_id) <> '')
                OR (surface_resolution <> 'resolved' AND (surface_id IS NULL OR btrim(surface_id) <> ''))
            ),
            CHECK (
                (status = 'completed' AND assistant_text IS NOT NULL AND btrim(assistant_text) <> ''
                    AND failure_code IS NULL AND completed_at IS NOT NULL)
                OR (status IN ('accepted', 'running') AND assistant_text IS NULL
                    AND failure_code IS NULL AND completed_at IS NULL)
                OR (status IN ('failed', 'interrupted') AND assistant_text IS NULL
                    AND failure_code IS NOT NULL AND completed_at IS NOT NULL)
            )
        )
        """
    )
    op.execute(
        """
        CREATE TABLE agent.turn_reference (
            turn_id UUID NOT NULL REFERENCES agent.turn(turn_id) ON DELETE CASCADE,
            reference_role TEXT NOT NULL CHECK (
                reference_role IN ('primary', 'supporting', 'selected')
            ),
            ordinal SMALLINT NOT NULL CHECK (ordinal >= 0),
            resolution TEXT NOT NULL CHECK (
                resolution IN ('resolved', 'absent', 'unresolved', 'unavailable')
            ),
            kind TEXT NULL,
            object_id TEXT NULL,
            revision TEXT NULL,
            content_sha256 TEXT NULL CHECK (
                content_sha256 IS NULL OR content_sha256 ~ '^[0-9a-fA-F]{64}$'
            ),
            PRIMARY KEY (turn_id, reference_role, ordinal),
            CHECK (
                (resolution = 'resolved' AND kind IS NOT NULL AND btrim(kind) <> ''
                    AND object_id IS NOT NULL AND btrim(object_id) <> '')
                OR (resolution = 'absent' AND kind IS NULL AND object_id IS NULL
                    AND revision IS NULL AND content_sha256 IS NULL)
                OR (resolution IN ('unresolved', 'unavailable'))
            ),
            CHECK (reference_role <> 'primary' OR ordinal = 0),
            CHECK (reference_role <> 'selected' OR ordinal = 0)
        )
        """
    )
    op.execute(
        "CREATE UNIQUE INDEX agent_turn_one_primary_reference ON agent.turn_reference(turn_id) WHERE reference_role = 'primary'"
    )
    op.execute(
        "CREATE UNIQUE INDEX agent_turn_one_selected_reference ON agent.turn_reference(turn_id) WHERE reference_role = 'selected'"
    )
    op.execute(
        """
        CREATE TABLE agent.composer_draft (
            draft_id UUID PRIMARY KEY,
            conversation_id UUID NOT NULL,
            world_id TEXT NOT NULL,
            revision BIGINT NOT NULL CHECK (revision > 0),
            body TEXT NOT NULL,
            request_fingerprint TEXT NOT NULL CHECK (request_fingerprint ~ '^[0-9a-f]{64}$'),
            surface_resolution TEXT NOT NULL CHECK (
                surface_resolution IN ('resolved', 'absent', 'unresolved', 'unavailable')
            ),
            surface_id TEXT NULL,
            primary_resolution TEXT NOT NULL CHECK (
                primary_resolution IN ('resolved', 'absent', 'unresolved', 'unavailable')
            ),
            primary_kind TEXT NULL,
            primary_object_id TEXT NULL,
            primary_revision TEXT NULL,
            primary_content_sha256 TEXT NULL CHECK (
                primary_content_sha256 IS NULL OR primary_content_sha256 ~ '^[0-9a-fA-F]{64}$'
            ),
            selected_resolution TEXT NOT NULL CHECK (
                selected_resolution IN ('resolved', 'absent', 'unresolved', 'unavailable')
            ),
            selected_kind TEXT NULL,
            selected_object_id TEXT NULL,
            selected_revision TEXT NULL,
            selected_content_sha256 TEXT NULL CHECK (
                selected_content_sha256 IS NULL OR selected_content_sha256 ~ '^[0-9a-fA-F]{64}$'
            ),
            source_fingerprint TEXT NOT NULL CHECK (source_fingerprint ~ '^[0-9a-f]{64}$'),
            retired_at TIMESTAMPTZ NULL,
            created_at TIMESTAMPTZ NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL,
            FOREIGN KEY (conversation_id, world_id)
                REFERENCES agent.conversation(conversation_id, world_id) ON DELETE RESTRICT,
            CHECK (
                (surface_resolution = 'resolved' AND surface_id IS NOT NULL AND btrim(surface_id) <> '')
                OR (surface_resolution <> 'resolved' AND (surface_id IS NULL OR btrim(surface_id) <> ''))
            ),
            CHECK (
                (primary_resolution = 'resolved' AND primary_kind IS NOT NULL
                    AND btrim(primary_kind) <> '' AND primary_object_id IS NOT NULL
                    AND btrim(primary_object_id) <> '')
                OR (primary_resolution = 'absent' AND primary_kind IS NULL
                    AND primary_object_id IS NULL AND primary_revision IS NULL
                    AND primary_content_sha256 IS NULL)
                OR (primary_resolution IN ('unresolved', 'unavailable'))
            ),
            CHECK (
                (selected_resolution = 'resolved' AND selected_kind IS NOT NULL
                    AND btrim(selected_kind) <> '' AND selected_object_id IS NOT NULL
                    AND btrim(selected_object_id) <> '')
                OR (selected_resolution = 'absent' AND selected_kind IS NULL
                    AND selected_object_id IS NULL AND selected_revision IS NULL
                    AND selected_content_sha256 IS NULL)
                OR (selected_resolution IN ('unresolved', 'unavailable'))
            )
        )
        """
    )
    op.execute(
        """
        CREATE TABLE agent.draft_reference (
            draft_id UUID NOT NULL REFERENCES agent.composer_draft(draft_id) ON DELETE CASCADE,
            ordinal SMALLINT NOT NULL CHECK (ordinal >= 0),
            resolution TEXT NOT NULL CHECK (
                resolution IN ('resolved', 'absent', 'unresolved', 'unavailable')
            ),
            kind TEXT NULL,
            object_id TEXT NULL,
            revision TEXT NULL,
            content_sha256 TEXT NULL CHECK (
                content_sha256 IS NULL OR content_sha256 ~ '^[0-9a-fA-F]{64}$'
            ),
            PRIMARY KEY (draft_id, ordinal),
            CHECK (
                (resolution = 'resolved' AND kind IS NOT NULL AND btrim(kind) <> ''
                    AND object_id IS NOT NULL AND btrim(object_id) <> '')
                OR (resolution = 'absent' AND kind IS NULL AND object_id IS NULL
                    AND revision IS NULL AND content_sha256 IS NULL)
                OR (resolution IN ('unresolved', 'unavailable'))
            )
        )
        """
    )
    op.execute(
        """
        CREATE TABLE agent.import_receipt (
            world_id TEXT NOT NULL REFERENCES agent.world_state(world_id) ON DELETE RESTRICT,
            source_import_key TEXT NOT NULL CHECK (btrim(source_import_key) <> ''),
            source_thread_id TEXT NOT NULL CHECK (btrim(source_thread_id) <> ''),
            request_fingerprint TEXT NOT NULL CHECK (request_fingerprint ~ '^[0-9a-f]{64}$'),
            conversation_id UUID NOT NULL,
            active_conversation_id UUID NULL,
            pointer_revision BIGINT NOT NULL CHECK (pointer_revision >= 0),
            imported_turn_count INTEGER NOT NULL CHECK (imported_turn_count > 0 AND imported_turn_count <= 20),
            recorded_at TIMESTAMPTZ NOT NULL,
            PRIMARY KEY (world_id, source_import_key),
            FOREIGN KEY (conversation_id, world_id)
                REFERENCES agent.conversation(conversation_id, world_id) ON DELETE RESTRICT,
            FOREIGN KEY (active_conversation_id, world_id)
                REFERENCES agent.conversation(conversation_id, world_id) ON DELETE RESTRICT
        )
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM agent.turn)
                OR EXISTS (SELECT 1 FROM agent.composer_draft)
                OR EXISTS (SELECT 1 FROM agent.command_receipt)
                OR EXISTS (SELECT 1 FROM agent.import_receipt)
                OR EXISTS (SELECT 1 FROM agent.conversation)
                OR EXISTS (SELECT 1 FROM agent.world_state)
            THEN
                RAISE EXCEPTION
                    'cannot downgrade while Agent conversation product state exists';
            END IF;
        END; $$
        """
    )
    op.execute("DROP TABLE IF EXISTS agent.import_receipt")
    op.execute("DROP TABLE IF EXISTS agent.draft_reference")
    op.execute("DROP TABLE IF EXISTS agent.composer_draft")
    op.execute("DROP INDEX IF EXISTS agent.agent_turn_one_selected_reference")
    op.execute("DROP INDEX IF EXISTS agent.agent_turn_one_primary_reference")
    op.execute("DROP TABLE IF EXISTS agent.turn_reference")
    op.execute("DROP TABLE IF EXISTS agent.turn")
    op.execute("DROP TABLE IF EXISTS agent.command_receipt")
    op.execute("DROP TABLE IF EXISTS agent.world_state")
    op.execute("DROP TABLE IF EXISTS agent.conversation")
    op.execute("DROP SCHEMA IF EXISTS agent")
