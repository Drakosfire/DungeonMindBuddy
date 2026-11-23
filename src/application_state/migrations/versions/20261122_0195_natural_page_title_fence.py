"""Fence readers before retaining natural title-before-page witnesses."""
revision = "20261122_0195"
down_revision = "20261122_0194"
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    raise RuntimeError("Use forward recovery: older readers reject natural page title witnesses.")
