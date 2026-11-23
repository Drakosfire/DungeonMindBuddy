"""Fence readers before persisting retained Build discussion admissions."""

revision = "20261122_0195"
down_revision = "20261122_0194"
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    raise RuntimeError("Use forward recovery: older readers cannot reopen retained conversations.")
