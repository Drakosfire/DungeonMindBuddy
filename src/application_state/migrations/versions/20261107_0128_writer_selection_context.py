"""Fence readers unable to reconstruct semantic native evidence selection.

No retained rows or constraints change; historical selection wire remains exact.
"""
revision = "20261107_0128"
down_revision = "20261107_0127"
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    raise RuntimeError("Older readers cannot reconstruct semantic evidence selection")
