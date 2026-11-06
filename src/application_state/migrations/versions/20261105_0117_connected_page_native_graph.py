"""Fence retired connected-page writers before native operation persistence."""
revision = "20261105_0117"
down_revision = "20261105_0116"
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    raise RuntimeError("Retired connected-page writers cannot read native operation receipts")
