"""persist explicit World ownership on committed Content revisions

Revision ID: 20260929_0008
Revises: 20260928_0007
Create Date: 2026-09-29

"""

from __future__ import annotations

from alembic import op

revision = "20260929_0008"
down_revision = "20260928_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE content.work_revision ADD COLUMN world_id TEXT NULL")
    op.execute(
        """
        UPDATE content.work_revision AS revision
        SET world_id = work_object.world_id
        FROM content.work_object AS work_object
        WHERE revision.work_object_id = work_object.work_object_id
          AND work_object.world_id IS NOT NULL
        """
    )
    op.execute(
        """
        ALTER TABLE content.work_revision
        ADD CONSTRAINT work_revision_world_id_check
        CHECK (world_id IS NULL OR btrim(world_id) <> '')
        """
    )
    op.execute("ALTER TABLE content.work_object DROP CONSTRAINT work_object_scope_check")
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
                kind IN ('plan', 'runbook')
                AND campaign_id IS NULL
                AND world_id IS NOT NULL
                AND btrim(world_id) <> ''
                AND target_session IS NULL
            )
        )
        """
    )
    op.execute(
        """
        CREATE FUNCTION content.enforce_work_revision_world_owner()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        DECLARE
            owner_world_id TEXT;
        BEGIN
            SELECT world_id INTO owner_world_id
            FROM content.work_object
            WHERE work_object_id = NEW.work_object_id;
            IF NOT FOUND THEN
                RAISE EXCEPTION 'work_revision WorkObject does not exist';
            END IF;
            IF NEW.world_id IS DISTINCT FROM owner_world_id THEN
                RAISE EXCEPTION 'work_revision World owner does not match its WorkObject';
            END IF;
            RETURN NEW;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER work_revision_world_owner_before_write
        BEFORE INSERT OR UPDATE OF work_object_id, world_id
        ON content.work_revision
        FOR EACH ROW EXECUTE FUNCTION content.enforce_work_revision_world_owner()
        """
    )
    op.execute(
        """
        CREATE FUNCTION content.prevent_work_object_world_owner_change()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF OLD.world_id IS DISTINCT FROM NEW.world_id THEN
                RAISE EXCEPTION 'cannot change WorkObject World owner';
            END IF;
            RETURN NEW;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER work_object_world_owner_before_update
        BEFORE UPDATE OF world_id ON content.work_object
        FOR EACH ROW EXECUTE FUNCTION content.prevent_work_object_world_owner_change()
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
                WHERE kind = 'runbook'
                  AND campaign_id IS NULL
                  AND world_id IS NOT NULL
            ) THEN
                RAISE EXCEPTION
                    'cannot downgrade while World-owned Runbooks exist';
            END IF;
        END; $$
        """
    )
    op.execute(
        "DROP TRIGGER IF EXISTS work_object_world_owner_before_update ON content.work_object"
    )
    op.execute(
        "DROP FUNCTION IF EXISTS content.prevent_work_object_world_owner_change()"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS work_revision_world_owner_before_write ON content.work_revision"
    )
    op.execute("DROP FUNCTION IF EXISTS content.enforce_work_revision_world_owner()")
    op.execute("ALTER TABLE content.work_revision DROP CONSTRAINT work_revision_world_id_check")
    op.execute("ALTER TABLE content.work_revision DROP COLUMN world_id")
    op.execute("ALTER TABLE content.work_object DROP CONSTRAINT work_object_scope_check")
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
