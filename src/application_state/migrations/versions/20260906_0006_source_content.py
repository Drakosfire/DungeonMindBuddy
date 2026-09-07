"""durable source-owned immutable Markdown

Revision ID: 20260906_0006
Revises: 20260902_0005
Create Date: 2026-09-06

"""

from __future__ import annotations

from alembic import op

revision = "20260906_0006"
down_revision = "20260902_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS source")
    op.execute(
        """
        CREATE TABLE source.artifact (
            source_artifact_id TEXT PRIMARY KEY,
            source_domain TEXT NOT NULL,
            campaign_id TEXT NULL,
            session_id TEXT NULL,
            world_id TEXT NULL,
            created_at TIMESTAMPTZ NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL
        )
        """
    )
    op.execute(
        """
        CREATE TABLE source.revision (
            source_revision_id UUID PRIMARY KEY,
            source_artifact_id TEXT NOT NULL,
            content_sha256 TEXT NOT NULL,
            media_type TEXT NOT NULL,
            encoding TEXT NOT NULL,
            markdown TEXT NOT NULL,
            lineage JSONB NOT NULL,
            created_at TIMESTAMPTZ NOT NULL,
            CONSTRAINT source_revision_artifact_fk
                FOREIGN KEY (source_artifact_id)
                REFERENCES source.artifact (source_artifact_id)
                ON DELETE RESTRICT,
            CONSTRAINT source_revision_artifact_digest_unique
                UNIQUE (source_artifact_id, content_sha256),
            CONSTRAINT source_revision_markdown_nonempty
                CHECK (length(markdown) > 0)
        )
        """
    )
    op.execute(
        """
        CREATE INDEX source_revision_artifact
            ON source.revision (source_artifact_id, created_at)
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS source.revision")
    op.execute("DROP TABLE IF EXISTS source.artifact")
    op.execute("DROP SCHEMA IF EXISTS source")
