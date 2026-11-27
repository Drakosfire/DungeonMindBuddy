"""Selected-source recovery against one isolated App fixture; no provider calls."""
import json
from types import SimpleNamespace
from uuid import uuid4

import psycopg
import pytest
from psycopg.types.json import Jsonb

from application_state.agent_conversation import AgentConversationService, types as t
from application_state.errors import ApplicationStateConflictError
from apps.live_control_server.services.world_container_registry import create_world_container
from tests.application_state.test_agent_conversation_postgres import _new
from tests.test_surface_native_context import provenance_for, seal
from tests.test_surface_native_execution import _selected_source_pending, controller, execution
from tests.test_surface_native_turn_records import submission


def test_selected_source_capture_survives_pre_dispatch_reclaim_but_not_provider_reclaim(application_state_dsn):
    world = create_world_container(name='Selected reader recovery ' + uuid4().hex).world_id
    context, policy, _ = _selected_source_pending()
    ref = policy.action.intent.authored_references.references[0].model_copy(update={'managed_world_id':world})
    refs = policy.action.intent.authored_references.model_copy(update={'references':(ref,)})
    intent = policy.action.intent.model_copy(update={'world_id':world,
        'graph_request':policy.action.intent.graph_request.model_copy(update={'world_id':world}),
        'authored_references':refs})
    authority = context.native_query.authority.model_copy(update={'managed_world_id':world})
    query = context.native_query.model_copy(update={'authority':authority,'selected_references_sha256':refs.sha256})
    source = context.source_authority.model_copy(update={'managed_world_id':world})
    data = context.model_dump(mode='json',by_alias=True)
    data['work_context']['source_basis']['world_id'] = world
    data['native_query'] = query.model_dump(mode='json',by_alias=True)
    data['source_authority'] = source.model_dump(mode='json',by_alias=True)
    work = type(context.work_context).model_validate(data['work_context'])
    provenance = provenance_for(work).model_copy(update={'surface_instance_id':intent.surface_instance_id})
    data['provenance_sha256'] = t.canonical_sha256(provenance)
    context = type(context).model_validate_json(json.dumps(seal(data)))
    policy = policy.model_copy(update={'action':policy.action.model_copy(update={'intent':intent}),
        'source_authority_sha256':t.canonical_sha256(source),
        'native_query_sha256':t.canonical_sha256(query.model_dump(mode='json',by_alias=True))})
    record = execution(context.context_receipt_sha256,policy,[])
    service = AgentConversationService()
    conversation = _new(service,world)
    sub = t.TurnSubmission.model_validate_json(submission('build').model_copy(update={
        'world_id':world,'conversation_id':conversation.conversation_id,'user_text':intent.message,
        'provenance':provenance,'submitted_intent_v2':intent,'graph_context_receipt':context,
        'graph_context_execution':record}).model_dump_json(by_alias=True))
    accepted = service.accept_turn(sub)
    assert AgentConversationService().inspect_turn(world_id=world,turn_id=accepted.turn_id) == accepted
    claimed = service.claim_turn(world,conversation.conversation_id,accepted.turn_id,expected_revision=accepted.revision).turn
    captured, fresh = service.capture_native_authored_references(world,conversation.conversation_id,claimed.turn_id,
        expected_revision=claimed.revision,expected_attempt=claimed.attempt,event_id=uuid4())
    assert fresh and AgentConversationService().inspect_turn(world_id=world,turn_id=captured.turn_id) == captured
    with psycopg.connect(application_state_dsn) as conn:
        conn.execute("UPDATE agent.turn SET claim_expires_at=clock_timestamp()-interval '1 second' WHERE turn_id=%s",(captured.turn_id,))
    recovered = service.claim_turn(world,conversation.conversation_id,captured.turn_id,expected_revision=captured.revision).turn
    assert recovered.attempt == captured.attempt + 1
    assert AgentConversationService().inspect_turn(world_id=world,turn_id=recovered.turn_id) == recovered
    assert recovered.graph_context_execution.events[0].references == refs
    assert recovered.graph_context_execution.events[0].attempt == captured.attempt
    from apps.live_control_server.services.native_authored_references import capture_input
    fence = SimpleNamespace(turn=recovered,append=lambda *_args,**_kwargs:pytest.fail('duplicate capture'))
    capture_input(SimpleNamespace(fence=fence,turn=recovered))

    # Simulate only the durable authorization record; no provider was called.
    auth = controller('build',policy,sequence=1)
    authorized = execution(context.context_receipt_sha256,policy,[recovered.graph_context_execution.events[0],auth])
    with psycopg.connect(application_state_dsn) as conn:
        conn.execute("UPDATE agent.turn SET graph_context_execution=%s,claim_expires_at=clock_timestamp()-interval '1 second' WHERE turn_id=%s",
            (Jsonb(authorized.model_dump(mode='json',by_alias=True)),recovered.turn_id))
    with pytest.raises(ApplicationStateConflictError,match='cannot be reclaimed'):
        service.claim_turn(world,conversation.conversation_id,recovered.turn_id,expected_revision=recovered.revision)
    fenced = service.inspect_turn(world_id=world,turn_id=recovered.turn_id)
    assert fenced.status == 'interrupted' and fenced.attempt == recovered.attempt
    assert [e.outcome for e in fenced.graph_context_execution.events if e.kind=='provider_outcome'] == ['outcome_unknown']
