"""Fence older readers before direct native source acquisitions are persisted."""
revision = "20261106_0118"
down_revision = "20261105_0117"
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    raise RuntimeError("Older readers cannot interpret direct native source acquisitions")
