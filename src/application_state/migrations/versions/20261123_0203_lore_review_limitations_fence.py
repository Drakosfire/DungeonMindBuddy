"""Fence readers before lore reviews retain generic optional-gap fallback policy."""

revision = '20261123_0203'
down_revision = '20261123_0202'
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    raise RuntimeError('Use forward recovery; older readers cannot replay current lore review limitations.')
