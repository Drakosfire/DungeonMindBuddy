"""Fence older readers from Plan continuation passage admission records."""

revision = "20261122_0185"
down_revision = "20261122_0184"
branch_labels = None
depends_on = None


def upgrade():
    # The application schema version fences the new selection field.
    pass


def downgrade():
    raise RuntimeError(
        "Use forward recovery. Older Plan readers cannot replay acquired passage admission."
    )
