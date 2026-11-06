"""Move connected-page recovery authority to application state."""
from alembic import op

revision = "20261105_0116"
down_revision = "20261105_0115"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""CREATE TABLE content.connected_page_operation (
      operation_id UUID PRIMARY KEY,
      world_id TEXT NOT NULL CHECK(length(world_id)>0),
      page_id UUID NOT NULL UNIQUE,
      payload JSONB NOT NULL CHECK(jsonb_typeof(payload)='object'),
      CHECK ((payload#>>'{intent,operation_id}') IS NOT NULL
             AND payload#>>'{intent,operation_id}'=operation_id::text),
      CHECK ((payload#>>'{intent,world_id}') IS NOT NULL
             AND payload#>>'{intent,world_id}'=world_id),
      CHECK ((payload->>'page_id') IS NOT NULL AND payload->>'page_id'=page_id::text),
      CHECK ((payload->>'phase') IS NOT NULL
             AND payload->>'phase' IN ('reserved','created','saved','prepared','complete'))
    )""")


def downgrade():
    raise RuntimeError("Retained connected-page operations require recovery forward")
