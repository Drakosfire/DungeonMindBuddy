"""Fence readers before retaining composed Plan caret nominations."""

revision = "20261122_0189"
down_revision = "20261122_0188"
branch_labels = None
depends_on = None


def upgrade():
    # The retained nomination can select a composed caret boundary. Existing
    # rows stay intact. Older readers cannot reconstruct this decision.
    pass


def downgrade():
    raise RuntimeError(
        "Use forward recovery. Older Plan readers cannot replay composed caret insertions."
    )
