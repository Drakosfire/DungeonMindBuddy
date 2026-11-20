"""Fence readers that cannot route acknowledged native scope expansion.

No rows or constraints change. Old code must not resume a new selection handle
as a source read or silently omit its expanded navigation on recovery.
"""
revision = "20261107_0122"
down_revision = "20261106_0121"
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    raise RuntimeError("Older readers cannot recover native source scope expansion")
