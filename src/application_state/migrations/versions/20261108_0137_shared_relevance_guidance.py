"""Fence readers unable to reconstruct shared controller relevance guidance."""
revision = '20261108_0137'
down_revision = '20261108_0136'
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    raise RuntimeError('Older readers cannot reconstruct shared relevance guidance')
