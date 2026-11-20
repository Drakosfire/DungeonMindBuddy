"""Admit generic authored-reference bundles and fence older readers.

No retained rows change. The existing reviewed-intent guard still requires its
known intent version, known reference bundle version and a reference array.
"""
from importlib import import_module
from alembic import op

revision = "20261105_0106"
down_revision = "20261103_0105"
branch_labels = None
depends_on = None
_prior = import_module('application_state.migrations.versions.20261025_0073_authored_graph_references')
_OLD = f"COALESCE(({_prior._INTENT_V1}) OR ({_prior._INTENT_V2}),FALSE)"
_GENERIC = _prior._INTENT_V2.replace(
    "intent->'authored_references'->>'schema'='dmb_authored_graph_references_v1'",
    "intent->'authored_references'->>'schema' IN ('dmb_authored_graph_references_v1','dmb_authored_references_v2')",
)
_NEW = f"COALESCE(({_prior._INTENT_V1}) OR ({_GENERIC}),FALSE)"


def upgrade():
    conn = op.get_bind()
    conn.exec_driver_sql('LOCK TABLE agent.turn_reviewed_action IN ACCESS EXCLUSIVE MODE')
    conn.exec_driver_sql(f'CREATE TEMP TABLE dmb_source_reference_intent_check(intent JSONB,CHECK({_OLD})) ON COMMIT DROP')
    expected = conn.exec_driver_sql("SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conrelid='pg_temp.dmb_source_reference_intent_check'::regclass AND contype='c'").scalar_one()
    actual = conn.exec_driver_sql("SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conrelid='agent.turn_reviewed_action'::regclass AND conname='turn_reviewed_action_intent_version_check'").scalar_one()
    if actual != expected:
        raise RuntimeError('Unexpected reviewed-intent guard; refuse replacement')
    conn.exec_driver_sql('ALTER TABLE agent.turn_reviewed_action DROP CONSTRAINT turn_reviewed_action_intent_version_check')
    conn.exec_driver_sql(f'ALTER TABLE agent.turn_reviewed_action ADD CONSTRAINT turn_reviewed_action_intent_version_check CHECK({_NEW})')


def downgrade():
    raise RuntimeError("Retained native source references require recovery forward")
