"""Fence versioned current-request lore review readers; stored records are unchanged."""
revision = '20261123_0208'
down_revision = '20261123_0207'
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    raise RuntimeError('Use forward recovery; prior readers cannot decode request-reference lore replies.')
