"""admit runbook as a Content kind

Revision ID: 20260825_0002
Revises: 20260825_0001
Create Date: 2026-08-25

"""

from __future__ import annotations

from alembic import op

revision = "20260825_0002"
down_revision = "20260825_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE content.work_object DROP CONSTRAINT IF EXISTS work_object_kind_check")
    op.execute(
        """
        ALTER TABLE content.work_object
            ADD CONSTRAINT work_object_kind_check
            CHECK (kind IN ('plan', 'runbook'))
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE content.work_object DROP CONSTRAINT IF EXISTS work_object_kind_check")
    op.execute(
        """
        ALTER TABLE content.work_object
            ADD CONSTRAINT work_object_kind_check
            CHECK (kind = 'plan')
        """
    )
