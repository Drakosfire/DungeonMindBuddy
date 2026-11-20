"""Reader fence for exact under-heading Plan placement; no row rewrites."""
revision = "20261105_0112"
down_revision = "20261105_0111"
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    raise RuntimeError("Under-heading Plan placement history requires recovery forward")
