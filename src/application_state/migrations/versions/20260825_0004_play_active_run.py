"""play active_run singleton

Revision ID: 20260825_0004
Revises: 20260825_0003
Create Date: 2026-08-25

"""

from __future__ import annotations

from alembic import op

revision = "20260825_0004"
down_revision = "20260825_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE play.active_run (
            scope_key TEXT PRIMARY KEY
                CHECK (scope_key = 'local'),
            run_id UUID NOT NULL
                REFERENCES play.run (run_id),
            selected_at TIMESTAMPTZ NOT NULL
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS play.active_run")
