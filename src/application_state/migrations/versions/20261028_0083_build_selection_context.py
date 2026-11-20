"""Fence readers after the frozen evidence-selection context policy; no row rewrite."""
revision = "20261028_0083"
down_revision = "20261028_0082"
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    raise RuntimeError("Selection-context Build decisions require recovery forward")
