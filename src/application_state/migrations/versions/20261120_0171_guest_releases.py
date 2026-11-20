"""Retain owner-reviewed, isolated guest release candidates."""

from alembic import op

revision = "20261120_0171"
down_revision = "20261120_0170"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE content.page_metadata ADD COLUMN guest_visibility_generation bigint NOT NULL DEFAULT 0")
    op.execute("""
        CREATE TABLE workspace.guest_source_status_generation (
            work_object_id uuid PRIMARY KEY REFERENCES content.work_object(work_object_id) ON DELETE CASCADE,
            generation bigint NOT NULL CHECK (generation >= 0)
        )
    """)
    op.execute("""
        CREATE FUNCTION content.advance_guest_visibility_generation() RETURNS trigger
        LANGUAGE plpgsql AS $$ BEGIN
            IF NEW.visibility_state IS DISTINCT FROM OLD.visibility_state THEN
                NEW.guest_visibility_generation := OLD.guest_visibility_generation + 1;
            ELSE NEW.guest_visibility_generation := OLD.guest_visibility_generation; END IF;
            RETURN NEW;
        END $$
    """)
    op.execute("""
        CREATE TRIGGER page_guest_visibility_generation BEFORE UPDATE ON content.page_metadata
        FOR EACH ROW EXECUTE FUNCTION content.advance_guest_visibility_generation()
    """)
    op.execute("""
        CREATE FUNCTION content.advance_guest_status_generation() RETURNS trigger
        LANGUAGE plpgsql AS $$ BEGIN
            IF NEW.status IS DISTINCT FROM OLD.status THEN
                INSERT INTO workspace.guest_source_status_generation(work_object_id,generation)
                VALUES (NEW.work_object_id,1) ON CONFLICT (work_object_id)
                DO UPDATE SET generation=workspace.guest_source_status_generation.generation+1;
            END IF;
            RETURN NEW;
        END $$
    """)
    op.execute("""
        CREATE TRIGGER work_guest_status_generation BEFORE UPDATE ON content.work_object
        FOR EACH ROW EXECUTE FUNCTION content.advance_guest_status_generation()
    """)
    op.execute("""
        CREATE TABLE workspace.guest_world_owner_generation (
            world_id text PRIMARY KEY REFERENCES workspace.managed_world(world_id) ON DELETE CASCADE,
            generation bigint NOT NULL CHECK (generation >= 0)
        )
    """)
    op.execute("""
        CREATE FUNCTION workspace.advance_release_owner_generation() RETURNS trigger
        LANGUAGE plpgsql AS $$ BEGIN
            IF NEW.owner_subject IS DISTINCT FROM OLD.owner_subject THEN
                INSERT INTO workspace.guest_world_owner_generation(world_id,generation)
                VALUES (NEW.world_id,1) ON CONFLICT (world_id)
                DO UPDATE SET generation=workspace.guest_world_owner_generation.generation+1;
            END IF;
            RETURN NEW;
        END $$
    """)
    op.execute("""
        CREATE TRIGGER managed_world_release_owner_generation
        BEFORE UPDATE ON workspace.managed_world FOR EACH ROW
        EXECUTE FUNCTION workspace.advance_release_owner_generation()
    """)
    op.execute("""
        CREATE TABLE workspace.guest_release (
            release_id uuid PRIMARY KEY,
            world_id text NOT NULL REFERENCES workspace.managed_world(world_id) ON DELETE RESTRICT,
            owner_subject text NOT NULL CHECK (length(owner_subject) > 0),
            owner_generation bigint NOT NULL CHECK (owner_generation >= 0),
            native_world_id text NOT NULL CHECK (length(native_world_id) > 0),
            native_binding_version bigint NOT NULL CHECK (native_binding_version > 0),
            graph_revision text NOT NULL CHECK (length(graph_revision) > 0),
            manifest_sha256 text NOT NULL CHECK (manifest_sha256 ~ '^[a-f0-9]{64}$'),
            manifest jsonb NOT NULL CHECK (jsonb_typeof(manifest) = 'object'),
            state text NOT NULL DEFAULT 'candidate' CHECK (state IN ('candidate','published','revoked','invalidated')),
            created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
            published_at timestamptz,
            revoked_at timestamptz,
            CHECK ((state = 'revoked') = (revoked_at IS NOT NULL)),
            CHECK (state <> 'published' OR published_at IS NOT NULL)
        )
    """)
    op.execute("""
        CREATE TABLE workspace.guest_release_asset (
            release_id uuid NOT NULL REFERENCES workspace.guest_release(release_id) ON DELETE RESTRICT,
            asset_id uuid NOT NULL,
            mime_type text NOT NULL CHECK (mime_type IN ('image/png','image/jpeg','image/webp')),
            content_sha256 text NOT NULL CHECK (content_sha256 ~ '^[a-f0-9]{64}$'),
            content bytea NOT NULL CHECK (octet_length(content) BETWEEN 1 AND 10000000),
            PRIMARY KEY (release_id, asset_id)
        )
    """)
    op.execute("""
        CREATE TABLE workspace.guest_release_source_binding (
            release_id uuid NOT NULL REFERENCES workspace.guest_release(release_id) ON DELETE RESTRICT,
            excerpt_id uuid NOT NULL,
            work_object_id uuid NOT NULL REFERENCES content.page_metadata(work_object_id) ON DELETE RESTRICT,
            visibility_generation bigint NOT NULL CHECK (visibility_generation >= 0),
            status_generation bigint NOT NULL CHECK (status_generation >= 0),
            revision_n integer NOT NULL CHECK (revision_n > 0),
            content_sha256 text NOT NULL CHECK (content_sha256 ~ '^[a-f0-9]{64}$'),
            span_start integer NOT NULL CHECK (span_start >= 0),
            span_end integer NOT NULL CHECK (span_end > span_start),
            registry_revision bigint NOT NULL CHECK (registry_revision > 0),
            PRIMARY KEY (release_id, excerpt_id)
        )
    """)
    op.execute("""
        CREATE TABLE workspace.guest_release_pointer (
            world_id text PRIMARY KEY REFERENCES workspace.managed_world(world_id) ON DELETE RESTRICT,
            public_id uuid NOT NULL UNIQUE,
            release_id uuid REFERENCES workspace.guest_release(release_id) ON DELETE RESTRICT,
            version bigint NOT NULL DEFAULT 0 CHECK (version >= 0)
        )
    """)


