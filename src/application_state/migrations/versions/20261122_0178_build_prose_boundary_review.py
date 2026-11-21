"""Admit retained Build prose boundaries and fence older readers."""

from alembic import op

revision = "20261122_0178"
down_revision = "20261122_0177"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        ALTER TABLE agent.build_proposal
        DROP CONSTRAINT build_proposal_schema_variant,
        ADD CONSTRAINT build_proposal_schema_variant CHECK(
            payload->>'schema_version' IN (
                'dmb_build_document_proposal_v1', 'dmb_build_image_preparation_v2'
            ) OR (
                payload->>'schema_version'='dmb_build_document_proposal_v3'
                AND jsonb_typeof(payload->'reservation'->'prose_target') IS NOT DISTINCT FROM 'object'
            )
        )
    """)
    op.execute("""
        ALTER TABLE agent.build_proposal_review
        DROP CONSTRAINT build_review_current_placement,
        ADD CONSTRAINT build_review_current_placement CHECK(
            payload->>'schema' IN (
                'dmb_build_proposal_review_v2', 'dmb_build_proposal_review_v3',
                'dmb_build_proposal_review_v5'
            )
            AND jsonb_typeof(payload->'placement_caret')='number'
            AND (payload->>'placement_caret')::numeric >= 0
            AND (payload->>'placement_caret')::numeric = trunc((payload->>'placement_caret')::numeric)
            AND (payload->>'schema'<>'dmb_build_proposal_review_v3' OR (
                jsonb_typeof(payload->'placement')='object'
                AND jsonb_typeof(payload->'retired_placements')='array'
                AND jsonb_array_length(payload->'retired_placements')>0
            ))
            AND (payload->>'schema'<>'dmb_build_proposal_review_v5'
                OR jsonb_typeof(payload->'prose_target') IS NOT DISTINCT FROM 'object')
        )
    """)


def downgrade():
    raise RuntimeError("Use forward recovery. Older Build readers cannot retain prose boundaries.")
