"""play run and sealed run_manifest

Revision ID: 20260825_0003
Revises: 20260825_0002
Create Date: 2026-08-25

"""

from __future__ import annotations

from alembic import op

revision = "20260825_0003"
down_revision = "20260825_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS play")
    op.execute(
        """
        CREATE TABLE play.run (
            run_id UUID PRIMARY KEY,
            campaign_id TEXT NOT NULL,
            playable_work_object_id UUID NOT NULL,
            playable_revision_n INTEGER NOT NULL,
            playable_work_revision_id UUID NOT NULL,
            playable_content_sha256 TEXT NOT NULL,
            run_revision INTEGER NOT NULL,
            progress JSONB NOT NULL,
            rebased_from_run_revision INTEGER NULL,
            created_at TIMESTAMPTZ NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL
        )
        """
    )
    op.execute(
        """
        CREATE INDEX play_run_campaign_created
            ON play.run (campaign_id, created_at DESC, run_id)
        """
    )
    op.execute(
        """
        CREATE INDEX play_run_playable
            ON play.run (playable_work_object_id)
        """
    )
    op.execute(
        """
        CREATE TABLE play.run_manifest (
            run_id UUID PRIMARY KEY
                REFERENCES play.run (run_id),
            playable_work_object_id UUID NOT NULL,
            playable_revision_n INTEGER NOT NULL,
            playable_work_revision_id UUID NOT NULL,
            playable_content_sha256 TEXT NOT NULL,
            manifest JSONB NOT NULL,
            sealed_at TIMESTAMPTZ NOT NULL
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS play.run_manifest")
    op.execute("DROP TABLE IF EXISTS play.run")
    op.execute("DROP SCHEMA IF EXISTS play")
