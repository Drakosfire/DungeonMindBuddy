"""Append-only Buddy World mechanics association receipts."""
from alembic import op

revision = "20261022_0043"
down_revision = "20261020_0042"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE SCHEMA world_mechanics")
    op.execute("""
        CREATE TABLE world_mechanics.association (
            association_id UUID PRIMARY KEY,
            world_id TEXT NOT NULL CHECK(world_id ~ '^[a-z][a-z0-9_-]{0,62}$'),
            node_id TEXT NOT NULL CHECK(btrim(node_id) <> ''),
            version INTEGER NOT NULL CHECK(version > 0),
            request_id UUID NOT NULL,
            previous_association_id UUID REFERENCES world_mechanics.association(association_id),
            payload JSONB NOT NULL CHECK(jsonb_typeof(payload)='object'),
            UNIQUE(world_id,request_id),
            UNIQUE(world_id,node_id,version),
            CHECK((version=1) = (previous_association_id IS NULL)),
            CHECK(payload->>'association_id'=association_id::text),
            CHECK(payload->'request'->>'request_id'=request_id::text),
            CHECK(payload->'request'->'target'->>'managed_world_id'=world_id),
            CHECK(payload->'request'->'target'->>'node_id'=node_id),
            CHECK((payload->>'version')::integer=version),
            CHECK((payload->>'previous_association_id') IS NOT DISTINCT FROM previous_association_id::text)
        )
    """)


def downgrade():
    if op.get_bind().exec_driver_sql("SELECT EXISTS(SELECT 1 FROM world_mechanics.association)").scalar_one():
        raise RuntimeError("Cannot downgrade while World mechanics associations exist")
    op.execute("DROP TABLE world_mechanics.association")
    op.execute("DROP SCHEMA world_mechanics")
