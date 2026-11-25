"""Fence readers before pending Build saves placement clarification."""

revision = '20261125_0213'
down_revision = '20261125_0212'
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    raise RuntimeError('Use forward recovery; prior readers cannot decode pending placement clarification.')
