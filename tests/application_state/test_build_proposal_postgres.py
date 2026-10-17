"""Real disposable APP persistence for inert Build authoring receipts."""
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from pydantic import ValidationError

from application_state.agent_conversation import AgentConversationService
from application_state.build_proposal.service import BuildProposalService
from application_state.build_proposal.types import (
    BuildGeneratedProposal, BuildProposalBasis, BuildProposalReservation, BuildProviderAuthorization,
)
from application_state.errors import ApplicationStateConflictError, ApplicationStateNotFoundError
from tests.application_state.test_agent_conversation_postgres import _new


@pytest.fixture
def reservation(application_state_dsn):
    world = 'compose-' + uuid4().hex
    conversation = _new(AgentConversationService(), world)
    return BuildProposalReservation(idempotency_key=uuid4(), conversation_id=conversation.conversation_id,
        expected_pointer_revision=1, instruction='Create NPCs and jobs as a table.',
        basis=BuildProposalBasis(world_id=world, document_id='source-one', registry_revision=1,
            content_sha256='a'*64, draft_sha256='b'*64, visibility='internal', caret=1,
            draft_generation=0, selection_generation=0))


def test_reservation_is_durable_and_idempotent_with_real_workspace_basis(reservation):
    store = BuildProposalService()
    record, created = store.reserve(reservation)
    assert created and record.state == 'reserved' and record.after_turn_sequence == 0
    assert record.reservation.basis.document_id == 'source-one'
    assert record.reservation.basis.registry_revision == 1
    replay, created = BuildProposalService().reserve(reservation)
    assert not created and replay == record
    assert BuildProposalService().list(reservation.basis.world_id, reservation.conversation_id) == [record]
    changed = reservation.model_copy(update={'instruction':'Different instruction'})
    with pytest.raises(ApplicationStateConflictError):
        store.reserve(changed)


def test_concurrent_same_key_reserves_once(reservation):
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _:BuildProposalService().reserve(reservation), range(2)))
    assert sorted(created for _, created in results) == [False, True]
    assert results[0][0].action_id == results[1][0].action_id


def test_foreign_world_and_changed_conversation_refuse(reservation):
    store = BuildProposalService()
    record, _ = store.reserve(reservation)
    with pytest.raises(ApplicationStateNotFoundError):
        store.get('foreign-world', record.action_id)
    other = reservation.model_copy(update={'idempotency_key':uuid4(),'expected_pointer_revision':2})
    with pytest.raises(ApplicationStateConflictError):
        store.reserve(other)


def test_durable_authorization_lifecycle_result_and_draft_receipt(reservation):
    store = BuildProposalService()
    record, _ = store.reserve(reservation)
    world, action = reservation.basis.world_id, record.action_id
    def advance(state, **fields):
        nonlocal record
        record = store.advance(world, action, expected_revision=record.revision, state=state, **fields)
        return record
    auth = BuildProviderAuthorization(provider_attempt_id=uuid4(), model='synthetic',payload_sha256='c'*64,payload_utf8_bytes=123)
    advance('authorized',authorization=auth)
    advance('sdk_entered')
    advance('response_received',raw_response='{"synthetic":true}')
    result = BuildGeneratedProposal(replacement_markdown='| NPC | Job |\n| --- | --- |\n| Nia | Baker |', summary='A proposed NPC table.', assumptions=['New authored lore.'])
    advance('proposed',proposal=result)
    fresh = BuildProposalService().get(world, action)
    assert fresh.proposal == result and fresh.authorization == auth
    inserted = store.report_inserted(world,action,expected_revision=fresh.revision)
    assert inserted.inserted_in_draft and inserted.state == 'proposed'
    assert store.report_inserted(world,action,expected_revision=fresh.revision) == inserted
    with pytest.raises(ApplicationStateConflictError):
        advance('sdk_entered')  # No provider replay after result.


def test_uncertain_dispatch_is_terminal_and_cannot_be_replayed(reservation):
    store = BuildProposalService()
    record, _ = store.reserve(reservation)
    world = reservation.basis.world_id
    record = store.advance(world,record.action_id,expected_revision=1,state='authorized',
        authorization=BuildProviderAuthorization(provider_attempt_id=uuid4(),model='synthetic',payload_sha256='c'*64,payload_utf8_bytes=123))
    record = store.advance(world,record.action_id,expected_revision=record.revision,state='sdk_entered')
    record = store.advance(world,record.action_id,expected_revision=record.revision,state='unknown',failure_code='provider_outcome_unknown')
    replay, created = store.reserve(reservation)
    assert not created and replay.state == 'unknown'
    with pytest.raises(ApplicationStateConflictError):
        store.advance(world,record.action_id,expected_revision=record.revision,state='authorized')


def test_missing_authorization_or_stale_transition_rolls_back(reservation):
    store = BuildProposalService()
    record, _ = store.reserve(reservation)
    with pytest.raises(ValidationError):
        store.advance(reservation.basis.world_id,record.action_id,expected_revision=1,state='authorized')
    assert store.get(reservation.basis.world_id,record.action_id).state == 'reserved'
    with pytest.raises(ApplicationStateConflictError):
        store.advance(reservation.basis.world_id,record.action_id,expected_revision=99,state='failed',failure_code='stale')
    with pytest.raises(ApplicationStateConflictError):
        store.report_inserted(reservation.basis.world_id,record.action_id,expected_revision=1)
