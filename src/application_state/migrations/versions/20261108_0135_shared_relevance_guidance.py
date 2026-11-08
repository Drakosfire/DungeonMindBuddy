"""Fence readers unable to reconstruct shared controller relevance guidance."""
revision = '20261108_0135'
down_revision = '20261108_0134'
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    raise RuntimeError('Older readers cannot reconstruct shared relevance guidance')
