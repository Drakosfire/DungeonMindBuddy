"""Fence readers before Build background requests use the evolved source scope question."""

revision = '20261123_0206'
down_revision = '20261123_0205'
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    raise RuntimeError('Use forward recovery; older readers do not recognize current Build source scope instructions.')
