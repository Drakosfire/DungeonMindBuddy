"""Fence readers before persisting full retained Build conversation admissions."""

revision = "20261122_0193"
down_revision = "20261122_0192"
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    raise RuntimeError("Use forward recovery: older readers cannot reopen retained conversations.")
