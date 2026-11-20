"""Retain explicit fresh placements and unresolved predecessor receipts."""
from alembic import op
revision = "20261025_0069"
down_revision = "20261025_0068"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE agent.build_proposal_review DROP CONSTRAINT build_review_current_placement")
    op.execute("""ALTER TABLE agent.build_proposal_review ADD CONSTRAINT build_review_current_placement CHECK(
        payload->>'schema' IN ('dmb_build_proposal_review_v2','dmb_build_proposal_review_v3')
        AND jsonb_typeof(payload->'placement_caret')='number'
        AND (payload->>'placement_caret')::numeric >= 0
        AND (payload->>'placement_caret')::numeric = trunc((payload->>'placement_caret')::numeric)
        AND (payload->>'schema'<>'dmb_build_proposal_review_v3' OR
            (jsonb_typeof(payload->'placement')='object' AND jsonb_typeof(payload->'retired_placements')='array'
             AND jsonb_array_length(payload->'retired_placements')>0)))""")


def downgrade():
    op.execute("LOCK TABLE agent.build_proposal_review IN ACCESS EXCLUSIVE MODE")
    if op.get_bind().exec_driver_sql("SELECT EXISTS(SELECT 1 FROM agent.build_proposal_review WHERE payload->>'schema'='dmb_build_proposal_review_v3')").scalar_one():
        raise RuntimeError("Retained replacement placements require recovery forward")
    op.execute("ALTER TABLE agent.build_proposal_review DROP CONSTRAINT build_review_current_placement")
    op.execute("""ALTER TABLE agent.build_proposal_review ADD CONSTRAINT build_review_current_placement CHECK(
        payload->>'schema'='dmb_build_proposal_review_v2' AND payload ? 'placement_caret'
        AND jsonb_typeof(payload->'placement_caret')='number' AND (payload->>'placement_caret')::numeric >= 0
        AND (payload->>'placement_caret')::numeric = trunc((payload->>'placement_caret')::numeric))""")
