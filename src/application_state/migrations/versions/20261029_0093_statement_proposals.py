"""Private qualified source proposal work; no native publication authority."""
from alembic import op
revision = "20261029_0093"
down_revision = "20261029_0092"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""CREATE TABLE ingest.statement_proposal_operation (
      operation_id UUID PRIMARY KEY, owner TEXT NOT NULL CHECK(length(owner)>0),
      world_id TEXT NOT NULL CHECK(length(world_id)>0), payload JSONB NOT NULL,
      CHECK (jsonb_typeof(payload)='object'),
      CHECK (payload->>'operation_id'=operation_id::text),
      CHECK (payload->>'owner'=owner),
      CHECK (payload#>>'{intent,managed_world_id}'=world_id)
    )""")


def downgrade():
    raise RuntimeError("Retained proposal work requires recovery forward")
