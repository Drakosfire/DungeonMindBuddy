"""Use LZ4 for newly stored agent execution records."""

from alembic import op

revision = "20261121_0172"
down_revision = "20261120_0171"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "ALTER TABLE agent.turn ALTER COLUMN graph_context_execution SET COMPRESSION lz4"
    )


def downgrade():
    op.execute(
        "ALTER TABLE agent.turn ALTER COLUMN graph_context_execution SET COMPRESSION default"
    )
