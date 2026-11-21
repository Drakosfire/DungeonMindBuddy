"""Fence older readers from versioned composed Plan column scope."""

revision = "20261122_0177"
down_revision = "20261121_0176"
branch_labels = None
depends_on = None


def upgrade():
    # The application schema guards the new retained opening interpretation.
    pass


def downgrade():
    raise RuntimeError(
        "Use forward recovery. Older Plan readers cannot replay composed column scope."
    )
