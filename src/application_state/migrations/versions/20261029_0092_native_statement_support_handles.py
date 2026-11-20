"""Admit finite-support writer V2; retain exact historical V1 rows/read contracts."""

from importlib import import_module
from alembic import op
from sqlalchemy import text

revision = "20261029_0092"
down_revision = "20261029_0091"
branch_labels = None
depends_on = None

_prior = import_module(
    "application_state.migrations.versions.20261029_0091_native_statement_answers"
)
_V1 = (
    "graph_context_execution->'policy'->>'policy_version'='native_statement_writer_v1'"
)
assert _prior._NATIVE.count(_V1) == 1
_NATIVE = _prior._NATIVE.replace(
    _V1,
    "graph_context_execution->'policy'->>'policy_version' IN ('native_statement_writer_v1','native_statement_writer_v2')",
)


def upgrade():
    bind = op.get_bind()
    for name in (
        "agent_turn_graph_context_receipt_check",
        "agent_turn_graph_context_execution_check",
        "agent_turn_graph_completion_check",
    ):
        definition = bind.execute(
            text(
                "SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conrelid='agent.turn'::regclass AND conname=:name"
            ),
            {"name": name},
        ).scalar_one()
        if not definition.startswith("CHECK (") or not definition.endswith(")"):
            raise RuntimeError("Expected owning turn CHECK predicate is unavailable")
        previous = definition[len("CHECK (") : -1]
        op.execute(f'ALTER TABLE agent.turn DROP CONSTRAINT "{name}"')
        op.execute(f"""ALTER TABLE agent.turn ADD CONSTRAINT "{name}" CHECK (
          CASE WHEN graph_context_receipt->>'schema'='dmb_native_statement_context_receipt_v1'
          THEN COALESCE(({_NATIVE}),FALSE) ELSE ({previous}) END)""")


def downgrade():
    raise RuntimeError(
        "Retained finite-support native writer contexts require recovery forward"
    )
