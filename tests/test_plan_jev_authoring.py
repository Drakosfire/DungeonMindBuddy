"""Plan authoring request capture belongs to its exact ordinary Agent intent."""
from uuid import uuid4

import pytest
from pydantic import ValidationError

from tests.application_state.test_plan_authoring import capture_payload
from apps.live_control_server.models.agent_turn import AgentTurnRequest
from apps.live_control_server.services.agent_turn_service import _submitted_turn_intent
from application_state.agent_conversation.types import submitted_turn_intent_fingerprint_v2


def request_payload():
    return dict(schema='dmb_agent_turn_request_v1',client_thread_id=str(uuid4()),turn_id=str(uuid4()),
        surface=dict(surface_id='plan',instance_id='surface:plan:a'),owner_scope=dict(kind='world',world_id='world:a'),
        primary_work=dict(kind='plan',object_id='page:a',expected_revision=3,expected_revision_n=3,expected_content_sha256='a'*64),
        client_work_state='saved_dirty',graph_request={'mode':'none'},graph_selection=None,
        plan_context_policy={'policy':'auto_plan_world'},plan_authoring_capture=capture_payload(),
        message='Now draft this Plan and preserve the current working note.')


def test_plan_live_capture_participates_in_the_exact_turn_identity():
    payload=request_payload()
    first=AgentTurnRequest.model_validate(payload)
    intent=_submitted_turn_intent(first,world_id='world:a')
    assert intent.plan_authoring_capture_sha256==first.plan_authoring_capture.sha256
    initial=submitted_turn_intent_fingerprint_v2(intent)
    payload['plan_authoring_capture']['draft_generation']+=1
    second=_submitted_turn_intent(AgentTurnRequest.model_validate(payload),world_id='world:a')
    assert initial!=submitted_turn_intent_fingerprint_v2(second)


@pytest.mark.parametrize('change',[
    lambda p:p['plan_authoring_capture'].update(world_id='world:foreign'),
    lambda p:p['plan_authoring_capture'].update(document_id='page:foreign'),
    lambda p:p['plan_authoring_capture'].update(base_revision=2),
    lambda p:p['plan_authoring_capture'].update(base_content_sha256='b'*64),
    lambda p:p['surface'].update(surface_id='play'),
    lambda p:p.update(plan_context_policy=None),
])
def test_foreign_or_stale_plan_capture_is_rejected_before_provider_dispatch(change):
    payload=request_payload();change(payload)
    with pytest.raises(ValidationError):AgentTurnRequest.model_validate(payload)
