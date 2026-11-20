from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

from apps.live_control_server.models.agent_turn import AgentTurnRequest
from apps.live_control_server.services.agent_turn_service import (
    AgentTurnResolvedWork, AgentTurnServiceError, _accept_world_turn,
    _conversation_provenance, _policy_continuity_segment, _submitted_turn_intent,
)
from apps.live_control_server.services.hermes_session_store import HermesSessionPointerStore


def request(client_thread='client-a', turn='turn-a'):
    return AgentTurnRequest.model_validate({
        'schema': 'dmb_agent_turn_request_v1', 'client_thread_id': client_thread,
        'turn_id': turn, 'surface': {'surface_id': 'plan', 'instance_id': 'plan-main'},
        'owner_scope': {'kind': 'world', 'world_id': 'world:one'},
        'primary_work': None, 'client_work_state': 'none',
        'graph_request': {'mode': 'none'}, 'graph_selection': None, 'message': 'Tell me about the city.',
    })


def work():
    return AgentTurnResolvedWork(kind='plan', object_id='plan:one', revision=1,
                                 changed_since_expected=False, owner_kind='world', owner_id='world:one')


def test_policy_lookup_reuses_completion_key_despite_new_client_thread(tmp_path: Path):
    cid = uuid4()
    service = SimpleNamespace(get_active_conversation=lambda world: SimpleNamespace(conversation_id=cid))
    _, first = _policy_continuity_segment(service, request(), world_id='world:one', work=work())
    store = HermesSessionPointerStore(tmp_path)
    store.upsert_structured_after_turn(owner_kind='world', owner_id='world:one',
        work_kind='agent_conversation_segment', work_id=first, agent_thread_id=first,
        hermes_session_id='native-conversation')
    _, second = _policy_continuity_segment(service, request('client-b', 'turn-b'),
                                          world_id='world:one', work=work())
    restored = store.resolve_structured_for_request(owner_kind='world', owner_id='world:one',
        work_kind='agent_conversation_segment', work_id=second, agent_thread_id=second, pointer_id=None)
    assert restored.continuity_session_id == 'native-conversation'
    service.get_active_conversation = lambda world: SimpleNamespace(conversation_id=uuid4())
    _, fresh = _policy_continuity_segment(service, request('client-b', 'turn-c'),
                                         world_id='world:one', work=work())
    assert fresh != first
    assert store.resolve_structured_for_request(owner_kind='world', owner_id='world:one',
        work_kind='agent_conversation_segment', work_id=fresh, agent_thread_id=fresh,
        pointer_id=None).continuity_session_id is None


def test_absent_conversation_does_not_create_pre_admission_state():
    service = SimpleNamespace(get_active_conversation=lambda world: None)
    assert _policy_continuity_segment(service, request(), world_id='world:one', work=work()) is None


def test_conversation_switch_is_rejected_before_acceptance_or_provider():
    expected = uuid4()
    service = SimpleNamespace(get_active_conversation=lambda world: SimpleNamespace(
        conversation_id=uuid4(), revision=1))
    req = request()
    with pytest.raises(AgentTurnServiceError) as failure:
        _accept_world_turn(service, req, world_id='world:one',
            provenance=_conversation_provenance(req, world_id='world:one', work=work()),
            submitted_intent=_submitted_turn_intent(req, world_id='world:one'), expected_conversation_id=expected)
    assert failure.value.code == 'conversation_changed'
    assert failure.value.provider_dispatched is False
