"""Fence semantic Build writer requests; existing stored replies are unchanged."""
revision = '20261124_0210'
down_revision = '20261123_0209'
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    raise RuntimeError('Use forward recovery; prior readers cannot decode semantic Build replies.')
