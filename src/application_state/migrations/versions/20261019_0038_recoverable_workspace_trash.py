"""Add durable reversible lifecycle state for World-owned Play sessions."""

from alembic import op

revision = "20261019_0038"
down_revision = "20261018_0037"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE play.run
        ADD COLUMN lifecycle_status TEXT NOT NULL DEFAULT 'active'
            CHECK (lifecycle_status IN ('active','trashed'))
    """)


def downgrade() -> None:
    op.execute("LOCK TABLE play.run IN ACCESS EXCLUSIVE MODE")
    if (
        op.get_bind()
        .exec_driver_sql(
            "SELECT EXISTS (SELECT 1 FROM play.run WHERE lifecycle_status <> 'active')"
        )
        .scalar_one()
    ):
        raise RuntimeError("refusing to discard recoverable Play Trash state")
    op.execute("ALTER TABLE play.run DROP COLUMN lifecycle_status")
