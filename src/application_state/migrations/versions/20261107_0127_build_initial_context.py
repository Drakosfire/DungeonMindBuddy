"""Fence readers unable to reconstruct semantic-only fresh Build selection.

No rows or constraints change. Historical and reviewed admission remain exact.
"""
revision = "20261107_0127"
down_revision = "20261107_0126"
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    raise RuntimeError("Older readers cannot reconstruct semantic fresh Build input")
