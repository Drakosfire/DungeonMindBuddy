"""Fence older readers from token-admitted Build controller decisions.

No user rows change. Historical accounting descriptors retain their meaning.
"""
revision = "20261103_0105"
down_revision = "20261102_0104"
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    raise RuntimeError("Retained token-admitted Build decisions require recovery forward")
