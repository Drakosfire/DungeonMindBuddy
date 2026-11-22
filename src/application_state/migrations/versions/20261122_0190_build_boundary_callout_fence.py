"""Fence readers before retaining Build boundary proposals with semantic callouts."""

revision = "20261122_0190"
down_revision = "20261122_0189"
branch_labels = None
depends_on = None


def upgrade():
    # Older readers only accept a single paragraph in this retained review.
    pass


def downgrade():
    raise RuntimeError(
        "Use forward recovery. Older Build readers cannot reopen callout boundary proposals."
    )
