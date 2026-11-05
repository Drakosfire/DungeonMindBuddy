"""Reader fence for reference-aware native Plan intents; no retained row rewrites."""
revision = "20261105_0109"
down_revision = "20261105_0108"
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    raise RuntimeError("Reference-aware Plan records require recovery forward")
