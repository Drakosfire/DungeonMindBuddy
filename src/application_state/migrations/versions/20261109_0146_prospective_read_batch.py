"""Fence readers unable to reconstruct prospective final read batches.

No tables or retained source/user rows change.
"""
revision = '20261109_0146'
down_revision = '20261109_0145'
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    raise RuntimeError('Use forward recovery; older readers cannot reconstruct prospective read batches')
