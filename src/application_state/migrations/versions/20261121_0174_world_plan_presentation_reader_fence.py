"""Fence older Plan readers before accepting revision-bound presentation."""

revision = "20261121_0174"
down_revision = "20261121_0173"
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    raise RuntimeError(
        "Use forward recovery. Older Plan readers and writers cannot retain Plan presentation."
    )
