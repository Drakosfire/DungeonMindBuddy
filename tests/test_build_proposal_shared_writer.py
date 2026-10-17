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
