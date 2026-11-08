"""Fence readers unable to reconstruct packed native assertion qualifications."""
revision = '20261108_0131'
down_revision = '20261108_0130'
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    raise RuntimeError('Older readers cannot reconstruct native qualification dictionaries')
