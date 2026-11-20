"""Fence older readers before captures can carry verified recap numbers."""

revision = "20261110_0152"
down_revision = "20261110_0151"
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    raise RuntimeError("Use forward recovery. Older readers cannot read captured recap sessions.")
