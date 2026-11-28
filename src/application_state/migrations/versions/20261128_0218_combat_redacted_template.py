"""Retain original Combat pins when a statblock deletion redacts their payload."""

from alembic import op

revision = "20261128_0218"
down_revision = "20261128_0217"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        ALTER TABLE combat.scene_template_version ADD COLUMN redacted_digest text
            CHECK (redacted_digest ~ '^sha256:[0-9a-f]{64}$')
    """)


def downgrade():
    op.execute("LOCK TABLE combat.scene_template_version IN ACCESS EXCLUSIVE MODE")
    if op.get_bind().exec_driver_sql(
        "SELECT EXISTS (SELECT FROM combat.scene_template_version WHERE redacted_digest IS NOT NULL)"
    ).scalar_one():
        raise RuntimeError("Cannot discard redacted Combat template verification digests")
    op.execute("ALTER TABLE combat.scene_template_version DROP COLUMN redacted_digest")
