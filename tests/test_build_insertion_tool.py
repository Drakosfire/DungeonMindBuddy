"""Actual APP proposal ownership and generator lifecycle beneath the Harness action."""
from hashlib import sha256
import json
from types import SimpleNamespace
from uuid import uuid4

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
    turn = SimpleNamespace(status='running', world_id=capability.basis.world_id,
        conversation_id=capability.conversation_id, turn_id=uuid4(),
        provenance=SimpleNamespace(surface_id='build', primary_work=SimpleNamespace(kind='build', object_id=capability.basis.document_id, revision=str(capability.basis.registry_revision), content_sha256=capability.basis.content_sha256)))
    wire = Wire(request, timeout=timeout)
    original = owner.compose
    async def generate(request):
        return await original(request, transport=wire)
    monkeypatch.setattr(owner, 'compose', generate)
    tool = BuildInsertionTool(capability, str(uuid4()), lambda: turn)
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
