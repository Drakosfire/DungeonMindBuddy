"""Fence readers after mode-bound Build decision authorization; no row rewrite."""
revision = "20261028_0082"
down_revision = "20261027_0081"
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    raise RuntimeError("Mode-bound Build decisions require recovery forward")
