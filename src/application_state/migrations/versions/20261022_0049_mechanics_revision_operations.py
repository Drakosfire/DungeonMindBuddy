"""Durable Buddy revision intent/recovery; producer mechanics remain external."""
from alembic import op
revision='20261022_0049'
down_revision='20261022_0048'
branch_labels=None
depends_on=None


def upgrade():
    op.execute("CREATE SCHEMA mechanics_revision")
    op.execute("CREATE TABLE mechanics_revision.cancellation(operation_id uuid PRIMARY KEY,world_id text NOT NULL,draft_id uuid NOT NULL)")
    op.execute("""CREATE TABLE mechanics_revision.operation(
      operation_id uuid PRIMARY KEY, world_id text NOT NULL, draft_id uuid NOT NULL,
      statblock_id text NOT NULL,state text NOT NULL CHECK(state IN ('prepared','outcome_unknown','committed','refused')),
      created_at timestamptz NOT NULL,payload jsonb NOT NULL,
      CHECK(COALESCE(jsonb_typeof(payload)='object' AND payload ?& ARRAY['schema','operation_id','world_id','draft_id','state','base'] AND payload->>'schema'='dmb_mechanics_revision_operation_v1',FALSE)),
      CHECK(COALESCE(payload->>'operation_id'=operation_id::text,FALSE)),CHECK(COALESCE(payload->>'world_id'=world_id,FALSE)),
      CHECK(COALESCE(payload->>'draft_id'=draft_id::text,FALSE)),CHECK(COALESCE(payload->>'state'=state,FALSE)),
      CHECK(COALESCE(payload->'base'->>'statblock_id'=statblock_id,FALSE)))""")
    op.execute('CREATE INDEX mechanics_revision_page ON mechanics_revision.operation(world_id,draft_id,created_at,operation_id)')
    op.execute("CREATE INDEX mechanics_revision_exact ON mechanics_revision.operation(world_id,draft_id,(payload#>>'{result,revision_id}')) WHERE state='committed'")
    op.execute("CREATE UNIQUE INDEX mechanics_revision_unresolved ON mechanics_revision.operation(statblock_id) WHERE state IN ('prepared','outcome_unknown')")


def downgrade():
    op.execute('LOCK TABLE mechanics_revision.operation IN ACCESS EXCLUSIVE MODE')
    if op.get_bind().exec_driver_sql('SELECT EXISTS(SELECT 1 FROM mechanics_revision.operation) OR EXISTS(SELECT 1 FROM mechanics_revision.cancellation)').scalar_one():
        raise RuntimeError('Cannot discard retained mechanics revision operations')
    op.execute('DROP SCHEMA mechanics_revision CASCADE')
