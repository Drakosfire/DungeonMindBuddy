"""Fence older readers when managed Worlds switch to their sole DB owner."""
revision = "20261031_0100"
down_revision = "20261030_0099"
branch_labels = None
depends_on = None


def upgrade():
    # No data rewrite or file adoption. Delivery explicitly adopts exact metadata
    # while the old writer is stopped before starting this runtime.
    pass


def downgrade():
    raise RuntimeError("World catalog cutover requires explicit recovery forward")
