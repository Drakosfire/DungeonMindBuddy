"""Store immutable producer source input metadata beside existing APP source bytes."""
from alembic import op

revision = "20261030_0097"
down_revision = "20261030_0096"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE source.artifact ADD COLUMN input_descriptor JSONB")
    op.execute("""ALTER TABLE source.artifact ADD CONSTRAINT source_input_descriptor_object
        CHECK (input_descriptor IS NULL OR jsonb_typeof(input_descriptor) = 'object')""")


def downgrade():
    raise RuntimeError("Source input metadata requires recovery forward; no file-registry fallback")
