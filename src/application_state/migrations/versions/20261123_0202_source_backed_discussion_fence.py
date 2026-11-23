"""Fence readers before factual Build discussion retains its typed-source policy."""

revision = '20261123_0202'
down_revision = '20261123_0201'
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    raise RuntimeError('Use forward recovery; older readers cannot replay typed-source Build discussion.')
