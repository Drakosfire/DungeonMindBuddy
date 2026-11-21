"""Fence legacy writers from protected authored Page layouts."""

from alembic import op

revision = "20261122_0182"
down_revision = "20261122_0181"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE content.page_layout_writer_profile (
            work_object_id uuid PRIMARY KEY REFERENCES content.page_metadata(work_object_id),
            profile text NOT NULL CHECK (profile = 'dmb_page_layout_writer_v1')
        )
    """)
    op.execute("""
        CREATE FUNCTION content.require_page_layout_writer() RETURNS trigger
        LANGUAGE plpgsql AS $$
        DECLARE
            page_id uuid;
        BEGIN
            page_id := CASE WHEN TG_OP = 'DELETE' THEN OLD.work_object_id ELSE NEW.work_object_id END;
            IF EXISTS (SELECT FROM content.page_layout_writer_profile WHERE work_object_id = page_id)
               AND current_setting('dmb.page_layout_writer', true) IS DISTINCT FROM page_id::text
            THEN
                RAISE EXCEPTION 'protected Page requires its layout-aware writer'
                    USING ERRCODE = '23514';
            END IF;
            IF TG_OP = 'DELETE' THEN
                RETURN OLD;
            END IF;
            RETURN NEW;
        END;
        $$
    """)
    op.execute("""
        CREATE TRIGGER page_layout_revision_writer
        BEFORE UPDATE OF current_revision_id ON content.work_object
        FOR EACH ROW WHEN (OLD.current_revision_id IS DISTINCT FROM NEW.current_revision_id)
        EXECUTE FUNCTION content.require_page_layout_writer()
    """)
    op.execute("""
        CREATE TRIGGER page_layout_copy_writer
        BEFORE INSERT OR UPDATE OR DELETE ON content.working_copy
        FOR EACH ROW EXECUTE FUNCTION content.require_page_layout_writer()
    """)


def downgrade():
    raise RuntimeError("Forward recovery required: older Page writers cannot preserve protected layouts.")
