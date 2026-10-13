"""Add one nullable bounded selection anchor to the existing Plan action row."""

from alembic import op
import sqlalchemy as sa

revision = "20261012_0021"
down_revision = "20261012_0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE plan_action.action ADD COLUMN selection_anchor JSONB NULL")
    op.execute("""
        ALTER TABLE plan_action.action ADD CONSTRAINT plan_action_selection_anchor_check CHECK (
            selection_anchor IS NULL OR (
                CASE WHEN jsonb_typeof(selection_anchor) = 'object'
                    AND selection_anchor ?& ARRAY[
                        'schema_version', 'editor_format', 'editor_json_sha256',
                        'anchor', 'head', 'from', 'to', 'section'
                    ]
                    AND selection_anchor - ARRAY[
                        'schema_version', 'editor_format', 'editor_json_sha256',
                        'anchor', 'head', 'from', 'to', 'section'
                    ] = '{}'::jsonb
                    AND selection_anchor->>'schema_version' = 'dmb_plan_selection_anchor_v1'
                    AND selection_anchor->>'editor_format' = 'world-plan-tiptap-json-v1'
                    AND jsonb_typeof(selection_anchor->'editor_json_sha256') = 'string'
                    AND selection_anchor->>'editor_json_sha256' ~ '^[0-9a-f]{64}$'
                    AND jsonb_typeof(selection_anchor->'anchor') = 'number'
                    AND jsonb_typeof(selection_anchor->'head') = 'number'
                    AND jsonb_typeof(selection_anchor->'from') = 'number'
                    AND jsonb_typeof(selection_anchor->'to') = 'number'
                    AND selection_anchor->>'anchor' ~ '^(0|[1-9][0-9]{0,6})$'
                    AND selection_anchor->>'head' ~ '^(0|[1-9][0-9]{0,6})$'
                    AND selection_anchor->>'from' ~ '^(0|[1-9][0-9]{0,6})$'
                    AND selection_anchor->>'to' ~ '^(0|[1-9][0-9]{0,6})$'
                    AND octet_length(selection_anchor::text) <= 512
                THEN (
                    (selection_anchor->>'anchor')::bigint <= 1000000
                    AND (selection_anchor->>'head')::bigint <= 1000000
                    AND (selection_anchor->>'from')::bigint <= 1000000
                    AND (selection_anchor->>'to')::bigint <= 1000000
                    AND (selection_anchor->>'anchor')::bigint <> (selection_anchor->>'head')::bigint
                    AND (selection_anchor->>'from')::bigint = LEAST(
                        (selection_anchor->>'anchor')::bigint, (selection_anchor->>'head')::bigint)
                    AND (selection_anchor->>'to')::bigint = GREATEST(
                        (selection_anchor->>'anchor')::bigint, (selection_anchor->>'head')::bigint)
                    AND (
                        selection_anchor->'section' = 'null'::jsonb
                        OR CASE WHEN jsonb_typeof(selection_anchor->'section') = 'object'
                            AND selection_anchor->'section' ?& ARRAY['id', 'apply_from', 'apply_to']
                            AND (selection_anchor->'section') - ARRAY['id', 'apply_from', 'apply_to'] = '{}'::jsonb
                            AND selection_anchor->'section'->>'id' ~ '^heading:(0|[1-9][0-9]{0,6}):[1-6]$'
                            AND jsonb_typeof(selection_anchor->'section'->'apply_from') = 'number'
                            AND jsonb_typeof(selection_anchor->'section'->'apply_to') = 'number'
                            AND selection_anchor->'section'->>'apply_from' ~ '^(0|[1-9][0-9]{0,6})$'
                            AND selection_anchor->'section'->>'apply_to' ~ '^(0|[1-9][0-9]{0,6})$'
                        THEN (
                            (selection_anchor->'section'->>'apply_from')::bigint <= 1000000
                            AND (selection_anchor->'section'->>'apply_to')::bigint <= 1000000
                            AND split_part(selection_anchor->'section'->>'id', ':', 2)
                                = selection_anchor->'section'->>'apply_from'
                            AND (selection_anchor->'section'->>'apply_from')::bigint
                                <= (selection_anchor->>'from')::bigint
                            AND (selection_anchor->>'to')::bigint
                                <= (selection_anchor->'section'->>'apply_to')::bigint
                        ) ELSE FALSE END
                    )
                ) ELSE FALSE END
            ) IS TRUE
        )
    """)


def downgrade() -> None:
    if op.get_bind().execute(sa.text(
        "SELECT EXISTS (SELECT 1 FROM plan_action.action WHERE selection_anchor IS NOT NULL)"
    )).scalar_one():
        raise RuntimeError("refusing to downgrade while Plan selection anchors exist")
    op.execute("ALTER TABLE plan_action.action DROP CONSTRAINT plan_action_selection_anchor_check")
    op.execute("ALTER TABLE plan_action.action DROP COLUMN selection_anchor")
