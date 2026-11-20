"""Fence readers unable to reconstruct semantic-only native navigation requests.

No rows or constraints change. Retained pre-V3 requests keep their exact codec.
"""
revision = "20261107_0125"
down_revision = "20261107_0124"
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    raise RuntimeError("Older readers cannot reconstruct semantic-only native navigation")
