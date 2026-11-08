"""Fence readers unable to reconstruct the current native uncertainty codec."""
revision = '20261108_0132'
down_revision = '20261108_0130'
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    raise RuntimeError('Older readers cannot reconstruct native uncertainty output')
