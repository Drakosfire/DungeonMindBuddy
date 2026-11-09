"""Fence readers lacking Plan saved-page action and exact related-claim reconstruction."""
revision = '20261108_0140'
down_revision = '20261108_0139'
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    raise RuntimeError('Older readers cannot reconstruct Plan saved authored-page context')
