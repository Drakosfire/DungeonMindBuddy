"""content work object / revision / working copy

Revision ID: 20260825_0001
Revises:
Create Date: 2026-08-25

"""

from __future__ import annotations

from alembic import op

revision = "20260825_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS content")
    op.execute(
        """
        CREATE TABLE content.work_object (
            work_object_id UUID PRIMARY KEY,
            kind TEXT NOT NULL CHECK (kind = 'plan'),
            campaign_id TEXT NOT NULL,
            world_id TEXT NULL,
            title TEXT NOT NULL,
            target_session INTEGER NULL,
            target_relpath TEXT NULL,
            status TEXT NOT NULL CHECK (status IN ('active', 'discarded')),
            current_revision_id UUID NULL,
            object_revision INTEGER NOT NULL,
            created_at TIMESTAMPTZ NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL
        )
        """
    )
    op.execute(
        """
        CREATE TABLE content.work_revision (
            work_revision_id UUID PRIMARY KEY,
            work_object_id UUID NOT NULL
                REFERENCES content.work_object (work_object_id),
            revision_n INTEGER NOT NULL,
            markdown TEXT NOT NULL,
            content_sha256 TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL,
            UNIQUE (work_object_id, revision_n)
        )
        """
    )
    op.execute(
        """
        ALTER TABLE content.work_object
            ADD CONSTRAINT work_object_current_revision_fk
            FOREIGN KEY (current_revision_id)
            REFERENCES content.work_revision (work_revision_id)
        """
    )
    op.execute(
        """
        CREATE TABLE content.working_copy (
            work_object_id UUID PRIMARY KEY
                REFERENCES content.work_object (work_object_id),
            markdown TEXT NOT NULL,
            content_sha256 TEXT NOT NULL,
            base_revision_id UUID NULL
                REFERENCES content.work_revision (work_revision_id),
            working_copy_revision INTEGER NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS content.working_copy")
    op.execute(
        "ALTER TABLE content.work_object DROP CONSTRAINT IF EXISTS work_object_current_revision_fk"
    )
    op.execute("DROP TABLE IF EXISTS content.work_revision")
    op.execute("DROP TABLE IF EXISTS content.work_object")
    op.execute("DROP SCHEMA IF EXISTS content")
