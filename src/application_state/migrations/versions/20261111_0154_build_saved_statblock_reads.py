"""Fence older readers before native Build can record saved statblock reads."""

revision = "20261111_0154"
down_revision = "20261111_0153"
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    raise RuntimeError("Use forward recovery. Older readers cannot read saved statblock events.")
