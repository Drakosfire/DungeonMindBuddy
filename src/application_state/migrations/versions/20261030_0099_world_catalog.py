"""Typed Buddy World metadata storage; no automatic file adoption or native writes."""
from alembic import op

revision = "20261030_0099"
down_revision = "20261030_0098"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE SCHEMA workspace")
    op.execute("""CREATE TABLE workspace.managed_world (
        world_id TEXT PRIMARY KEY CHECK (world_id ~ '^[a-z][a-z0-9_-]{0,62}$'),
        name TEXT NOT NULL CHECK (btrim(name) <> ''),
        source_root_relpath TEXT NOT NULL CHECK (source_root_relpath <> ''),
        created_at TEXT NOT NULL CHECK (created_at <> ''),
        owner_subject TEXT,
        revision BIGINT NOT NULL CHECK (revision > 0)
    )""")
    op.execute("""CREATE TABLE workspace.world_native_binding (
        world_id TEXT PRIMARY KEY REFERENCES workspace.managed_world(world_id),
        native_world_id TEXT NOT NULL CHECK (btrim(native_world_id) <> ''),
        status TEXT NOT NULL CHECK (status IN ('active','inactive','provisioning')),
        binding_version BIGINT NOT NULL CHECK (binding_version > 0),
        validated_at TEXT,
        validated_head_revision_id TEXT,
        provisioning_id TEXT UNIQUE,
        initialization_revision_id TEXT,
        CHECK (provisioning_id IS NULL OR provisioning_id ~ '^provision:[0-9a-f]{32}$'),
        CHECK (status <> 'provisioning' OR (
            binding_version = 1 AND native_world_id ~ '^world:[0-9a-f]{32}$'
            AND provisioning_id IS NOT NULL AND initialization_revision_id IS NULL
            AND validated_at IS NULL AND validated_head_revision_id IS NULL)),
        CHECK (status = 'provisioning' OR (
            validated_at IS NOT NULL AND validated_at <> ''
            AND validated_head_revision_id IS NOT NULL AND btrim(validated_head_revision_id) <> ''
            AND ((provisioning_id IS NULL AND initialization_revision_id IS NULL)
                OR (provisioning_id IS NOT NULL AND initialization_revision_id IS NOT NULL
                    AND btrim(initialization_revision_id) <> ''))))
    )""")
    op.execute("""CREATE UNIQUE INDEX world_native_claim_unique
        ON workspace.world_native_binding(native_world_id)
        WHERE status IN ('active','provisioning')""")
    op.execute("""CREATE TABLE workspace.world_access_grant (
        world_id TEXT NOT NULL REFERENCES workspace.managed_world(world_id),
        subject TEXT NOT NULL CHECK (subject <> ''),
        granted_by_subject TEXT NOT NULL CHECK (granted_by_subject <> ''),
        ordinal INTEGER NOT NULL CHECK (ordinal >= 0),
        can_read BOOLEAN NOT NULL,
        can_write BOOLEAN NOT NULL,
        can_manage BOOLEAN NOT NULL,
        can_share BOOLEAN NOT NULL,
        PRIMARY KEY(world_id,subject),
        UNIQUE(world_id,ordinal),
        CHECK (can_read OR can_write OR can_manage OR can_share)
    )""")


def downgrade():
    raise RuntimeError("World storage requires explicit recovery forward")
