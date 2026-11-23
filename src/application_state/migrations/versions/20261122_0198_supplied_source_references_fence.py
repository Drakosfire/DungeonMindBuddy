"""Fence readers before binding Build citations to supplied source references."""
revision = "20261122_0198"
down_revision = "20261122_0197"
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    raise RuntimeError("Use forward recovery: older readers require regenerated source quotes.")
