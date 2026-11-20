"""Atomic encounter mechanics adoption/cancellation metadata, no source copy."""
from alembic import op
revision='20261022_0050'
down_revision='20261022_0049'
branch_labels=None
depends_on=None


def upgrade():
    op.execute("""CREATE TABLE combat.mechanics_adoption(
      operation_id uuid PRIMARY KEY,world_id text NOT NULL,encounter_id uuid NOT NULL REFERENCES combat.encounter(encounter_id),
      created_at timestamptz NOT NULL,payload jsonb NOT NULL,
      CHECK(COALESCE(jsonb_typeof(payload)='object' AND payload ?& ARRAY['schema','operation_id','world_id','encounter_id','state','request_digest'] AND payload->>'schema'='dmb_combat_mechanics_adoption_receipt_v1',FALSE)),
      CHECK(COALESCE(payload->>'operation_id'=operation_id::text,FALSE)),
      CHECK(COALESCE(payload->>'world_id'=world_id,FALSE)),
      CHECK(COALESCE(payload->>'encounter_id'=encounter_id::text,FALSE)),
      CHECK(COALESCE(payload->>'state' IN ('applied','canceled'),FALSE)))""")
    op.execute('CREATE INDEX combat_mechanics_adoption_history ON combat.mechanics_adoption(world_id,encounter_id,created_at,operation_id)')


def downgrade():
    op.execute('LOCK TABLE combat.mechanics_adoption IN ACCESS EXCLUSIVE MODE')
    if op.get_bind().exec_driver_sql('SELECT EXISTS(SELECT 1 FROM combat.mechanics_adoption)').scalar_one():
        raise RuntimeError('Cannot discard retained mechanics adoption history')
    op.execute('DROP TABLE combat.mechanics_adoption')
