"""Objective-aware plans; historical payloads and reserved dispatches are unchanged."""
from importlib import import_module
from alembic import op
from sqlalchemy import text

revision = '20261025_0072'
down_revision = '20261025_0071'
branch_labels = None
depends_on = None
_prior = import_module('application_state.migrations.versions.20261025_0070_intentional_build_response')
_review = import_module('application_state.migrations.versions.20261025_0067_relationship_review')
_OLD = f'({_prior._OLD}) OR COALESCE(({_prior._NEW}),FALSE)'


def objective_branch(expression, old, new):
    expression = expression.replace(old,new)
    assert expression.count("ARRAY['kind','steps']") == 1
    expression = expression.replace("ARRAY['kind','steps']", "ARRAY['kind','objective','steps']")
    expression = expression.replace("completion->'collaboration'->>'kind'='plan'\n", "completion->'collaboration'->>'kind'='plan'\n    AND jsonb_typeof(completion->'collaboration'->'objective')='string'\n    AND (completion->'collaboration'->>'objective') ~ '[^[:space:]]'\n",1)
    return expression + " AND jsonb_path_exists(graph_context_execution,'$.events[*] ? (@.kind == \"build_plan_output_contract_v1\" && @.policy == \"typed_plan_objective_v1\")')"


_INTENTIONAL = objective_branch(_prior._NEW,'dmb_build_intentional_response_completion_v1','dmb_build_intentional_response_completion_v2')
_REVIEWED = objective_branch(_review._REVIEW,'dmb_build_relationship_review_completion_v1','dmb_build_relationship_review_completion_v2')
_NEW = f'COALESCE(({_INTENTIONAL}),FALSE) OR COALESCE(({_REVIEWED}),FALSE)'
_PLAN_V1 = "payload->>'schema'='dmb_reviewed_work_plan_v1'"
_PLAN_V2 = "payload->>'schema'='dmb_reviewed_work_plan_v2' AND jsonb_typeof(payload->'objective')='string' AND (payload->>'objective') ~ '[^[:space:]]'"


def upgrade():
    conn = op.get_bind()
    conn.exec_driver_sql('LOCK TABLE agent.turn,agent.work_plan IN ACCESS EXCLUSIVE MODE')
    conn.exec_driver_sql(f'CREATE TEMP TABLE dmb_plan_check_expected(payload JSONB,CHECK({_PLAN_V1})) ON COMMIT DROP')
    expected = conn.exec_driver_sql("SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conrelid='pg_temp.dmb_plan_check_expected'::regclass AND contype='c'").scalar_one()
    names = conn.execute(text("SELECT conname FROM pg_constraint WHERE conrelid='agent.work_plan'::regclass AND contype='c' AND pg_get_constraintdef(oid)=:expected"), {'expected':expected}).fetchall()
    if len(names)!=1:
        raise RuntimeError('Unexpected work-plan version constraint; refuse replacement')
    conn.exec_driver_sql('ALTER TABLE agent.work_plan DROP CONSTRAINT "'+names[0][0].replace('"','""')+'"')
    conn.exec_driver_sql(f'ALTER TABLE agent.work_plan ADD CONSTRAINT work_plan_version_check CHECK (COALESCE(({_PLAN_V1}) OR ({_PLAN_V2}),FALSE))')
    _prior._replace('agent_turn_graph_completion_check',f'({_OLD}) OR ({_NEW})')
    _prior._replace('agent_turn_lifecycle_check',f'({_prior._NEW_LIFECYCLE}) OR COALESCE((status=\'completed\' AND assistant_text=\'\' AND failure_code IS NULL AND completed_at IS NOT NULL AND completion->\'answer_segments\'=\'[]\'::jsonb AND ({_INTENTIONAL})),FALSE)')


def downgrade():
    conn = op.get_bind()
    conn.exec_driver_sql('LOCK TABLE agent.turn,agent.work_plan IN ACCESS EXCLUSIVE MODE')
    if conn.exec_driver_sql("""SELECT EXISTS(SELECT 1 FROM agent.work_plan WHERE payload->>'schema'='dmb_reviewed_work_plan_v2')
       OR EXISTS(SELECT 1 FROM agent.turn WHERE completion->>'schema' IN ('dmb_build_intentional_response_completion_v2','dmb_build_relationship_review_completion_v2')
       OR jsonb_path_exists(graph_context_execution,'$.events[*] ? (@.kind == "build_plan_output_contract_v1")'))""").scalar_one():
        raise RuntimeError('Retained objective-aware plans require recovery forward')
    _prior._replace('agent_turn_graph_completion_check',_OLD)
    _prior._replace('agent_turn_lifecycle_check',_prior._NEW_LIFECYCLE)
    conn.exec_driver_sql('ALTER TABLE agent.work_plan DROP CONSTRAINT work_plan_version_check')
    conn.exec_driver_sql(f'ALTER TABLE agent.work_plan ADD CONSTRAINT work_plan_version_check CHECK ({_PLAN_V1})')
