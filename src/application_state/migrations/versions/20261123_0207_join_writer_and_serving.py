"""Join reviewed writer readers with the existing portrait serving history."""

revision = '20261123_0207'
down_revision = ('20261123_0206', '20261123_0204')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    raise RuntimeError('Use forward recovery; prior serving readers cannot decode current writer replies.')
