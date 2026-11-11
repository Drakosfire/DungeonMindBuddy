"""Persist Buddy index graph guest sessions and command recovery metadata."""

from alembic import op
import sqlalchemy as sa


revision = "20261110_0150"
down_revision = "20261110_0148"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "index_graph_sessions",
        sa.Column("session_id", sa.Uuid(as_uuid=False), primary_key=True),
        sa.Column("credential_hash", sa.LargeBinary(32), nullable=False, unique=True),
        sa.Column("allocation_id", sa.Text(), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "length(allocation_id) <= 128", name="ck_index_graph_allocation_id_length"
        ),
        schema="application_state",
    )
    op.create_index(
        "ix_index_graph_sessions_expires_at",
        "index_graph_sessions",
        ["expires_at"],
        schema="application_state",
    )
    op.create_table(
        "index_graph_bindings",
        sa.Column(
            "session_id",
            sa.Uuid(as_uuid=False),
            sa.ForeignKey("application_state.index_graph_sessions.session_id"),
            nullable=False,
        ),
        sa.Column("key", sa.Text(), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("session_id", "key"),
        schema="application_state",
    )
    op.create_table(
        "index_graph_operations",
        sa.Column(
            "session_id",
            sa.Uuid(as_uuid=False),
            sa.ForeignKey("application_state.index_graph_sessions.session_id"),
            nullable=False,
        ),
        sa.Column("operation_id", sa.String(64), nullable=False),
        sa.Column("request_json", sa.Text(), nullable=False),
        sa.Column("request_sha256", sa.String(64), nullable=False),
        sa.Column("parent_revision_id", sa.Text(), nullable=False),
        sa.Column("prepared_json", sa.Text(), nullable=False),
        sa.Column("prepared_sha256", sa.String(64), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("committed_json", sa.Text()),
        sa.Column("rejected_json", sa.Text()),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("session_id", "operation_id"),
        sa.CheckConstraint(
            "status IN ('prepared', 'committed', 'unknown', 'rejected')",
            name="ck_index_graph_operation_status",
        ),
        schema="application_state",
    )
    op.create_index(
        "ix_index_graph_operations_updated",
        "index_graph_operations",
        ["session_id", "updated_at"],
        schema="application_state",
    )
    op.create_table(
        "index_graph_reservations",
        sa.Column(
            "session_id",
            sa.Uuid(as_uuid=False),
            sa.ForeignKey("application_state.index_graph_sessions.session_id"),
            nullable=False,
        ),
        sa.Column("operation_id", sa.String(64), nullable=False),
        sa.Column("request_json", sa.Text(), nullable=False),
        sa.Column("request_sha256", sa.String(64), nullable=False),
        sa.Column("parent_revision_id", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("session_id", "operation_id"),
        schema="application_state",
    )


def downgrade() -> None:
    raise RuntimeError(
        "Index graph sessions and recovery records are retained; use forward recovery"
    )
