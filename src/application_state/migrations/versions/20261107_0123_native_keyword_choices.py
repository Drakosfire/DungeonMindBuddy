"""Fence readers that cannot reconstruct acknowledged keyword navigation hints.

No rows or constraints change. Earlier readers must not silently omit a new
selection action or reject the prepared keyword decision during recovery.
"""
revision = "20261107_0123"
down_revision = "20261107_0122"
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    raise RuntimeError("Older readers cannot recover native keyword choices")
