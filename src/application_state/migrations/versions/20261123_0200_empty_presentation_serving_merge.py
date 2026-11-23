"""Fence serving-line readers before retaining empty paragraph presentation."""

revision = "20261123_0200"
down_revision = "20261122_0198"
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    raise RuntimeError("Use forward recovery; older readers cannot retain empty paragraph presentation.")
