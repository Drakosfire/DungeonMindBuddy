"""ingest.run canonical ExtractionRun authority

Revision ID: 20260902_0005
Revises: 20260825_0004
Create Date: 2026-09-02

"""

from __future__ import annotations

from alembic import op

revision = "20260902_0005"
down_revision = "20260825_0004"
branch_labels = None
depends_on = None

_STATUS_VALUES = (
    "draft",
    "prepared",
    "extracted",
    "validated",
    "reviewable",
    "promoted",
    "rejected",
    "incomplete",
    "failed",
    "superseded",
)


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS ingest")
    status_list = ", ".join(f"'{value}'" for value in _STATUS_VALUES)
    op.execute(
        f"""
        CREATE TABLE ingest.run (
            run_id TEXT PRIMARY KEY,
            schema_version TEXT NOT NULL,
            record_version TEXT NOT NULL,
            source_artifact_id TEXT NOT NULL,
            source_domain TEXT NOT NULL,
            status TEXT NOT NULL CHECK (status IN ({status_list})),
            revision INTEGER NOT NULL CHECK (revision >= 1),
            campaign_id TEXT NULL,
            session_id TEXT NULL,
            profile_id TEXT NULL,
            components JSONB NOT NULL,
            diagnostics JSONB NOT NULL,
            lineage JSONB NOT NULL,
            superseded_by_run_id TEXT NULL,
            supersedes_run_id TEXT NULL,
            created_at TIMESTAMPTZ NULL,
            updated_at TIMESTAMPTZ NULL,
            CONSTRAINT ingest_run_superseded_by_not_self
                CHECK (superseded_by_run_id IS DISTINCT FROM run_id),
            CONSTRAINT ingest_run_supersedes_not_self
                CHECK (supersedes_run_id IS DISTINCT FROM run_id),
            CONSTRAINT ingest_run_superseded_by_fk
                FOREIGN KEY (superseded_by_run_id)
                REFERENCES ingest.run (run_id)
                DEFERRABLE INITIALLY DEFERRED,
            CONSTRAINT ingest_run_supersedes_fk
                FOREIGN KEY (supersedes_run_id)
                REFERENCES ingest.run (run_id)
                DEFERRABLE INITIALLY DEFERRED
        )
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX ingest_run_unique_successor
            ON ingest.run (supersedes_run_id)
            WHERE supersedes_run_id IS NOT NULL
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX ingest_run_unique_predecessor_claim
            ON ingest.run (superseded_by_run_id)
            WHERE superseded_by_run_id IS NOT NULL
        """
    )
    op.execute(
        """
        CREATE INDEX ingest_run_source_artifact
            ON ingest.run (source_artifact_id)
        """
    )
    op.execute(
        """
        CREATE INDEX ingest_run_campaign_session_updated
            ON ingest.run (campaign_id, session_id, updated_at)
        """
    )
    op.execute(
        """
        CREATE INDEX ingest_run_status
            ON ingest.run (status)
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS ingest.run")
    op.execute("DROP SCHEMA IF EXISTS ingest")
