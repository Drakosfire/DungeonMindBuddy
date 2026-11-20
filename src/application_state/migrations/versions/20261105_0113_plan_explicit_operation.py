"""Reader fence for explicit native Plan operations; no retained row rewrites."""
revision = "20261105_0113"
down_revision = "20261105_0112"
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    raise RuntimeError("Explicit Plan operation history requires recovery forward")
