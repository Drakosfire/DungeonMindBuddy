"""Fence meaningful lore outcomes; prior stored replies are unchanged."""
revision = '20261123_0209'
down_revision = '20261123_0208'
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    raise RuntimeError('Use forward recovery; prior readers cannot decode meaningful lore outcomes.')
