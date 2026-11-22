"""Fence older readers before retaining Plan author requests with editor focus."""

revision = "20261122_0192"
down_revision = "20261122_0191"
branch_labels = None
depends_on = None


def upgrade():
    # The new request carries a small focus classification for exact replay.
    pass


def downgrade():
    raise RuntimeError(
        "Use forward recovery. Older Plan readers cannot reopen author requests with editor focus."
    )
