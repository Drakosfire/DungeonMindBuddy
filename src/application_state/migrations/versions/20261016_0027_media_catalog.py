"""Owner-scoped media identity and fenced storage lifecycle."""

from alembic import op

revision = "20261016_0027"
down_revision = "20261016_0026"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE SCHEMA media")
    op.execute("""
        CREATE TABLE media.asset (
            asset_id UUID PRIMARY KEY,
            owner_id TEXT NOT NULL CHECK (btrim(owner_id) <> ''),
            created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
            mime_type TEXT NOT NULL CHECK (mime_type IN ('image/png','image/jpeg','image/webp')),
            width INTEGER NOT NULL CHECK (width > 0),
            height INTEGER NOT NULL CHECK (height > 0),
            byte_length BIGINT NOT NULL CHECK (byte_length > 0 AND byte_length <= 10000000),
            content_sha256 TEXT NOT NULL CHECK (content_sha256 ~ '^[a-f0-9]{64}$'),
            provenance_sha256 TEXT NOT NULL CHECK (provenance_sha256 ~ '^[a-f0-9]{64}$'),
            provenance JSONB NOT NULL CHECK (jsonb_typeof(provenance) = 'object' AND octet_length(provenance::text) <= 262144)
        )
    """)
    op.execute(
        "CREATE INDEX media_asset_owner_recent ON media.asset(owner_id, created_at DESC, asset_id DESC)"
    )
    op.execute("""
        CREATE TABLE media.storage (
            asset_id UUID PRIMARY KEY REFERENCES media.asset(asset_id),
            state TEXT NOT NULL DEFAULT 'staged' CHECK (state IN ('staged','uploading','unknown','ready')),
            fence UUID,
            staged_bytes BYTEA NOT NULL CHECK (octet_length(staged_bytes) > 0 AND octet_length(staged_bytes) <= 10000000),
            receipt JSONB,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
            CHECK ((state = 'staged' AND fence IS NULL) OR (state <> 'staged' AND fence IS NOT NULL)),
            CHECK ((state = 'ready' AND receipt IS NOT NULL AND jsonb_typeof(receipt) = 'object') OR (state <> 'ready' AND receipt IS NULL))
        )
    """)


def downgrade():
    if (
        op.get_bind()
        .exec_driver_sql("SELECT EXISTS(SELECT 1 FROM media.asset)")
        .scalar_one()
    ):
        raise RuntimeError("refusing to discard retained media assets")
    op.execute("DROP TABLE media.storage")
    op.execute("DROP TABLE media.asset")
    op.execute("DROP SCHEMA media")
