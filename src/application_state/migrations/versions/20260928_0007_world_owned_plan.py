"""permit strictly World-owned Content Plans

Revision ID: 20260928_0007
Revises: 20260906_0006
Create Date: 2026-09-28

"""

from __future__ import annotations

from alembic import op

revision = "20260928_0007"
down_revision = "20260906_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE content.work_object ALTER COLUMN campaign_id DROP NOT NULL")
    op.execute(
        """
        ALTER TABLE content.work_object
        ADD CONSTRAINT work_object_scope_check CHECK (
            (
                campaign_id IS NOT NULL
                AND btrim(campaign_id) <> ''
                AND world_id IS NULL
            )
            OR
            (
                kind = 'plan'
                AND campaign_id IS NULL
                AND world_id IS NOT NULL
                AND btrim(world_id) <> ''
                AND target_session IS NULL
            )
        )
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM content.work_object
                WHERE campaign_id IS NULL AND world_id IS NOT NULL
            ) THEN
                RAISE EXCEPTION
                    'cannot downgrade while World-owned Plans exist';
            END IF;
        END $$
        """
    )
    op.execute(
        "ALTER TABLE content.work_object DROP CONSTRAINT work_object_scope_check"
    )
    op.execute("ALTER TABLE content.work_object ALTER COLUMN campaign_id SET NOT NULL")
