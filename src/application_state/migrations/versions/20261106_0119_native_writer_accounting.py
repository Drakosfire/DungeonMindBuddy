"""Fence older readers before native estimated writer budgets are persisted."""

revision = "20261106_0119"
down_revision = "20261106_0118"
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    raise RuntimeError("Older readers cannot interpret native estimated writer budgets")
