"""Immutable session preparation, cancellation fences and Run-owned encounters."""
from alembic import op
revision="20261022_0052"
down_revision="20261022_0051"
branch_labels=None
depends_on=None

def upgrade():
    op.execute("ALTER TABLE play.run ADD CONSTRAINT run_world_identity UNIQUE(run_id,world_id)")
    op.execute("""CREATE TABLE play.session_preparation (
      run_id uuid PRIMARY KEY,world_id text NOT NULL,request_digest text NOT NULL,
      payload jsonb NOT NULL CHECK(jsonb_typeof(payload)='object'),
      FOREIGN KEY(run_id,world_id) REFERENCES play.run(run_id,world_id))""")
    op.execute("""CREATE TABLE play.session_creation_cancellation (
      run_id uuid PRIMARY KEY,world_id text NOT NULL,request_digest text NOT NULL,
      request jsonb NOT NULL CHECK(jsonb_typeof(request)='object'))""")
    op.execute("""CREATE TABLE combat.run_scene_encounter (
      encounter_id uuid PRIMARY KEY,world_id text NOT NULL,run_id uuid NOT NULL,
      scene_id text NOT NULL,operation_id uuid NOT NULL UNIQUE,
      template_encounter_id uuid NOT NULL,template_revision integer NOT NULL,
      request_digest text NOT NULL,payload jsonb NOT NULL CHECK(jsonb_typeof(payload)='object'),
      UNIQUE(world_id,run_id,scene_id),
      FOREIGN KEY(encounter_id,world_id) REFERENCES combat.encounter(encounter_id,world_id),
      FOREIGN KEY(run_id,world_id) REFERENCES play.run(run_id,world_id),
      FOREIGN KEY(template_encounter_id,template_revision) REFERENCES combat.scene_template_version(encounter_id,revision))""")
    op.execute("""CREATE TABLE combat.run_scene_cancellation (
      operation_id uuid PRIMARY KEY,world_id text NOT NULL,run_id uuid NOT NULL,
      scene_id text NOT NULL,request_digest text NOT NULL,
      request jsonb NOT NULL CHECK(jsonb_typeof(request)='object'),
      FOREIGN KEY(run_id,world_id) REFERENCES play.run(run_id,world_id))""")

def downgrade():
    tables=('combat.run_scene_cancellation','combat.run_scene_encounter','play.session_creation_cancellation','play.session_preparation')
    op.execute('LOCK TABLE '+','.join(tables)+' IN ACCESS EXCLUSIVE MODE')
    if any(op.get_bind().exec_driver_sql('SELECT EXISTS(SELECT 1 FROM '+table+')').scalar_one() for table in tables):
        raise RuntimeError('Cannot discard retained session preparation or encounter history')
    for table in tables:op.execute('DROP TABLE '+table)
    op.execute('ALTER TABLE play.run DROP CONSTRAINT run_world_identity')
