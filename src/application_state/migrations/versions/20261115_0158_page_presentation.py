"""Revision-bound Page presentation; forward-only reader compatibility fence."""

from alembic import op

revision = "20261115_0158"
down_revision = "20261112_0157"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""CREATE TABLE content.page_presentation (
        work_revision_id uuid PRIMARY KEY REFERENCES content.work_revision(work_revision_id),
        payload jsonb NOT NULL CHECK (jsonb_typeof(payload) = 'object'),
        presentation_sha256 text NOT NULL CHECK (presentation_sha256 ~ '^[0-9a-f]{64}$')
    )""")


def downgrade():
    raise RuntimeError(
        "Forward recovery required: old writers cannot retain Page presentation"
    )
