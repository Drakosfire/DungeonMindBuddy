"""Plan-native authoring origin; proposal bytes belong to one inert Plan action result."""
from alembic import op
import sqlalchemy as sa

revision = '20261026_0078'
down_revision = '20261026_0077'
branch_labels = None
depends_on = None


def upgrade():
    op.execute('ALTER TABLE plan_action.action ADD COLUMN authoring_origin JSONB NULL')
    op.execute('ALTER TABLE plan_action.action ADD COLUMN authoring_review JSONB NULL')
    op.execute("""
        ALTER TABLE plan_action.action ADD CONSTRAINT plan_action_authoring_origin_check CHECK (
          authoring_origin IS NULL OR (
            consultation IS NULL
            AND jsonb_typeof(authoring_origin) = 'object'
            AND authoring_origin ?& ARRAY['schema','action_id','idempotency_key','action_request_fingerprint',
                'action_fence','basis','conversation_id','turn_id','product_attempt','expected_pointer_revision',
                'context_receipt_sha256','execution_policy_sha256','capture_sha256','controller_attempt_id','selection_event_id']
            AND authoring_origin->>'action_id' = action_id::text
            AND authoring_origin->>'idempotency_key' = idempotency_key::text
            AND authoring_origin->>'action_request_fingerprint' = request_fingerprint
            AND authoring_origin->'basis'->>'world_id' = world_id
            AND authoring_origin->'basis'->>'document_id' = document_id
            AND authoring_origin->'basis'->>'object_revision' = object_revision::text
            AND authoring_origin->'basis'->>'work_revision_id' = work_revision_id::text
            AND authoring_origin->'basis'->>'revision_n' = revision_n::text
            AND authoring_origin->'basis'->>'content_sha256' = content_sha256
            AND authoring_origin->>'capture_sha256' ~ '^[a-f0-9]{64}$'
            AND (
              (authoring_origin->>'schema' = 'dmb_plan_jev_authoring_reservation_v1'
                AND status IN ('pending','failed','indeterminate'))
              OR (authoring_origin->>'schema' = 'dmb_plan_action_authoring_result_v1'
                AND status = 'completed'
                AND authoring_origin ?& ARRAY['expected_turn_revision','writer_attempt_id',
                    'writer_envelope_sha256','raw_reply_sha256','evidence_event_ids','replacement_markdown_sha256',
                    'capture','replacement_markdown','agent_result_sha256']
                AND jsonb_typeof(authoring_origin->'evidence_event_ids') = 'array'
                AND jsonb_typeof(authoring_origin->'capture') = 'object'
                AND jsonb_typeof(authoring_origin->'replacement_markdown') = 'string'
                AND authoring_origin->>'agent_result_sha256' ~ '^[a-f0-9]{64}$'
                AND authoring_origin->>'action_fence' = fence::text
                AND authoring_origin->>'replacement_markdown_sha256' ~ '^[a-f0-9]{64}$')
            )
          ) IS TRUE
        )
    """)
    op.execute("""
        CREATE UNIQUE INDEX plan_authoring_one_result_per_attempt
        ON plan_action.action (world_id, (authoring_origin->>'turn_id'), (authoring_origin->>'product_attempt'))
        WHERE authoring_origin IS NOT NULL
    """)
    op.execute("""ALTER TABLE plan_action.action ADD CONSTRAINT plan_authoring_review_owner_check CHECK (
        authoring_review IS NULL OR (
            status='completed' AND authoring_origin->>'schema'='dmb_plan_action_authoring_result_v1'
            AND jsonb_typeof(authoring_review)='object'
            AND authoring_review ?& ARRAY['schema','world_id','action_id','origin_sha256','revision','state',
                'markdown','markdown_sha256','capture','applications','last_command_id','last_command_sha256','updated_at']
            AND authoring_review->>'schema'='dmb_plan_authoring_review_v1'
            AND authoring_review->>'action_id'=action_id::text
            AND authoring_review->>'world_id'=world_id
            AND authoring_review->'capture'->>'document_id'=document_id
            AND jsonb_typeof(authoring_review->'applications')='array'
            AND jsonb_typeof(authoring_review->'revision')='number'
            AND (authoring_review->>'revision')::bigint > 0
        ) IS TRUE
    )""")


def downgrade():
    if op.get_bind().execute(sa.text('SELECT EXISTS (SELECT 1 FROM plan_action.action WHERE authoring_origin IS NOT NULL)')).scalar_one():
        raise RuntimeError('Plan authoring origins require recovery forward')
    op.execute('ALTER TABLE plan_action.action DROP CONSTRAINT plan_authoring_review_owner_check')
    op.execute('ALTER TABLE plan_action.action DROP COLUMN authoring_review')
    op.execute('DROP INDEX plan_action.plan_authoring_one_result_per_attempt')
    op.execute('ALTER TABLE plan_action.action DROP CONSTRAINT plan_action_authoring_origin_check')
    op.execute('ALTER TABLE plan_action.action DROP COLUMN authoring_origin')
