"""Fence pending chat drafts; existing stored records are unchanged."""
revision = '20261125_0212'
down_revision = '20261125_0211'
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    raise RuntimeError('Use forward recovery; prior readers cannot decode pending conversation drafts.')
