"""Actual APP proposal ownership and generator lifecycle beneath the Harness action."""
from hashlib import sha256
import json
from types import SimpleNamespace
from uuid import uuid4, uuid5, NAMESPACE_URL

import psycopg
from application_state.agent_conversation import AgentConversationService
from application_state.agent_conversation.types import TurnSubmission, TurnProvenance, HistoricalReference, SubmittedTurnIntentV1, SubmittedPrimaryWorkIntentV1, SubmittedGraphRequestIntentV1

import pytest
from application_state.build_proposal.service import BuildProposalService
from apps.live_control_server.models.build_document_proposal import BuildWriteCapability
from apps.live_control_server.services.build_insertion_tool import BuildInsertionTool
from apps.live_control_server.services import build_document_proposal as owner
from tests.test_build_document_proposal import request_case as proposal_case, Wire, TABLE


@pytest.fixture
def request_case(tmp_path, monkeypatch, application_state_dsn):
    return proposal_case.__wrapped__(tmp_path, monkeypatch, application_state_dsn)


def setup_tool(request, monkeypatch, *, timeout=False):
    capability = BuildWriteCapability(**request.model_dump(exclude={'instruction', 'origin'}))
    client_id = uuid4()
    service = AgentConversationService()
    provenance = TurnProvenance(world_id=capability.basis.world_id, surface_resolution='resolved', surface_id='build', surface_instance_id='build-test',
        primary_work=HistoricalReference(resolution='resolved', kind='build', object_id=capability.basis.document_id,
            revision=str(capability.basis.registry_revision), content_sha256=capability.basis.content_sha256),
        selected_object=HistoricalReference(resolution='absent'))
    accepted = service.accept_turn(TurnSubmission(world_id=capability.basis.world_id, conversation_id=capability.conversation_id,
        idempotency_key=uuid5(NAMESPACE_URL, f'dmb-agent-turn:{capability.basis.world_id}:{client_id}'),
        expected_conversation_revision=1, user_text='Put the agreed NPC on the page.', provenance=provenance,
        submitted_intent_v1=SubmittedTurnIntentV1(world_id=capability.basis.world_id, client_thread_id='test-thread',
            message='Put the agreed NPC on the page.', surface_id='build', surface_instance_id='build-test',
            client_work_state='saved_clean', primary_work=SubmittedPrimaryWorkIntentV1(kind='build',
                object_id=capability.basis.document_id, expected_revision=capability.basis.registry_revision,
                expected_content_sha256=capability.basis.content_sha256), graph_request=SubmittedGraphRequestIntentV1(mode='none'), graph_selection=None)))
    claimed = service.claim_turn(accepted.world_id, accepted.conversation_id, accepted.turn_id, expected_revision=accepted.revision).turn
    turn = SimpleNamespace(status=claimed.status, world_id=claimed.world_id,
        conversation_id=claimed.conversation_id, turn_id=claimed.turn_id, attempt=claimed.attempt,
        provenance=SimpleNamespace(surface_id='build', primary_work=SimpleNamespace(kind='build', object_id=capability.basis.document_id,
            revision=str(capability.basis.registry_revision), content_sha256=capability.basis.content_sha256)))
    wire = Wire(request, timeout=timeout)
    original = owner.compose
    async def generate(request):
        return await original(request, transport=wire)
    monkeypatch.setattr(owner, 'compose', generate)
    tool = BuildInsertionTool(capability, str(client_id), lambda: turn)
    message = dict(toolName='propose_build_insertion', operationId='host:g1', arguments={'instruction': 'Put the discussed Nia, a baker with a blue lantern, into a table.'})
    return tool, message, wire, turn


