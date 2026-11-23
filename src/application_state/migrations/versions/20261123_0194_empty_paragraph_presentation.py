"""Fence readers predating versioned empty paragraph presentation."""

revision = "20261123_0194"
down_revision = "20261122_0193"
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    raise RuntimeError("Use forward recovery; older readers cannot retain empty paragraph presentation.")
