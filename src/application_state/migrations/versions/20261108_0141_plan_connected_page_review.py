"""Fence readers lacking the explicit Plan connected-page review event and result."""
revision = '20261108_0141'
down_revision = '20261108_0140'
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    raise RuntimeError('Older readers cannot reconstruct Plan connected-page reviews')
