"""Fence older readers from native-body-aware Build selection events.

No user rows change. V1 events keep their historical writer input meaning.
"""
revision = "20261102_0104"
down_revision = "20261101_0103"
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    raise RuntimeError("Retained native body selections require recovery forward")
