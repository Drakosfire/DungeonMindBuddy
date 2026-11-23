"""Fence readers before retaining the exact author-context tail presentation."""
revision = "20261122_0197"
down_revision = "20261122_0196"
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    raise RuntimeError("Use forward recovery: older readers cannot verify author-context presentation.")
