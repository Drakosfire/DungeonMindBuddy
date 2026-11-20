"""Reader fence for native object-unit query records; no retained rows change."""
revision = "20261105_0107"
down_revision = "20261105_0106"
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    raise RuntimeError("Native object retrieval records require recovery forward")
