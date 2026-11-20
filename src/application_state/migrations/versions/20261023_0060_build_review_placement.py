"""Persist author-selected review placement without changing generated evidence."""

from alembic import op

revision = "20261023_0060"
down_revision = "20261023_0059"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""DO $$ DECLARE item record; BEGIN
      FOR item IN SELECT conname FROM pg_constraint
        WHERE conrelid='agent.build_proposal_review'::regclass
        AND pg_get_constraintdef(oid) LIKE '%dmb_build_proposal_review_v1%'
      LOOP EXECUTE format('ALTER TABLE agent.build_proposal_review DROP CONSTRAINT %I', item.conname); END LOOP;
    END $$""")
    op.execute("""UPDATE agent.build_proposal_review r SET payload =
      jsonb_set(jsonb_set(r.payload, '{schema}', '"dmb_build_proposal_review_v2"'),
        '{placement_caret}', p.payload #> '{reservation,basis,caret}') ||
      CASE WHEN r.payload->'apply' IS NOT NULL AND r.payload->'apply' != 'null'::jsonb
        THEN jsonb_build_object('apply', r.payload->'apply' || jsonb_build_object(
          'placement_caret',p.payload #> '{reservation,basis,caret}'))
        ELSE '{}'::jsonb END
      FROM agent.build_proposal p WHERE p.action_id=r.action_id AND p.world_id=r.world_id""")
    op.execute("""ALTER TABLE agent.build_proposal_review ADD CONSTRAINT build_review_current_placement CHECK(
      payload->>'schema'='dmb_build_proposal_review_v2' AND payload ? 'placement_caret'
      AND jsonb_typeof(payload->'placement_caret')='number'
      AND (payload->>'placement_caret')::numeric >= 0
      AND (payload->>'placement_caret')::numeric = trunc((payload->>'placement_caret')::numeric))""")


def downgrade():
    raise RuntimeError(
        "Author-selected review placement cannot be downgraded without losing its meaning"
    )
