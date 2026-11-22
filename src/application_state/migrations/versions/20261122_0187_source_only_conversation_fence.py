"""Fence readers that require a pending Graph for prior-citation admission."""

revision = "20261122_0187"
down_revision = "20261122_0186"
branch_labels = None
depends_on = None


def upgrade():
    # Existing receipt/event shapes now admit source-only conversation reuse.
    # Older readers cannot validate that combination; no rows are rewritten.
    pass


def downgrade():
    raise RuntimeError(
        "Use forward recovery. Older Build readers cannot replay source-only conversation citation reuse."
    )
