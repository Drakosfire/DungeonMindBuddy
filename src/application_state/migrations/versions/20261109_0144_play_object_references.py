"""Fence older readers that reject native Play object reference selections.

No tables, user rows, source bytes, Run editions or historical receipts change.
"""
revision = '20261109_0144'
down_revision = '20261109_0143'
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    raise RuntimeError('Use recovery forward with a forward migration; older readers cannot reconstruct native Play object references')
