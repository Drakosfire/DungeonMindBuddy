"""Fence readers unable to reconstruct semantic World qualification envelopes."""
revision = '20261108_0133'
down_revision = '20261108_0131'
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    raise RuntimeError('Older readers cannot reconstruct semantic World qualifications')
