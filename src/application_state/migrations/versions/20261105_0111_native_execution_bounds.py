"""Reader fence for shared execution history; no retained row rewrites."""
revision = "20261105_0111"
down_revision = "20261105_0110"
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    raise RuntimeError("Shared native execution history requires recovery forward")
