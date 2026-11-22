"""Fence prior APP readers from partitioned native Plan recap catalogs."""

revision = "20261122_0186"
down_revision = "20261122_0185"
branch_labels = None
depends_on = None


def upgrade():
    # Readiness compares the installed version before native catalog writes.
    pass


def downgrade():
    raise RuntimeError("Use forward recovery. Older readers cannot replay partitioned recap catalogs.")