def test_tool_uses_real_generator_receipt_and_replays_without_second_call(request_case, monkeypatch):
    request, source, root = request_case
    tool, message, wire, _ = setup_tool(request, monkeypatch)
    reply = json.loads(tool.dispatch(message)['resultJson'])
    assert reply['status'] == 'awaiting_approval'
    row = BuildProposalService().get('elderwyld', request.idempotency_key)
    assert row.proposal.replacement_markdown == TABLE and row.reservation.origin is not None
    assert row.reservation.origin.arguments_sha256 == sha256(json.dumps(message['arguments'], ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    assert row.authorization and row.raw_response and row.observation
    assert json.loads(wire.calls[0].content)['tools'] == []
    assert (root / source.record.target_relpath).read_text() == source.markdown
    repeated = tool.dispatch({**message, 'operationId': 'host:g2'})
    assert json.loads(repeated['resultJson']) == reply and len(wire.calls) == 1
    changed = tool.dispatch({**message, 'arguments': {'instruction': 'Replace it with something else'}})
    assert json.loads(changed['resultJson'])['status'] == 'unavailable' and len(wire.calls) == 1


def test_uncertain_generation_retains_action_and_never_regenerates(request_case, monkeypatch):
    request, _, _ = request_case
    tool, message, wire, _ = setup_tool(request, monkeypatch, timeout=True)
    first = json.loads(tool.dispatch(message)['resultJson'])
    second = json.loads(tool.dispatch({**message, 'operationId': 'host:g2'})['resultJson'])
    assert first == second and first['status'] == 'unknown'
    assert first['action_id'] == str(request.idempotency_key) and len(wire.calls) == 1


@pytest.mark.parametrize('wrong', ['world', 'document', 'conversation', 'stale_source', 'model_target'])
def test_foreign_or_stale_tool_scope_never_dispatches(request_case, monkeypatch, wrong):
    request, _, _ = request_case
    tool, message, wire, turn = setup_tool(request, monkeypatch)
    if wrong == 'world':
        turn.world_id = 'another-world'
    if wrong == 'document':
        turn.provenance.primary_work.object_id = 'another-document'
    if wrong == 'conversation':
        turn.conversation_id = uuid4()
    if wrong == 'stale_source':
        monkeypatch.setattr(owner, '_source', lambda _: (_ for _ in ()).throw(ValueError('stale')))
    if wrong == 'model_target':
        message['arguments']['document_id'] = 'another-document'
    assert json.loads(tool.dispatch(message)['resultJson'])['status'] == 'unavailable'
    assert wire.calls == []


@pytest.mark.parametrize('failure', ['expired', 'reclaimed', 'failed', 'missing', 'client_identity'])
def test_actual_origin_claim_is_required_even_when_cached_turn_says_running(request_case, monkeypatch, application_state_dsn, failure):
    request, _, _ = request_case
    tool, message, wire, turn = setup_tool(request, monkeypatch)
    with psycopg.connect(application_state_dsn) as conn:
        if failure == 'expired':
            conn.execute("UPDATE agent.turn SET claim_expires_at=clock_timestamp()-interval '1 second' WHERE turn_id=%s", (turn.turn_id,))
        elif failure == 'reclaimed':
            conn.execute('UPDATE agent.turn SET attempt=attempt+1 WHERE turn_id=%s', (turn.turn_id,))
        elif failure == 'failed':
            conn.execute("UPDATE agent.turn SET status='failed', failure_code='test_failure', completed_at=clock_timestamp(), claim_expires_at=NULL WHERE turn_id=%s", (turn.turn_id,))
        elif failure == 'missing':
            turn.turn_id = uuid4()
        else:
            tool.client_turn_id = uuid4()
    assert turn.status == 'running'
    assert json.loads(tool.dispatch(message)['resultJson'])['status'] == 'unavailable'
    assert wire.calls == []


@pytest.mark.parametrize('boundary', ['authorized', 'sdk_entered'])
def test_claim_loss_after_reservation_still_prevents_generator_http(request_case, monkeypatch, application_state_dsn, boundary):
    request, _, _ = request_case
    tool, message, wire, turn = setup_tool(request, monkeypatch)
    advance = BuildProposalService.advance
    def lose_claim(self, *args, **kwargs):
        if kwargs.get('state') == boundary:
            with psycopg.connect(application_state_dsn) as conn:
                conn.execute("UPDATE agent.turn SET claim_expires_at=clock_timestamp()-interval '1 second' WHERE turn_id=%s", (turn.turn_id,))
        return advance(self, *args, **kwargs)
    monkeypatch.setattr(BuildProposalService, 'advance', lose_claim)
    result = json.loads(tool.dispatch(message)['resultJson'])
    assert result['status'] != 'awaiting_approval' and wire.calls == []


def test_prepared_agent_input_must_contain_the_exact_parent_tool_result():
    from apps.live_control_server.services.build_insertion_tool import arguments_digest, validate_included_results
    from apps.live_control_server.services.agent_turn_service import _included_tool_payloads
    args = {'instruction': 'Put Nella on the page.'}
    body = {'input': [dict(type='function_call', name='propose_build_insertion', call_id='tool-1', arguments=json.dumps(args)),
                      dict(type='function_call_output', call_id='tool-1', output='{"status":"awaiting_approval"}') ]}
    permitted = {(arguments_digest(args), body['input'][1]['output'])}
    validate_included_results(body, permitted)
    assert _included_tool_payloads(body, tool_name='expand_graph_retrieval') == []
    assert _included_tool_payloads(body, tool_name='propose_build_insertion') == [body['input'][1]['output']]
    with pytest.raises(ValueError):
        validate_included_results(body, set())
    body['input'][0]['arguments'] = json.dumps({'instruction': 'Write a different table.'})
    with pytest.raises(ValueError):
        validate_included_results(body, permitted)


def test_editor_capability_is_bound_to_the_exact_build_request_and_intent(request_case):
    from apps.live_control_server.models.agent_turn import AgentTurnRequest
    from apps.live_control_server.services.agent_turn_service import _submitted_turn_intent
    from application_state.agent_conversation.types import submitted_turn_intent_fingerprint_v2
    from tests.test_agent_build_surface_context import graph_request
    request, source, _ = request_case
    cap = BuildWriteCapability(**request.model_dump(exclude={'instruction', 'origin'}))
    body = graph_request(source).model_dump(by_alias=True)
    body['build_write_capability'] = cap.model_dump(mode='json')
    good = AgentTurnRequest.model_validate(body)
    first = submitted_turn_intent_fingerprint_v2(_submitted_turn_intent(good, world_id='elderwyld'))
    body['build_write_capability']['basis']['caret'] += 1
    changed = AgentTurnRequest.model_validate(body)
    assert submitted_turn_intent_fingerprint_v2(_submitted_turn_intent(changed, world_id='elderwyld')) != first
    body['build_write_capability']['basis']['world_id'] = 'foreign'
    with pytest.raises(ValueError):
        AgentTurnRequest.model_validate(body)
