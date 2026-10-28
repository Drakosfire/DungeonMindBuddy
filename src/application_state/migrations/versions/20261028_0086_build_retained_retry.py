"""Fence readers for original-context discussion retry intents; no row rewrite."""
revision = "20261028_0086"
down_revision = "20261028_0085"
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    raise RuntimeError("Retained discussion retry intents require recovery forward")
