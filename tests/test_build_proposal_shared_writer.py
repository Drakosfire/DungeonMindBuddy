"""One real SDK request, proposal APP ownership and a trusted parent gate; synthetic."""
import asyncio
import json
from hashlib import sha256

import pytest
from generationengine.text_dispatch import TextDispatchGate

from application_state.build_proposal.service import BuildProposalService
from apps.live_control_server.services import build_document_proposal as owner
from tests.test_build_document_proposal import request_case as _request_case
from tests.test_build_insertion_tool import setup_tool


@pytest.fixture
def request_case(tmp_path, monkeypatch, application_state_dsn):
    return _request_case.__wrapped__(tmp_path, monkeypatch, application_state_dsn)


class Parent:
    def __init__(self, request, *, deny=None, raises=False):
        self.request, self.deny, self.raises = request, deny, raises
        self.prepared, self.events = [], []

    def row(self):
        return BuildProposalService().get('elderwyld', self.request.idempotency_key)

    async def authorize(self, prepared):
        row = self.row()
        assert row.state == 'authorized'
        assert str(row.authorization.provider_attempt_id) == prepared.attempt_id
        assert row.authorization.payload_sha256 == prepared.body_sha256
        assert prepared.body_sha256 == sha256(prepared.body).hexdigest()
        assert json.loads(prepared.body)['tools'] == []
        self.prepared.append(prepared)
        return self.result('authorize')

    def result(self, phase):
        if phase == self.deny:
            if self.raises:
                raise ValueError('synthetic parent persistence failure')
            return False
        return True

    async def record(self, event):
        assert event.request == self.prepared[-1]
        self.events.append(event)
        return self.result(event.outcome)

    def gate(self):
        return TextDispatchGate(self.authorize, self.record)


def setup(request_case, monkeypatch, **options):
    request, source, root = request_case
    shared = owner.compose_with_writer
    parent = Parent(request, **options)
    tool, message, wire, turn = setup_tool(request, monkeypatch)

    async def compose(body):
        return await shared(body, parent.gate(), transport=wire)

    monkeypatch.setattr(owner, 'compose', compose)
    return request, source, root, parent, tool, message, wire, turn


def test_one_shared_attempt_persists_before_ready_and_recovers_without_send(request_case, monkeypatch):
    request, source, root, parent, tool, message, wire, _ = setup(request_case, monkeypatch)
    reply = json.loads(tool.dispatch(message)['resultJson'])
    row = parent.row()
    assert row.state == 'proposed' and reply['status'] == 'awaiting_approval'
    assert len(wire.calls) == len(parent.prepared) == 1
    assert [e.outcome for e in parent.events] == ['sending', 'response_received']
    assert row.authorization.payload_sha256 == sha256(wire.calls[0].content).hexdigest()
    assert row.raw_response == wire.text and row.proposal is not None
    assert (root / source.record.target_relpath).read_text() == source.markdown
    # Simulate conversational completion missing: recover the persisted action,
    # even if the parent would now refuse every dispatch. No regeneration.
    parent.deny = 'authorize'
    assert json.loads(tool.dispatch(message)['resultJson']) == reply
    assert len(parent.prepared) == len(wire.calls) == 1


@pytest.mark.parametrize('phase', ['authorize', 'sending', 'response_received'])
@pytest.mark.parametrize('raises', [False, True])
def test_parent_gate_refusal_or_failure_preserves_no_replay(request_case, monkeypatch, phase, raises):
    _, _, _, parent, tool, message, wire, _ = setup(request_case, monkeypatch, deny=phase, raises=raises)
    reply = json.loads(tool.dispatch(message)['resultJson'])
    assert reply['status'] != 'awaiting_approval'
    assert len(wire.calls) == (1 if phase == 'response_received' else 0)
    assert parent.row().state == ('unknown' if phase == 'response_received' else 'failed')
    before = len(parent.prepared), len(parent.events), len(wire.calls)
    assert json.loads(tool.dispatch(message)['resultJson']) == reply
    assert (len(parent.prepared), len(parent.events), len(wire.calls)) == before


def test_transport_uncertainty_reaches_both_owners_and_never_regenerates(request_case, monkeypatch):
    _, _, _, parent, tool, message, wire, _ = setup(request_case, monkeypatch)
    wire.timeout = True
    reply = json.loads(tool.dispatch(message)['resultJson'])
    assert reply['status'] == parent.row().state == 'unknown'
    assert [e.outcome for e in parent.events] == ['sending', 'outcome_unknown']
    assert json.loads(tool.dispatch(message)['resultJson']) == reply
    assert len(wire.calls) == len(parent.prepared) == 1


