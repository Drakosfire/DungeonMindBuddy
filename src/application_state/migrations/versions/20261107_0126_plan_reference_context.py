"""Fence readers unable to reconstruct semantic-only Plan reference context.

No rows or constraints change. Retained V1-V5 parent codecs remain exact.
"""
revision = "20261107_0126"
down_revision = "20261107_0125"
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    raise RuntimeError("Older readers cannot reconstruct semantic Plan reference context")
