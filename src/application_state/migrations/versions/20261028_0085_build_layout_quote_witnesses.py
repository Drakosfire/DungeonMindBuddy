"""Fence readers for layout-only source quote matching; no row rewrite."""
revision = "20261028_0085"
down_revision = "20261028_0084"
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    raise RuntimeError("Layout quote witnesses require recovery forward")
