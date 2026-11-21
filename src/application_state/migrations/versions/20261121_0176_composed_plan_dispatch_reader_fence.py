"""Fence older readers from persisted composed Plan opening records."""

revision = "20261121_0176"
down_revision = "20261121_0175"
branch_labels = None
depends_on = None


def upgrade():
    # The application schema version guards the new durable event and catalog.
    pass


def downgrade():
    raise RuntimeError(
        "Use forward recovery. Older Plan readers cannot replay composed opening records."
    )
