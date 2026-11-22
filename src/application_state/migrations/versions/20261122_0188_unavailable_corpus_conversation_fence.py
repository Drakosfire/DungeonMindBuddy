"""Fence readers that reject conversation reuse before a native corpus head exists."""

revision = "20261122_0188"
down_revision = "20261122_0187"
branch_labels = None
depends_on = None


def upgrade():
    # Existing receipts/events can now retain a conversation-only draft while
    # its owned World has no native source head. No stored content is changed.
    pass


def downgrade():
    raise RuntimeError(
        "Use forward recovery. Older readers cannot replay unavailable-corpus conversation drafts."
    )
