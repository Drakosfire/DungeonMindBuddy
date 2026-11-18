"""Fence older readers before recording PDF support on saved statblock reads."""

revision = "20261112_0157"
down_revision = "20261111_0156"
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    raise RuntimeError("Use forward recovery. Older readers cannot read saved statblock PDF support.")