def test_proposal_owner_refusal_prevents_parent_authorization_and_http(request_case, monkeypatch):
    _, _, _, parent, tool, message, wire, _ = setup(request_case, monkeypatch)
    original = BuildProposalService.advance

    def advance(self, *args, **kwargs):
        if kwargs.get('state') == 'authorized':
            raise ValueError('synthetic proposal authorization refusal')
        return original(self, *args, **kwargs)

    monkeypatch.setattr(BuildProposalService, 'advance', advance)
    assert json.loads(tool.dispatch(message)['resultJson'])['status'] != 'awaiting_approval'
    assert parent.prepared == [] and wire.calls == []


def test_shared_seam_requires_real_agent_origin(request_case):
    request, _, _ = request_case
    parent = Parent(request)
    with pytest.raises(ValueError, match='origin_required'):
        asyncio.run(owner.compose_with_writer(request, parent.gate()))
    assert parent.prepared == []


def test_real_writer_progress_is_provisional_before_exact_final_admission(request_case, monkeypatch):
    from apps.live_control_server.services.build_construction_stream import construction_sink
    request, _, _, parent, tool, message, wire, _ = setup(request_case, monkeypatch)
    observed=[]
    token=construction_sink.set(lambda value: observed.append((value, parent.row().state, parent.row().raw_response)))
    try:
        reply=json.loads(tool.dispatch(message)['resultJson'])
    finally:
        construction_sink.reset(token)
    assert reply['status']=='awaiting_approval' and len(wire.calls)==1
    building=[item for item in observed if item[0]['status']=='building']
    assert building and all(state=='response_received' and raw is None for _,state,raw in building)
    assert observed[-1][0]['status']=='ready' and observed[-1][1]=='proposed'
    assert observed[-1][0]['origin']==parent.row().reservation.origin.model_dump(mode='json')
    assert observed[-1][0]['provider_attempt_id']==str(parent.row().authorization.provider_attempt_id)
    assert parent.row().raw_response==wire.text


def test_failed_final_evidence_acknowledgment_cannot_produce_ready_proposal(request_case,monkeypatch):
    request, _, _, parent, tool, message, wire, _ = setup(request_case,monkeypatch)
    advance=BuildProposalService.advance
    def deny(self,*args,**kwargs):
        if kwargs.get('raw_response') is not None:
            raise ValueError('synthetic failed final evidence acknowledgment')
        return advance(self,*args,**kwargs)
    monkeypatch.setattr(BuildProposalService,'advance',deny)
    reply=json.loads(tool.dispatch(message)['resultJson'])
    assert reply['status']!='awaiting_approval'
    assert parent.row().proposal is None and parent.row().raw_response is None
    assert len(wire.calls)==1


@pytest.mark.parametrize('destination', ['different_page', 'unresolved'])
def test_parent_refuses_destination_conflict_without_ready_or_resend(request_case, monkeypatch, destination):
    from apps.live_control_server.services.build_construction_stream import construction_sink
    _, _, _, parent, tool, message, wire, _ = setup(request_case, monkeypatch)
    wire.text = json.dumps(dict(destination=destination, replacement_markdown='',
        summary='Writing belongs on another page or needs clarification.', assumptions=[]))
    observed = []
    token = construction_sink.set(observed.append)
    try:
        reply = json.loads(tool.dispatch(message)['resultJson'])
    finally:
        construction_sink.reset(token)
    row = parent.row()
    assert reply['status'] == 'failed' and row.state == 'failed'
    assert row.failure_code == 'build_compose_target_mismatch'
    assert row.proposal is None and row.raw_response == wire.text
    assert not any(item['status'] == 'ready' for item in observed)
    assert observed[-1]['status'] == 'incomplete'
    assert len(parent.prepared) == len(wire.calls) == 1
    assert json.loads(tool.dispatch(message)['resultJson']) == reply
    assert len(parent.prepared) == len(wire.calls) == 1


def test_buildout_of_newly_created_current_page_preserves_its_destination(request_case, monkeypatch):
    _, source, _, parent, tool, message, wire, _ = setup(request_case, monkeypatch)
    message['arguments']['instruction'] = 'Build out this new page, which has already been created and is now open. Write here.'
    reply = json.loads(tool.dispatch(message)['resultJson'])
    assert reply['status'] == 'awaiting_approval'
    body = json.loads(wire.calls[0].content)
    packet = json.loads(body['input'])
    assert packet['source_title'] == source.record.title
    assert packet['source_basis']['document_id'] == source.record.document_id
    assert packet['instruction'] == message['arguments']['instruction']
    assert 'A page being new does not make it a different target.' in body['instructions']
    assert parent.row().state == 'proposed' and len(parent.prepared) == len(wire.calls) == 1
