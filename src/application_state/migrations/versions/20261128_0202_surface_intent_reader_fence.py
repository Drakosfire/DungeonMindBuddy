"""Fence older readers before persisting Plan and Play opening intent."""

revision = "20261128_0202"
down_revision = "20261127_0201"
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    raise RuntimeError("Saved surface intent requires a compatible forward reader")
