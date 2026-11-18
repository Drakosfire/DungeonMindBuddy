"""Fence older readers of PDF-backed mechanics revision intents."""

revision = "20261111_0156"
down_revision = "20261111_0155"
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    raise RuntimeError("Older readers cannot reconstruct PDF-backed mechanics revision intents")
