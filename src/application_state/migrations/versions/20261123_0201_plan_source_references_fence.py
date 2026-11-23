"""Fence readers before Plan replies retain supplied-page reference contracts."""

revision = '20261123_0201'
down_revision = '20261123_0200'
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    raise RuntimeError('Use forward recovery; older readers cannot reopen Plan source-reference replies.')
