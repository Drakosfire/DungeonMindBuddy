"""Fence readers unable to reconstruct semantic native evidence and aliases."""
revision = '20261107_0129'
down_revision = '20261107_0128'
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    raise RuntimeError('Older readers cannot reconstruct semantic native evidence')
