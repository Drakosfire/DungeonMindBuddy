"""Plan-scene template identity and transactional immutable encounter versions."""
from alembic import op
revision = "20261022_0051"
down_revision = "20261022_0050"
branch_labels = None
depends_on = None

def upgrade():
    op.execute("""CREATE TABLE combat.scene_template_cancellation (
        operation_id uuid PRIMARY KEY,world_id text NOT NULL,
        request_digest text NOT NULL CHECK(request_digest ~ '^sha256:[0-9a-f]{64}$'),
        request jsonb NOT NULL CHECK(jsonb_typeof(request)='object'))""")
    op.execute("ALTER TABLE combat.encounter ADD CONSTRAINT encounter_world_identity UNIQUE(encounter_id,world_id)")
    op.execute("""CREATE TABLE combat.scene_template (
        encounter_id uuid PRIMARY KEY,
        world_id text NOT NULL,
        document_id uuid NOT NULL REFERENCES content.work_object(work_object_id),
        scene_id text NOT NULL,
        operation_id uuid NOT NULL UNIQUE,
        request_digest text NOT NULL CHECK(request_digest ~ '^sha256:[0-9a-f]{64}$'),
        request jsonb NOT NULL CHECK(jsonb_typeof(request)='object'),
        payload jsonb NOT NULL CHECK(jsonb_typeof(payload)='object'),
        UNIQUE(world_id,document_id,scene_id),
        FOREIGN KEY(encounter_id,world_id) REFERENCES combat.encounter(encounter_id,world_id))""")
    op.execute("""CREATE TABLE combat.scene_template_version (
        encounter_id uuid NOT NULL REFERENCES combat.scene_template(encounter_id),
        revision integer NOT NULL CHECK(revision>0),
        digest text NOT NULL CHECK(digest ~ '^sha256:[0-9a-f]{64}$'),
        saved_at timestamptz NOT NULL,
        payload jsonb NOT NULL CHECK(jsonb_typeof(payload)='object'),
        PRIMARY KEY(encounter_id,revision))""")

def downgrade():
    op.execute("LOCK TABLE combat.scene_template,combat.scene_template_version,combat.scene_template_cancellation IN ACCESS EXCLUSIVE MODE")
    if op.get_bind().exec_driver_sql("SELECT EXISTS(SELECT 1 FROM combat.scene_template) OR EXISTS(SELECT 1 FROM combat.scene_template_cancellation)").scalar_one():
        raise RuntimeError("Cannot discard retained scene encounter templates")
    op.execute("DROP TABLE combat.scene_template_cancellation")
    op.execute("DROP TABLE combat.scene_template_version")
    op.execute("DROP TABLE combat.scene_template")
    op.execute("ALTER TABLE combat.encounter DROP CONSTRAINT encounter_world_identity")
