"""Fence older readers from Plan recap prose deduplication proofs."""

revision = "20261122_0185"
down_revision = "20261122_0184"
branch_labels = None
depends_on = None


def upgrade():
    # The application schema version fences the new writer authorization field.
    pass


def downgrade():
    raise RuntimeError(
        "Use forward recovery. Older Plan readers cannot replay deduplicated recap prose."
    )
