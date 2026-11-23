"""Join the portrait and serving release migration histories."""
revision = "20261123_0204"
down_revision = ("20261122_0193", "20261123_0200")
branch_labels = None
depends_on = None

def upgrade():
    pass

def downgrade():
    raise RuntimeError("Use forward recovery to preserve portrait appends.")
