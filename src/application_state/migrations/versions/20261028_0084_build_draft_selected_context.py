"""Fence readers for selected saved context with a complete working draft."""
revision = "20261028_0084"
down_revision = "20261028_0083"
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    raise RuntimeError("Selected saved draft context requires recovery forward")
