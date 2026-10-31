"""Typed authored pages reuse Content revisions; no live page adoption."""

from alembic import op

revision = "20261031_0101"
down_revision = "20261031_0100"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE content.work_object DROP CONSTRAINT work_object_kind_check")
    op.execute("""ALTER TABLE content.work_object ADD CONSTRAINT work_object_kind_check
        CHECK (kind IN ('plan','runbook','worldbuilding_source'))""")
    op.execute(
        "ALTER TABLE content.work_object DROP CONSTRAINT work_object_scope_check"
    )
    op.execute("""ALTER TABLE content.work_object ADD CONSTRAINT work_object_scope_check CHECK (
        (kind IN ('plan','runbook') AND campaign_id IS NOT NULL
            AND btrim(campaign_id) <> '' AND world_id IS NULL)
        OR (campaign_id IS NULL AND world_id IS NOT NULL AND btrim(world_id) <> ''
            AND target_session IS NULL))""")
    op.execute("""CREATE TABLE content.page_metadata (
        work_object_id UUID PRIMARY KEY REFERENCES content.work_object(work_object_id),
        document_class TEXT,
        authority_state TEXT NOT NULL CHECK (authority_state IN ('draft','reviewed','canonical')),
        visibility_state TEXT NOT NULL CHECK (visibility_state IN ('internal','player_safe')),
        connected_page_operation_id UUID UNIQUE
    )""")


def downgrade():
    raise RuntimeError("Authored page storage requires explicit recovery forward")
