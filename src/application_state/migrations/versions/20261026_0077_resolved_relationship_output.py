"""Fence readers after resolved relationship output grammar adoption; no row rewrite."""
revision = '20261026_0077'
down_revision = '20261026_0076'
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    # Normalized completions cannot prove absence from prepared packets or traces.
    raise RuntimeError('Resolved relationship output adoption requires recovery forward')
