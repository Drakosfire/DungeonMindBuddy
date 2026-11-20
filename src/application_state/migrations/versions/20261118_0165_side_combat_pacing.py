"""Fence older readers before side-based Combat profiles can be retained."""

revision = "20261118_0165"
down_revision = "20261118_0164"
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    raise RuntimeError("Use forward recovery. Older readers cannot decode retained side-based Combat profiles and history.")
