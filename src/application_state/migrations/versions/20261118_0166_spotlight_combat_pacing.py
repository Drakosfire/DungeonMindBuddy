"""Fence older readers before free spotlight Combat profiles can be retained."""

revision = "20261118_0166"
down_revision = "20261118_0165"
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    raise RuntimeError("Use forward recovery. Older readers cannot decode retained spotlight Combat profiles and history.")
