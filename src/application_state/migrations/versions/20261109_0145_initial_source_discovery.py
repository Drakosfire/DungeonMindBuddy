"""Fence older readers that cannot reconstruct request-owned source discovery.

No tables, user rows, source bytes or historical receipts change.
"""
revision = '20261109_0145'
down_revision = '20261109_0144'
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    raise RuntimeError('Use recovery forward; older readers cannot reconstruct initial source discovery')
