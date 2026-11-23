"""Join the empty-paragraph reader fence with the serving migration lineage."""

revision = "20261123_0200"
down_revision = ("20261123_0194", "20261122_0198")
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    raise RuntimeError("Use forward recovery to preserve page presentation and serving state.")
