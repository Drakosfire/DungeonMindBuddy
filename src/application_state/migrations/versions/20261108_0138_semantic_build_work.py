"""Fence readers lacking semantic Build work and complete-work authorization."""
revision = '20261108_0138'
down_revision = '20261108_0137'
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    raise RuntimeError('Older readers cannot reconstruct committed semantic Build work')
