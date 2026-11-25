"""Fence readers before pending Build saves paragraph proposal completions."""

revision = '20261125_0214'
down_revision = '20261125_0213'
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    raise RuntimeError('Use forward recovery; prior readers cannot decode pending paragraph proposals.')
