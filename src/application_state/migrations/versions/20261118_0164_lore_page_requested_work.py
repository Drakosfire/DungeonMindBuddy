"""Fence readers before recording generic lore-page requested work."""

revision = "20261118_0164"
down_revision = "20261118_0163"
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    raise RuntimeError("Use forward recovery. Older readers cannot read lore-page requested work.")
