"""Fence readers lacking the acquired-record Plan controller input contract."""
revision = '20261109_0143'
down_revision = '20261109_0142'
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    raise RuntimeError('Older readers cannot reconstruct acquired-record Plan decisions')
