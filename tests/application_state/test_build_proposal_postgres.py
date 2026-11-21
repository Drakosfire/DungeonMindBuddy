"""Real disposable APP persistence for inert Build authoring receipts."""
from concurrent.futures import ThreadPoolExecutor
import json
from uuid import uuid4

import pytest
from pydantic import ValidationError

from application_state.agent_conversation import AgentConversationService
from application_state.build_proposal.service import BuildProposalService
from application_state.build_proposal.types import (
    BuildGeneratedProposal, BuildProposalBasis, BuildProposalReservation, BuildProviderAuthorization,
    BuildProseBoundaryProposalRecord, BuildProseBoundaryReservation, BuildProseBoundaryTarget,
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
    result = BuildGeneratedProposal(replacement_markdown='| NPC | Job |\n| --- | --- |\n| Nia | Baker |', summary='A proposed NPC table.', assumptions=['New authored lore.'], target='captured')
    advance('response_received',raw_response=json.dumps(dict(destination='current_page',**result.model_dump(mode='json'))))
    advance('proposed')
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


@pytest.mark.parametrize('substitution', ['markdown', 'summary', 'assumptions', 'raw', 'target'])
def test_proposal_owner_rejects_results_unrelated_to_captured_final(reservation, substitution):
    store = BuildProposalService()
    record, _ = store.reserve(reservation)
    world = reservation.basis.world_id
    def advance(state, **fields):
        nonlocal record
        record = store.advance(world,record.action_id,expected_revision=record.revision,state=state,**fields)
        return record
    advance('authorized',authorization=BuildProviderAuthorization(provider_attempt_id=uuid4(),
        model='synthetic',payload_sha256='c'*64,payload_utf8_bytes=123))
    advance('sdk_entered')
    result = BuildGeneratedProposal(replacement_markdown='A proposed copper lamp.',
        summary='A proposed detail.',assumptions=['The lamp is invented.'],target='captured')
    raw=json.dumps(dict(destination='current_page',**result.model_dump(mode='json')))
    advance('response_received',raw_response=raw)
    changed = {'markdown': {'proposal':result.model_copy(update={'replacement_markdown':'A substituted silver lamp.'})},
        'summary': {'proposal':result.model_copy(update={'summary':'A changed summary.'})},
        'assumptions': {'proposal':result.model_copy(update={'assumptions':['It happened.']})},
        'target': {'proposal':result.model_copy(update={'target':None})},
        'raw': {'raw_response':raw.replace('copper','silver')}}[substitution]
    with pytest.raises(ApplicationStateConflictError):
        advance('response_received' if substitution=='raw' else 'proposed',**changed)
    assert store.get(world,record.action_id)==record
    assert record.state=='response_received' and record.proposal is None and record.raw_response==raw
    # The original final remains usable after the rejected transaction.
    assert advance('proposed').proposal==result


def test_prose_boundary_review_keeps_original_caret_and_requires_exact_offered_target(reservation):
    from application_state.build_proposal.review import BuildProposalReviewService, BuildReviewCommand

    basis = reservation.basis.model_copy(update={"editor_sha256": "e" * 64})
    target = BuildProseBoundaryTarget(
        catalog_sha256="a" * 64, alias="passage2:insert_after",
        operation="insert_after", **{"from": 43, "to": 43},
        before_text_sha256="b" * 64,
    )
    request = BuildProseBoundaryReservation.model_validate(
        reservation.model_dump() | {"basis": basis, "prose_target": target},
    )
    with pytest.raises(ApplicationStateConflictError, match="catalog owner"):
        BuildProposalService().reserve(request)
    admitted = []
    service = BuildProposalService(admit_prose_boundary=lambda conn, value: admitted.append(value))
    record, created = service.reserve(request)
    assert created and admitted == [request]
    assert service.reserve(request) == (record, False)
    world, action = basis.world_id, record.action_id

    def advance(state, **fields):
        nonlocal record
        record = service.advance(world, action, expected_revision=record.revision, state=state, **fields)

    advance("authorized", authorization=BuildProviderAuthorization(
        provider_attempt_id=uuid4(), model="synthetic", payload_sha256="c" * 64, payload_utf8_bytes=123,
    ))
    advance("sdk_entered")
    advance("response_received", raw_response=json.dumps({
        "destination": "current_page", "target": "prose_target",
        "replacement_markdown": "Bring a second lantern.", "summary": "A proposed precaution.",
        "assumptions": [],
    }))
    advance("proposed")
    assert type(BuildProposalService().get(world, action)) is BuildProseBoundaryProposalRecord
    assert record.reservation.basis.caret == 1 and record.reservation.prose_target == target

    review = BuildProposalReviewService()
    opened = review.execute(world, action, BuildReviewCommand(operation="open", expected_revision=0))
    assert opened.schema_version == "dmb_build_proposal_review_v5"
    assert opened.placement_caret == 1 and opened.prose_target == target
    with pytest.raises(ApplicationStateConflictError, match="offered paragraph boundary"):
        review.execute(world, action, BuildReviewCommand(
            operation="move", expected_revision=opened.revision, placement_caret=2,
        ))
    values = dict(operation="prepare", expected_revision=opened.revision, apply_id=uuid4(),
                  after_editor_sha256="f" * 64, after_draft_sha256="d" * 64)
    with pytest.raises(ApplicationStateConflictError, match="acknowledge the exact prose boundary"):
        review.execute(world, action, BuildReviewCommand(**values))
    prepare = BuildReviewCommand(**values, prose_target=target)
    prepared = review.execute(world, action, prepare)
    assert prepared.apply.prose_target == target
    assert review.execute(world, action, prepare) == prepared
    confirm = BuildReviewCommand(operation="confirm", expected_revision=prepared.revision, apply_id=prepare.apply_id)
    assert review.execute(world, action, confirm).state == "applied"
    assert BuildProposalService().get(world, action).inserted_in_draft
    with pytest.raises(ApplicationStateNotFoundError):
        review.get("foreign-world", action)
