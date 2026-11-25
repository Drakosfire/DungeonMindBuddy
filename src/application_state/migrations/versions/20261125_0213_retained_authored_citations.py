"""Fence retained saved-page citation presentation; existing records are unchanged."""
revision = "20261125_0213"
down_revision = "20261125_0212"
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    raise RuntimeError("Retained saved-page citations require a compatible forward reader")
