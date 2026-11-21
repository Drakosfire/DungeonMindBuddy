"""Fence older readers before recording V2 Plan paragraph placement catalogs."""

revision = "20261120_0172"
down_revision = "20261120_0171"
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    raise RuntimeError(
        "Use forward recovery. Older readers cannot read V2 Plan paragraph placement catalogs."
    )
