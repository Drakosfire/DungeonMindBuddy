"""Fence older readers of request-admitted combined Plan opening decisions.

The existing native JSON storage owner covers these records. No table or source
row changes; actual request/SDK/selection validation stays with Python owners.
"""
revision = '20261109_0147'
down_revision = '20261109_0146'
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    raise RuntimeError('Use forward recovery; older readers cannot reconstruct Plan opening admission')
