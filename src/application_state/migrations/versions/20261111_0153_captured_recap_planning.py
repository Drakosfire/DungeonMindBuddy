"""Fence older readers before captures can carry recap planning ranges."""

revision = "20261111_0153"
down_revision = "20261110_0152"
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    raise RuntimeError("Use forward recovery. Older readers cannot read captured recap planning ranges.")
