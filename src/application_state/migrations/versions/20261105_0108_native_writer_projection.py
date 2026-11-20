"""Reader fence for compact native writer inputs; no retained rows change."""
revision = "20261105_0108"
down_revision = "20261105_0107"
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    raise RuntimeError("Native writer projection records require recovery forward")
