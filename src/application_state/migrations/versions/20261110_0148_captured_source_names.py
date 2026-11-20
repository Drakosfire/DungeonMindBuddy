"""Fence readers unable to reconstruct captured native source display names.

Only the existing native catalog JSON carries the additive presentation field.
No retained rows, tables or source authority change. The existing schema-head
check refuses older readers before they encounter the new records.
"""
revision = '20261110_0148'
down_revision = '20261109_0147'
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    raise RuntimeError('Use forward recovery; older readers cannot reconstruct captured source names')
