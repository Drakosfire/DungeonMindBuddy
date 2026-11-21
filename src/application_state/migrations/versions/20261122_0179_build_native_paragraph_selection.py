"""Fence older readers before native Build retains paragraph selections."""

revision = "20261122_0179"
down_revision = "20261122_0178"
branch_labels = None
depends_on = None


def upgrade():
    # The existing application schema guard binds readers to the Alembic head.
    # Both new fields live inside existing, separately validated JSON records.
    pass


def downgrade():
    raise RuntimeError("Use forward recovery. Older Build readers cannot retain paragraph selections.")
