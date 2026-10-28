"""Fence readers for Sol final-writer budget records; no row rewrite."""
revision = "20261028_0087"
down_revision = "20261028_0086"
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    raise RuntimeError("Retained final-writer allocations require recovery forward")
