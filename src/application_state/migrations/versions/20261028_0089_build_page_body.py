"""Fence readers for reviewed whole-page targets; retain all prior payload bytes."""
revision = "20261028_0089"
down_revision = "20261028_0088"
branch_labels = None
depends_on = None


def upgrade():
    # Existing schema-head admission fences incompatible strict JSON readers.
    pass


def downgrade():
    raise RuntimeError("Retained whole-page targets require recovery forward")
