"""Fence readers which cannot decode stored statblock passage evidence."""

revision = "20261126_0197"
down_revision = "20261123_0196"
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    raise RuntimeError("Stored statblock conversations require a compatible forward reader")
