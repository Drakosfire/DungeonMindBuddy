"""Admit an explicit inert image-preparation variant in Build action storage."""

from alembic import op

revision = "20261016_0028"
down_revision = "20261016_0027"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""DO $$ DECLARE item record; BEGIN
        FOR item IN SELECT conname FROM pg_constraint WHERE conrelid='agent.build_proposal'::regclass
          AND contype='c' AND pg_get_constraintdef(oid) LIKE '%dmb_build_document_proposal_v1%'
        LOOP EXECUTE format('ALTER TABLE agent.build_proposal DROP CONSTRAINT %I', item.conname); END LOOP;
    END $$""")
    op.execute("""ALTER TABLE agent.build_proposal ADD CONSTRAINT build_proposal_schema_variant
        CHECK(payload->>'schema_version' IN ('dmb_build_document_proposal_v1','dmb_build_image_preparation_v2'))""")


def downgrade():
    if (
        op.get_bind()
        .exec_driver_sql(
            "SELECT EXISTS(SELECT 1 FROM agent.build_proposal WHERE payload->>'schema_version'='dmb_build_image_preparation_v2')"
        )
        .scalar_one()
    ):
        raise RuntimeError("refusing to discard retained image preparations")
    op.execute(
        "ALTER TABLE agent.build_proposal DROP CONSTRAINT build_proposal_schema_variant"
    )
    op.execute(
        "ALTER TABLE agent.build_proposal ADD CONSTRAINT build_proposal_schema_variant CHECK(payload->>'schema_version'='dmb_build_document_proposal_v1')"
    )
