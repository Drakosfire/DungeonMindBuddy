"""Fence readers unable to reconstruct request-local context qualifications."""
revision = '20261108_0134'
down_revision = '20261108_0133'
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    raise RuntimeError('Older readers cannot reconstruct context qualification dictionaries')
