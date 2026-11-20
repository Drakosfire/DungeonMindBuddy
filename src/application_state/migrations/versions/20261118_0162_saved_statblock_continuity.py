"""Fence older readers before recording saved statblock continuity."""

revision = "20261118_0162"
down_revision = "20261117_0161"
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    raise RuntimeError("Use forward recovery. Older readers cannot read saved statblock continuity.")
