"""Real disposable PostgreSQL migration gates. No runtime database is a fixture."""
from uuid import uuid4
import json

from alembic import command
import psycopg
from psycopg.types.json import Jsonb
import pytest

from application_state.agent_conversation import AgentConversationService
from application_state.agent_conversation.types import ConversationCommand, HistoricalReference, TurnProvenance, TurnSubmission, SubmittedTurnIntentV1, SubmittedGraphRequestIntentV1
from application_state.cli import _current_and_head, alembic_config, upgrade_to_head


def turn_fixture():
    service = AgentConversationService(); world = 'rules-migration-fixture'
    receipt = service.new_conversation(ConversationCommand(world_id=world, command_id=uuid4(), expected_pointer_revision=0, expected_active_conversation_id=None))
    conversation = service.get_conversation(world, receipt.conversation_id)
    return service.accept_turn(TurnSubmission(world_id=world,conversation_id=conversation.conversation_id,idempotency_key=uuid4(),expected_conversation_revision=conversation.revision,user_text='Rules fixture',
        provenance=TurnProvenance(world_id=world,surface_resolution='resolved',surface_id='index',surface_instance_id='rules-fixture',primary_work=HistoricalReference(resolution='absent'),supporting_work=[],selected_object=HistoricalReference(resolution='absent')),
        submitted_intent_v1=SubmittedTurnIntentV1(world_id=world,client_thread_id='rules-fixture-thread',message='Rules fixture',surface_id='index',surface_instance_id='rules-fixture',client_work_state='none',primary_work=None,graph_request=SubmittedGraphRequestIntentV1(mode='none'),graph_selection=None)))


def payload(turn_id, **overrides):
    value = {'schema':'dmb_rules_execution_v1','scope':{'turn_id':str(turn_id),'product_attempt':1},'state':'active','supports':{},'events':[],'budget_use':{}}
    value.update(overrides); return value


def test_empty_migration_downgrade_and_upgrade_preserve_existing_turn(application_state_dsn):
    turn = turn_fixture()
    assert _current_and_head(application_state_dsn) == ('20261020_0041','20261020_0041')
    with psycopg.connect(application_state_dsn) as conn:
        assert conn.execute('SELECT answer_composition_kind FROM agent.turn WHERE turn_id=%s',(turn.turn_id,)).fetchone()==('base',)
    command.downgrade(alembic_config(),'20261019_0040')
    with psycopg.connect(application_state_dsn) as conn:
        assert conn.execute('SELECT user_text FROM agent.turn WHERE turn_id=%s',(turn.turn_id,)).fetchone()==('Rules fixture',)
        assert conn.execute("SELECT to_regclass('agent.turn_rules_execution')").fetchone()==(None,)
    upgrade_to_head(dsn=application_state_dsn)
    with psycopg.connect(application_state_dsn) as conn:
        assert conn.execute('SELECT answer_composition_kind FROM agent.turn WHERE turn_id=%s',(turn.turn_id,)).fetchone()==('base',)


def test_downgrade_refuses_any_retained_rules_row(application_state_dsn):
    turn = turn_fixture()
    with psycopg.connect(application_state_dsn) as conn:
        conn.execute('INSERT INTO agent.turn_rules_execution(turn_id,product_attempt,revision,payload) VALUES(%s,1,1,%s)',(turn.turn_id,Jsonb(payload(turn.turn_id))))
    with pytest.raises(RuntimeError,match='refusing to discard'):
        command.downgrade(alembic_config(),'20261019_0040')
    assert _current_and_head(application_state_dsn)[0]=='20261020_0041'
    with psycopg.connect(application_state_dsn) as conn:
        assert conn.execute('SELECT count(*) FROM agent.turn_rules_execution').fetchone()==(1,)


@pytest.mark.parametrize('mutate',[
    lambda p:p.update(state='accepted'),
    lambda p:p['scope'].update(turn_id=str(uuid4())),
    lambda p:p['scope'].update(product_attempt=2),
    lambda p:p.update(events=[{}]*257),
    lambda p:p.update(events='not an array'),
    lambda p:p.update(extra='x'*330000),
])
def test_sql_shape_scope_and_transfer_bounds(application_state_dsn,mutate):
    turn=turn_fixture(); value=payload(turn.turn_id);mutate(value)
    with psycopg.connect(application_state_dsn) as conn:
        with pytest.raises(psycopg.errors.CheckViolation):
            conn.execute('INSERT INTO agent.turn_rules_execution(turn_id,product_attempt,revision,payload) VALUES(%s,1,1,%s)',(turn.turn_id,Jsonb(value)))


def test_mixed_marker_cannot_be_put_on_an_uncompleted_turn(application_state_dsn):
    turn=turn_fixture()
    with psycopg.connect(application_state_dsn) as conn:
        with pytest.raises(psycopg.errors.CheckViolation):
            conn.execute("UPDATE agent.turn SET answer_composition_kind='rules_mixed_v1' WHERE turn_id=%s",(turn.turn_id,))
