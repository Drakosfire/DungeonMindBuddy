"""Persist principal/managed-World-scoped native graph operation recovery."""

from alembic import op
import sqlalchemy as sa


revision = "20261110_0151"
down_revision = "20261110_0150"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "native_graph_explorer_operations",
        sa.Column("principal_subject", sa.Text(), nullable=False),
        sa.Column("managed_world_id", sa.String(63), nullable=False),
        sa.Column("operation_id", sa.String(36), nullable=False),
        sa.Column("native_world_id", sa.Text(), nullable=False),
        sa.Column("binding_version", sa.BigInteger(), nullable=False),
        sa.Column("expected_revision_id", sa.Text(), nullable=False),
        sa.Column("parent_revision_id", sa.Text()),
        sa.Column("request_json", sa.Text(), nullable=False),
        sa.Column("request_sha256", sa.String(64), nullable=False),
        sa.Column("source_admission_id", sa.Text()),
        sa.Column("source_receipt_json", sa.Text()),
        sa.Column("source_receipt_sha256", sa.String(64)),
        sa.Column("prepared_json", sa.Text()),
        sa.Column("prepared_sha256", sa.String(64)),
        sa.Column("committed_json", sa.Text()),
        sa.Column("committed_sha256", sa.String(64)),
        sa.Column("rejected_json", sa.Text()),
        sa.Column("rejected_sha256", sa.String(64)),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint(
            "principal_subject",
            "managed_world_id",
            "operation_id",
            name="pk_native_graph_explorer_operations",
        ),
        sa.CheckConstraint(
            "binding_version > 0", name="ck_native_graph_explorer_binding_version"
        ),
        sa.CheckConstraint(
            "status IN ('reserved', 'prepared', 'unknown', 'committed', 'rejected')",
            name="ck_native_graph_explorer_operation_status",
        ),
        sa.CheckConstraint(
            "length(request_sha256) = 64",
            name="ck_native_graph_explorer_request_digest",
        ),
        schema="application_state",
    )
    op.create_index(
        "ix_native_graph_explorer_operations_updated",
        "native_graph_explorer_operations",
        ["principal_subject", "managed_world_id", "updated_at"],
        schema="application_state",
    )


def downgrade() -> None:
    raise RuntimeError(
        "Native graph operation records are retained; use forward recovery"
    )
