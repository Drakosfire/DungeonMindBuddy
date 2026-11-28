"""Fence stored statblock evidence and pending saved-statblock events."""
revision = "20261128_0219"
down_revision = "20261128_0218"
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    raise RuntimeError("Stored statblock conversations require a compatible forward reader")
