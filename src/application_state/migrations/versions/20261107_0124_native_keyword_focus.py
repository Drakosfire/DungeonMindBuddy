"""Fence readers that cannot reconstruct retained keyword-focus prepared input.

No rows or constraints change. Earlier readers project these metadata rows as
examined subjects rather than reconstructing their exact captured decision wire.
"""
revision = "20261107_0124"
down_revision = "20261107_0123"
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    raise RuntimeError("Older readers cannot recover retained keyword focus")
