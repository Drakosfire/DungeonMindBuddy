"""Fence readers unable to reconstruct semantic Plan work and local selectors."""
revision = '20261108_0130'
down_revision = '20261107_0129'
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    raise RuntimeError('Older readers cannot reconstruct semantic native Plan work')