def downgrade():
    # Match the normal owner -> source -> release acquisition order before
    # taking locks that block staging. Trigger removal requires parent locks.
    op.execute("LOCK TABLE workspace.managed_world, content.work_object, content.page_metadata IN ACCESS EXCLUSIVE MODE")
    op.execute("LOCK TABLE workspace.guest_release_pointer, workspace.guest_release_source_binding, workspace.guest_release_asset, workspace.guest_release IN ACCESS EXCLUSIVE MODE")
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM workspace.guest_release)
                OR EXISTS (SELECT 1 FROM workspace.guest_release_pointer) THEN
                RAISE EXCEPTION 'Cannot discard guest release history';
            END IF;
        END $$
    """)
    op.drop_table("guest_release_pointer", schema="workspace")
    op.drop_table("guest_release_source_binding", schema="workspace")
    op.drop_table("guest_release_asset", schema="workspace")
    op.drop_table("guest_release", schema="workspace")
    op.execute("DROP TRIGGER managed_world_release_owner_generation ON workspace.managed_world")
    op.execute("DROP FUNCTION workspace.advance_release_owner_generation()")
    op.drop_table("guest_world_owner_generation", schema="workspace")
    op.execute("DROP TRIGGER page_guest_visibility_generation ON content.page_metadata")
    op.execute("DROP FUNCTION content.advance_guest_visibility_generation()")
    op.execute("DROP TRIGGER work_guest_status_generation ON content.work_object")
    op.execute("DROP FUNCTION content.advance_guest_status_generation()")
    op.execute("ALTER TABLE content.page_metadata DROP COLUMN guest_visibility_generation")
    op.drop_table("guest_source_status_generation", schema="workspace")
