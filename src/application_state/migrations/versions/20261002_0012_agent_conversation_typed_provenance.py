"""add typed Agent surface and Content revision provenance

Revision ID: 20261002_0012
Revises: 20261001_0011
Create Date: 2026-10-02

"""

from __future__ import annotations

from alembic import op

revision = "20261002_0012"
down_revision = "20261001_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE agent.turn ADD COLUMN surface_instance_id TEXT NULL")
    op.execute(
        """
        ALTER TABLE agent.turn
        ADD CONSTRAINT agent_turn_surface_instance_check
        CHECK (
            surface_instance_id IS NULL
            OR (surface_resolution = 'resolved' AND btrim(surface_instance_id) <> '')
        )
        """
    )
    op.execute(
        "ALTER TABLE agent.composer_draft ADD COLUMN surface_instance_id TEXT NULL"
    )
    op.execute(
        """
        ALTER TABLE agent.composer_draft
        ADD CONSTRAINT agent_draft_surface_instance_check
        CHECK (
            surface_instance_id IS NULL
            OR (surface_resolution = 'resolved' AND btrim(surface_instance_id) <> '')
        )
        """
    )

    op.execute(
        """
        ALTER TABLE agent.turn_reference
        ADD COLUMN object_revision BIGINT NULL,
        ADD COLUMN work_revision_id UUID NULL,
        ADD COLUMN revision_n BIGINT NULL,
        ADD CONSTRAINT agent_turn_reference_content_revision_check
        CHECK (
            (object_revision IS NULL AND work_revision_id IS NULL AND revision_n IS NULL)
            OR (
                resolution = 'resolved'
                AND object_revision IS NOT NULL
                AND object_revision > 0
                AND work_revision_id IS NOT NULL
                AND revision_n IS NOT NULL
                AND revision_n > 0
                AND content_sha256 IS NOT NULL
            )
        )
        """
    )
    op.execute(
        """
        ALTER TABLE agent.draft_reference
        ADD COLUMN object_revision BIGINT NULL,
        ADD COLUMN work_revision_id UUID NULL,
        ADD COLUMN revision_n BIGINT NULL,
        ADD CONSTRAINT agent_draft_reference_content_revision_check
        CHECK (
            (object_revision IS NULL AND work_revision_id IS NULL AND revision_n IS NULL)
            OR (
                resolution = 'resolved'
                AND object_revision IS NOT NULL
                AND object_revision > 0
                AND work_revision_id IS NOT NULL
                AND revision_n IS NOT NULL
                AND revision_n > 0
                AND content_sha256 IS NOT NULL
            )
        )
        """
    )

    op.execute(
        """
        ALTER TABLE agent.composer_draft
        ADD COLUMN primary_object_revision BIGINT NULL,
        ADD COLUMN primary_work_revision_id UUID NULL,
        ADD COLUMN primary_revision_n BIGINT NULL,
        ADD COLUMN selected_object_revision BIGINT NULL,
        ADD COLUMN selected_work_revision_id UUID NULL,
        ADD COLUMN selected_revision_n BIGINT NULL,
        ADD CONSTRAINT agent_draft_primary_content_revision_check
        CHECK (
            (
                primary_object_revision IS NULL
                AND primary_work_revision_id IS NULL
                AND primary_revision_n IS NULL
            )
            OR (
                primary_resolution = 'resolved'
                AND primary_object_revision IS NOT NULL
                AND primary_object_revision > 0
                AND primary_work_revision_id IS NOT NULL
                AND primary_revision_n IS NOT NULL
                AND primary_revision_n > 0
                AND primary_content_sha256 IS NOT NULL
            )
        ),
        ADD CONSTRAINT agent_draft_selected_content_revision_check
        CHECK (
            (
                selected_object_revision IS NULL
                AND selected_work_revision_id IS NULL
                AND selected_revision_n IS NULL
            )
            OR (
                selected_resolution = 'resolved'
                AND selected_object_revision IS NOT NULL
                AND selected_object_revision > 0
                AND selected_work_revision_id IS NOT NULL
                AND selected_revision_n IS NOT NULL
                AND selected_revision_n > 0
                AND selected_content_sha256 IS NOT NULL
            )
        )
        """
    )


def downgrade() -> None:
    connection = op.get_bind()
    has_new_provenance = connection.exec_driver_sql(
        """
        SELECT EXISTS (
            SELECT 1 FROM agent.turn WHERE surface_instance_id IS NOT NULL
            UNION ALL
            SELECT 1 FROM agent.turn_reference
             WHERE object_revision IS NOT NULL
                OR work_revision_id IS NOT NULL
                OR revision_n IS NOT NULL
            UNION ALL
            SELECT 1 FROM agent.composer_draft
             WHERE surface_instance_id IS NOT NULL
                OR primary_object_revision IS NOT NULL
                OR primary_work_revision_id IS NOT NULL
                OR primary_revision_n IS NOT NULL
                OR selected_object_revision IS NOT NULL
                OR selected_work_revision_id IS NOT NULL
                OR selected_revision_n IS NOT NULL
            UNION ALL
            SELECT 1 FROM agent.draft_reference
             WHERE object_revision IS NOT NULL
                OR work_revision_id IS NOT NULL
                OR revision_n IS NOT NULL
        )
        """
    ).scalar_one()
    if has_new_provenance:
        raise RuntimeError(
            "cannot downgrade while typed Agent provenance exists; preserve the "
            "new provenance fields before retrying"
        )

    op.execute(
        "ALTER TABLE agent.composer_draft "
        "DROP CONSTRAINT IF EXISTS agent_draft_selected_content_revision_check, "
        "DROP CONSTRAINT IF EXISTS agent_draft_primary_content_revision_check, "
        "DROP CONSTRAINT IF EXISTS agent_draft_surface_instance_check, "
        "DROP COLUMN IF EXISTS selected_revision_n, "
        "DROP COLUMN IF EXISTS selected_work_revision_id, "
        "DROP COLUMN IF EXISTS selected_object_revision, "
        "DROP COLUMN IF EXISTS primary_revision_n, "
        "DROP COLUMN IF EXISTS primary_work_revision_id, "
        "DROP COLUMN IF EXISTS primary_object_revision, "
        "DROP COLUMN IF EXISTS surface_instance_id"
    )
    op.execute(
        "ALTER TABLE agent.draft_reference "
        "DROP CONSTRAINT IF EXISTS agent_draft_reference_content_revision_check, "
        "DROP COLUMN IF EXISTS revision_n, "
        "DROP COLUMN IF EXISTS work_revision_id, "
        "DROP COLUMN IF EXISTS object_revision"
    )
    op.execute(
        "ALTER TABLE agent.turn_reference "
        "DROP CONSTRAINT IF EXISTS agent_turn_reference_content_revision_check, "
        "DROP COLUMN IF EXISTS revision_n, "
        "DROP COLUMN IF EXISTS work_revision_id, "
        "DROP COLUMN IF EXISTS object_revision"
    )
    op.execute(
        "ALTER TABLE agent.turn "
        "DROP CONSTRAINT IF EXISTS agent_turn_surface_instance_check, "
        "DROP COLUMN IF EXISTS surface_instance_id"
    )
