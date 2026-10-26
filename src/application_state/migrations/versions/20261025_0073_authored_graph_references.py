"""Reference-aware plan reviews and immutable authored-context intents, additive only."""
from importlib import import_module
from alembic import op
from sqlalchemy import text

revision = '20261025_0073'
down_revision = '20261025_0072'
branch_labels = None
depends_on = None
_prior = import_module('application_state.migrations.versions.20261025_0072_plan_objective')
_PLAN_V3 = """payload->>'schema'='dmb_reviewed_work_plan_v3'
 AND jsonb_typeof(payload->'objective')='string' AND (payload->>'objective') ~ '[^[:space:]]'
 AND jsonb_typeof(payload->'root_references')='array'"""
_INTENT_V1 = "intent->>'schema'='dmb_build_graph_intent_v1'"
_INTENT_V2 = """intent->>'schema'='dmb_build_graph_intent_v2'
 AND intent->'authored_references'->>'schema'='dmb_authored_graph_references_v1'
 AND jsonb_typeof(intent->'authored_references'->'references')='array'"""


def upgrade():
    conn = op.get_bind()
    conn.exec_driver_sql('LOCK TABLE agent.work_plan,agent.turn_reviewed_action IN ACCESS EXCLUSIVE MODE')
    conn.exec_driver_sql('ALTER TABLE agent.work_plan DROP CONSTRAINT work_plan_version_check')
    conn.exec_driver_sql(f'ALTER TABLE agent.work_plan ADD CONSTRAINT work_plan_version_check CHECK(COALESCE(({_prior._PLAN_V1}) OR ({_prior._PLAN_V2}) OR ({_PLAN_V3}),FALSE))')
    conn.exec_driver_sql(f'CREATE TEMP TABLE dmb_reference_intent_check(intent JSONB,CHECK({_INTENT_V1})) ON COMMIT DROP')
    expected = conn.exec_driver_sql("SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conrelid='pg_temp.dmb_reference_intent_check'::regclass AND contype='c'").scalar_one()
    names = conn.execute(text("SELECT conname FROM pg_constraint WHERE conrelid='agent.turn_reviewed_action'::regclass AND contype='c' AND pg_get_constraintdef(oid)=:expected"), {'expected': expected}).fetchall()
    if len(names) != 1:
        raise RuntimeError('Unexpected reviewed-intent version constraint; refuse replacement')
    conn.exec_driver_sql('ALTER TABLE agent.turn_reviewed_action DROP CONSTRAINT "'+names[0][0].replace('"','""')+'"')
    conn.exec_driver_sql(f'ALTER TABLE agent.turn_reviewed_action ADD CONSTRAINT turn_reviewed_action_intent_version_check CHECK(COALESCE(({_INTENT_V1}) OR ({_INTENT_V2}),FALSE))')


def downgrade():
    conn = op.get_bind()
    conn.exec_driver_sql('LOCK TABLE agent.work_plan,agent.turn_reviewed_action,agent.turn IN ACCESS EXCLUSIVE MODE')
    if conn.exec_driver_sql("""SELECT EXISTS(SELECT 1 FROM agent.work_plan WHERE payload->>'schema'='dmb_reviewed_work_plan_v3')
 OR EXISTS(SELECT 1 FROM agent.turn_reviewed_action WHERE intent->>'schema'='dmb_build_graph_intent_v2')
 OR EXISTS(SELECT 1 FROM agent.turn WHERE jsonb_path_exists(graph_context_execution,'$.events[*] ? (@.kind == "build_authored_references_captured_v1")'))""").scalar_one():
        raise RuntimeError('Retained authored Graph reference context requires recovery forward')
    conn.exec_driver_sql('ALTER TABLE agent.work_plan DROP CONSTRAINT work_plan_version_check')
    conn.exec_driver_sql(f'ALTER TABLE agent.work_plan ADD CONSTRAINT work_plan_version_check CHECK(COALESCE(({_prior._PLAN_V1}) OR ({_prior._PLAN_V2}),FALSE))')
    conn.exec_driver_sql('ALTER TABLE agent.turn_reviewed_action DROP CONSTRAINT turn_reviewed_action_intent_version_check')
    conn.exec_driver_sql(f'ALTER TABLE agent.turn_reviewed_action ADD CONSTRAINT turn_reviewed_action_intent_version_check CHECK({_INTENT_V1})')
