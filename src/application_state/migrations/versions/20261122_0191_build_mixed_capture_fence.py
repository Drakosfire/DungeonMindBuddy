"""Fence readers before admitting mixed-content Build placement captures."""

revision = "20261122_0191"
down_revision = "20261122_0190"
branch_labels = None
depends_on = None


def upgrade():
    # Older readers cannot reconstruct a retained mixed-content Build catalog.
    pass


def downgrade():
    raise RuntimeError(
        "Use forward recovery. Older Build readers cannot reopen mixed-content captures."
    )
