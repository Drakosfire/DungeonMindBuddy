"""Fence readers before a Plan opening can retain an unstated insertion location."""

revision = "20261122_0188"
down_revision = "20261122_0187"
branch_labels = None
depends_on = None


def upgrade():
    # The new author interpretation can resolve to an existing capture. Older
    # readers cannot revalidate that result. No DDL or row rewrite is needed.
    pass


def downgrade():
    raise RuntimeError(
        "Use forward recovery. Older Plan readers cannot replay implicit caret insertion."
    )
