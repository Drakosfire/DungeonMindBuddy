"""Fence readers for reviewed page-end insertion; preserve all retained payloads."""
revision = "20261029_0090"
down_revision = "20261028_0089"
branch_labels = None
depends_on = None


def upgrade():
    # Existing schema-head admission fences incompatible strict JSON readers.
    pass


def downgrade():
    raise RuntimeError("Retained page-end targets require recovery forward")
