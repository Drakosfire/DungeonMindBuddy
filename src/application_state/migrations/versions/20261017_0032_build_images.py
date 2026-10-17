"""Admit an explicit inert image-preparation variant in Build action storage."""

from alembic import op
from importlib import import_module

_previous = import_module(
    "application_state.migrations.versions.20261017_0030_build_authoring_completion"
)
_IMAGE = (
    _previous._AUTHORING.replace(
        "dmb_build_authoring_completion_v1", "dmb_build_image_preparation_completion_v1"
    )
    .replace("prepared_page_proposal", "prepared_image_direction")
    .replace("proposal_ready", "image_preparation_ready")
    .replace("proposal_result_sha256", "preparation_result_sha256")
    .replace(
        "A preview is ready. Review it before inserting it into the page. Nothing has been saved or published.",
        "Your image prompt is ready in Image Studio. Review it before generating. Nothing has been generated, inserted or saved.",
    )
)

revision = "20261017_0032"
down_revision = "20261017_0031"
branch_labels = None
depends_on = None


def upgrade():
    _previous._previous._predecessor._replace(
        "agent_turn_graph_completion_check",
        f"({_previous._OLD}) OR COALESCE(({_previous._AUTHORING}), FALSE) OR COALESCE(({_IMAGE}), FALSE)",
    )
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
            "SELECT EXISTS(SELECT 1 FROM agent.turn WHERE completion->>'schema'='dmb_build_image_preparation_completion_v1')"
        )
        .scalar_one()
    ):
        raise RuntimeError("refusing to discard retained image completions")
    _previous._previous._predecessor._replace(
        "agent_turn_graph_completion_check",
        f"({_previous._OLD}) OR COALESCE(({_previous._AUTHORING}), FALSE)",
    )
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
