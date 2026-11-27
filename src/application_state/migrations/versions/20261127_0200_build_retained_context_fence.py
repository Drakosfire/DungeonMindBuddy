"""Fence readers before persisting full retained Build conversation and discussion admissions."""

revision = "20261127_0200"
down_revision = "20261126_0199"
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    raise RuntimeError("Use forward recovery: older readers cannot reopen retained conversations.")
