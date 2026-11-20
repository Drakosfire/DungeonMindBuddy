"""Scripted boundary admission through real native owners, never model quality."""
import copy
import json
from uuid import uuid4

import pytest
from pydantic import ValidationError
from evals.inline_prose_targeting.native_contract_test import proof
from evals.inline_prose_targeting.native_fixture import catalog_for
from application_state.build_proposal.types import (
    BuildProposalRecord, BuildProseProposalRecord, BuildProseBoundaryProposalRecord,
    BuildProseBoundaryTarget,
)
from application_state.build_proposal.service import BuildProposalService
from application_state.build_proposal.review import (
    BuildProposalReview, BuildProseProposalReview, BuildProseBoundaryProposalReview,
    BuildProposalReviewService,
)
from application_state.errors import ApplicationStateConflictError

pytest_plugins = ['tests.application_state.conftest']


def boundary(payload, operation):
    payload = copy.deepcopy(payload)
    choices, targets = catalog_for(json.loads(payload['editor_json']))
    choice = next(c for c in choices if c['section'] == 'Preparation' and c['operation'] == operation)
    payload['prose_target'] = {
        'schema': 'dmb_build_prose_boundary_target_v1',
        'catalog_sha256': payload['prose_target']['catalog_sha256'],
        'alias': choice['selector'], **targets[choice['selector']],
    }
    return payload


@pytest.mark.parametrize('operation', ['insert_before', 'insert_after'])
def test_boundary_native_roundtrip_and_closed_readers(proof, operation):
    fixture, page, original = proof
    payload = boundary(original, operation)
    record = fixture.stage(payload)
    assert record['schema_version'] == 'dmb_build_document_proposal_v3'
    assert record['reservation']['basis'] == payload['basis']
    assert payload['prose_target']['from'] == payload['prose_target']['to']
    assert payload['prose_target']['before_text_sha256'] == original['prose_target']['before_text_sha256']
    action = record['action_id']
    review = fixture.review(action, {'operation': 'open', 'expected_revision': 0})
    assert review['schema'] == 'dmb_build_proposal_review_v5'
    assert review['placement_caret'] == payload['basis']['caret']
    for model, value in [(BuildProposalRecord, record), (BuildProseProposalRecord, record),
                         (BuildProposalReview, review), (BuildProseProposalReview, review)]:
        with pytest.raises(ValidationError): model.model_validate(value)
        with pytest.raises(ValidationError): model.model_validate_json(json.dumps(value))
    assert BuildProseBoundaryProposalRecord.model_validate(record).model_dump(mode='json') == record
    assert BuildProseBoundaryProposalReview.model_validate(review).model_dump(mode='json') == review
    for flag in [False, True]:
        with pytest.raises(ApplicationStateConflictError):
            BuildProposalService(allow_prose_targets=flag).get(fixture.world, action)
        with pytest.raises(ApplicationStateConflictError):
            BuildProposalReviewService(allow_prose_targets=flag).get(fixture.world, action)
    command = dict(operation='prepare', expected_revision=review['revision'], apply_id=str(uuid4()),
                   after_editor_sha256='c'*64, after_draft_sha256='d'*64, prose_target=payload['prose_target'])
    prepared = fixture.review(action, command)
    assert fixture.review(action, command) == prepared
    assert prepared['apply']['prose_target'] == payload['prose_target']
    confirmed = fixture.review(action, dict(operation='confirm', expected_revision=prepared['revision'], apply_id=command['apply_id']))
    assert fixture.review(action) == confirmed
    assert fixture.page() == page  # Neither review nor confirm saves the document.


@pytest.mark.parametrize('change', ['extent', 'digest', 'alias', 'scope', 'stale'])
def test_boundary_admission_refuses_wrong_capture_without_mutation(proof, change):
    fixture, page, original = proof
    payload = boundary(original, 'insert_after')
    if change == 'extent': payload['prose_target']['from'] += 1; payload['prose_target']['to'] += 1
    if change == 'digest': payload['prose_target']['before_text_sha256'] = '0'*64
    if change == 'alias': payload['prose_target']['alias'] = 'unknown'
    if change == 'scope': payload['basis']['document_id'] = 'foreign'
    if change == 'stale': fixture.save({'basis': payload['basis'], 'markdown': page['markdown']+'\n\nHuman edit.'})
    before = fixture.page()
    with pytest.raises((ValueError, ApplicationStateConflictError)): fixture.stage(payload)
    assert fixture.page() == before


def test_boundary_move_binding_staleness_and_version_refusal(proof, application_state_dsn):
    import psycopg
    fixture, page, original = proof
    payload = boundary(original, 'insert_before')
    record = fixture.stage(payload); action = record['action_id']
    review = fixture.review(action, {'operation': 'open', 'expected_revision': 0})
    with pytest.raises(ApplicationStateConflictError):
        fixture.review(action, dict(operation='move', expected_revision=review['revision'], placement_caret=3))
    command = dict(operation='prepare', expected_revision=review['revision'], apply_id=str(uuid4()),
                   after_editor_sha256='c'*64, after_draft_sha256='d'*64)
    with pytest.raises(ApplicationStateConflictError):
        fixture.review(action, {**command, 'prose_target': boundary(original, 'insert_after')['prose_target']})
    fixture.save({'basis': payload['basis'], 'markdown': page['markdown']+'\n\nHuman edit.'})
    with pytest.raises(ApplicationStateConflictError):
        fixture.review(action, {**command, 'prose_target': payload['prose_target']})
    assert fixture.review(action) == review
    with psycopg.connect(application_state_dsn) as conn:
        with pytest.raises(psycopg.errors.CheckViolation):
            with conn.transaction():
                conn.execute("UPDATE agent.build_proposal SET payload=jsonb_set(payload,'{schema_version}','\"dmb_build_document_proposal_v99\"') WHERE action_id=%s", (action,))
    with pytest.raises(ValidationError):
        BuildProseBoundaryTarget.model_validate({**payload['prose_target'], 'to': payload['prose_target']['to']+1})


def test_boundary_reservation_requires_separate_optin_and_admitter(proof):
    from application_state.build_proposal.types import BuildProposalReservation
    fixture, _, original = proof
    payload = boundary(original, 'insert_before')
    reservation = BuildProposalReservation(
        idempotency_key=uuid4(), conversation_id=fixture.conversation.conversation_id,
        expected_pointer_revision=1, basis=payload['basis'],
        prose_target=payload['prose_target'], instruction='Synthetic insertion',
    )
    for owner in [
        BuildProposalService(),
        BuildProposalService(allow_prose_targets=True, admit_prose_target=lambda _: None),
        BuildProposalService(allow_prose_boundaries=True),
    ]:
        with pytest.raises(ApplicationStateConflictError, match='not enabled'):
            owner.reserve(reservation)
    with pytest.raises(ValidationError):
        BuildProposalReservation.model_validate({
            **reservation.model_dump(mode='json'),
            'basis': {**payload['basis'], 'selection': {'from': 1, 'to': 2}},
        })
