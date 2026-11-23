"""Fence readers before native replies use generic limitation codes only."""

revision = '20261123_0205'
down_revision = '20261123_0203'
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    raise RuntimeError('Use forward recovery; older readers cannot decode current native reply limitations.')
