"""Fence readers unable to reconstruct current shared relevance request codecs."""
revision = '20261108_0131'
down_revision = '20261108_0130'
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    raise RuntimeError('Older readers cannot reconstruct shared relevance decision inputs')
