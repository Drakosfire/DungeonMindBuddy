"""Statblock-owned copies of artwork from published PDF reviews."""

from alembic import op

revision = "20261128_0219"
down_revision = "20261128_0218"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE mechanics_revision.pdf_portrait (
            statblock_id text NOT NULL CHECK (statblock_id ~ '^sb_[a-z0-9]+$'),
            world_id text NOT NULL,
            draft_id uuid NOT NULL,
            review_id uuid NOT NULL,
            jpeg bytea NOT NULL CHECK (octet_length(jpeg) BETWEEN 4 AND 16777216),
            PRIMARY KEY (statblock_id, review_id)
        )
    """)
    op.execute("""
        CREATE FUNCTION mechanics_revision.remove_purged_pdf_portraits()
        RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog AS $$
        BEGIN
            DELETE FROM mechanics_revision.pdf_portrait
            WHERE statblock_id=NEW.statblock_id AND world_id=NEW.world_id AND draft_id=NEW.draft_id;
            RETURN NEW;
        END
        $$;
        REVOKE EXECUTE ON FUNCTION mechanics_revision.remove_purged_pdf_portraits() FROM PUBLIC;
        CREATE TRIGGER remove_purged_pdf_portraits AFTER UPDATE OF complete ON mechanics_revision.purge
        FOR EACH ROW WHEN (NEW.complete AND NOT OLD.complete)
        EXECUTE FUNCTION mechanics_revision.remove_purged_pdf_portraits();
        DO $$ BEGIN
            IF EXISTS (SELECT FROM pg_roles WHERE rolname='dmb_app_runtime') THEN
                GRANT SELECT, INSERT ON mechanics_revision.pdf_portrait TO dmb_app_runtime;
            END IF;
        END $$;
    """)


def downgrade():
    op.execute("LOCK TABLE mechanics_revision.pdf_portrait IN ACCESS EXCLUSIVE MODE")
    if op.get_bind().exec_driver_sql("SELECT EXISTS (SELECT FROM mechanics_revision.pdf_portrait)").scalar_one():
        raise RuntimeError("Cannot discard saved statblock portraits")
    op.execute("DROP TRIGGER remove_purged_pdf_portraits ON mechanics_revision.purge")
    op.execute("DROP FUNCTION mechanics_revision.remove_purged_pdf_portraits()")
    op.execute("DROP TABLE mechanics_revision.pdf_portrait")
