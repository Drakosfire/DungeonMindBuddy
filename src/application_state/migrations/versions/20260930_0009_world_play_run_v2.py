"""add typed World ownership for PlayRun V2

Revision ID: 20260930_0009
Revises: 20260929_0008
Create Date: 2026-09-30

"""

from __future__ import annotations

from alembic import op

revision = "20260930_0009"
down_revision = "20260929_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE play.run ADD COLUMN world_id TEXT NULL")
    op.execute("ALTER TABLE play.run ALTER COLUMN campaign_id DROP NOT NULL")
    op.execute(
        """
        ALTER TABLE play.run
        ADD CONSTRAINT play_run_exactly_one_owner_check CHECK (
            (
                campaign_id IS NOT NULL
                AND btrim(campaign_id) <> ''
                AND world_id IS NULL
            )
            OR
            (
                campaign_id IS NULL
                AND world_id IS NOT NULL
                AND btrim(world_id) <> ''
            )
        )
        """
    )
    op.execute(
        """
        CREATE INDEX play_run_world_created
            ON play.run (world_id, created_at DESC, run_id)
            WHERE world_id IS NOT NULL
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM play.run WHERE world_id IS NOT NULL) THEN
                RAISE EXCEPTION
                    'cannot downgrade while World-owned Play Runs exist';
            END IF;
        END; $$
        """
    )
    op.execute("DROP INDEX IF EXISTS play.play_run_world_created")
    op.execute("ALTER TABLE play.run DROP CONSTRAINT play_run_exactly_one_owner_check")
    op.execute("ALTER TABLE play.run DROP COLUMN world_id")
    op.execute("ALTER TABLE play.run ALTER COLUMN campaign_id SET NOT NULL")
