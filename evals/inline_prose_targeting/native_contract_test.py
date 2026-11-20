"""Native DB owner proof; scripted nomination/output, no ordinary model routing."""
import json
from uuid import uuid4
import pytest
from evals.inline_prose_targeting.native_fixture import NativeProseFixture, catalog_for, sha, wire
from application_state.build_proposal.service import BuildProposalService
from application_state.build_proposal.review import BuildProposalReviewService
from application_state.errors import ApplicationStateConflictError
pytest_plugins=['tests.application_state.conftest']

@pytest.fixture
def proof(tmp_path, application_state_dsn):
    from evals.inline_prose_targeting.native_schema import extend_empty_clone
    extend_empty_clone(application_state_dsn,tmp_path/'test-only-schema.json')
    fixture=NativeProseFixture(tmp_path)
    markdown='## Overview\n\nKeep this.\n\n## Preparation\n\nThe scouts returned silently.\n\n## Opening Beat\n\nThe scouts returned silently.'
    page=fixture.bootstrap({'markdown':markdown})
    doc={'type':'doc','content':[]}
    for text,kind in [('Overview','heading'),('Keep this.','paragraph'),('Preparation','heading'),('The scouts returned silently.','paragraph'),('Opening Beat','heading'),('The scouts returned silently.','paragraph')]:
        node={'type':kind,'content':[{'type':'text','text':text}]}
        if kind=='heading':node['attrs']={'level':2}
        doc['content'].append(node)
    choices,targets=catalog_for(doc); choice=next(x for x in choices if x['section']=='Preparation' and x['operation']=='replace_paragraph')
    target={'schema':'dmb_build_prose_target_v1','catalog_sha256':sha(wire(choices)),'alias':choice['selector'],**targets[choice['selector']]}
    basis={k:page[k] for k in ['world_id','document_id','registry_revision','content_sha256']}
    basis.update(visibility='internal',editor_sha256=sha(wire(doc)),draft_sha256=sha(markdown),caret=1,draft_generation=0,selection_generation=0)
    payload=dict(basis=basis,draft_markdown=markdown,editor_json=wire(doc),prose_target=target,catalog_choices=choices,replacement_markdown='The scouts returned without speaking.')
    return fixture,page,payload

def test_real_native_review_preserves_binding_no_save_and_fresh_read(proof):
    fixture,page,payload=proof; record=fixture.stage(payload); action=record['action_id']
    assert record['schema_version']=='dmb_build_document_proposal_v2'
    assert 'selection' not in record['reservation']['basis']
    assert fixture.page()['content_sha256']==page['content_sha256']
    review=fixture.review(action,{'operation':'open','expected_revision':0})
    assert review['schema']=='dmb_build_proposal_review_v4' and review['prose_target']==payload['prose_target']
    apply_id=str(uuid4())
    command=dict(operation='prepare',expected_revision=review['revision'],apply_id=apply_id,after_editor_sha256='c'*64,after_draft_sha256='d'*64,prose_target=payload['prose_target'])
    prepared=fixture.review(action,command)
    assert prepared['apply']['prose_target']==payload['prose_target']
    assert fixture.review(action,command)==prepared
    confirmed=fixture.review(action,dict(operation='confirm',expected_revision=prepared['revision'],apply_id=apply_id))
    assert fixture.review(action)==confirmed
    assert fixture.page()['content_sha256']==page['content_sha256']
    with pytest.raises(ApplicationStateConflictError): BuildProposalService().get(fixture.world,record['action_id'])
    with pytest.raises(ApplicationStateConflictError): BuildProposalReviewService().get(fixture.world,record['action_id'])
    changed=payload['draft_markdown'].replace('The scouts returned silently.','The scouts returned without speaking.',1)
    saved=fixture.save({'basis':payload['basis'],'markdown':changed})
    assert saved['markdown']==changed and saved['registry_revision']>page['registry_revision']
    assert fixture.page()==saved

@pytest.mark.parametrize('change',['target','scope','source','multiblock'])
def test_refusals_preserve_source(proof,change):
    fixture,page,payload=proof
    if change=='target': payload['prose_target']['from']+=1
    if change=='scope': payload['basis']['document_id']='other'
    if change=='source': fixture.save({'basis':payload['basis'],'markdown':page['markdown']+'\n\nHuman edit.'})
    if change=='multiblock':payload['replacement_markdown']='One.\n\nTwo.'
    before=fixture.page()
    with pytest.raises((ApplicationStateConflictError,ValueError)):fixture.stage(payload)
    assert fixture.page()==before

def test_prepare_rejects_different_binding_and_changed_source(proof):
    fixture,page,payload=proof;record=fixture.stage(payload);action=record['action_id'];review=fixture.review(action,{'operation':'open','expected_revision':0})
    command=dict(operation='prepare',expected_revision=review['revision'],apply_id=str(uuid4()),after_editor_sha256='c'*64,after_draft_sha256='d'*64)
    with pytest.raises(ApplicationStateConflictError):fixture.review(action,command)
    with pytest.raises(ApplicationStateConflictError):fixture.review(action,dict(operation='move',expected_revision=review['revision'],placement_caret=3))
    fixture.save({'basis':payload['basis'],'markdown':page['markdown']+'\n\nHuman edit.'})
    with pytest.raises(ApplicationStateConflictError):fixture.review(action,{**command,'prose_target':payload['prose_target']})
    assert fixture.review(action)['state']=='editing'

def test_legacy_reservation_still_works_and_default_owner_cannot_emit_prose(proof):
    from application_state.build_proposal.types import BuildProposalReservation
    fixture,page,payload=proof
    legacy=BuildProposalReservation(idempotency_key=uuid4(),conversation_id=fixture.conversation.conversation_id,
        expected_pointer_revision=1,basis=payload['basis'],instruction='Legacy fixture')
    row,_=BuildProposalService().reserve(legacy)
    assert row.schema_version=='dmb_build_document_proposal_v1'
    assert 'prose_target' not in row.model_dump(mode='json')['reservation']
    nominated=BuildProposalReservation.model_validate({**legacy.model_dump(mode='json'),'idempotency_key':str(uuid4()),'prose_target':payload['prose_target']})
    with pytest.raises(ApplicationStateConflictError,match='not enabled'): BuildProposalService().reserve(nominated)
    with pytest.raises(ApplicationStateConflictError,match='not enabled'): BuildProposalService(allow_prose_targets=True).reserve(nominated)


def test_fixture_constraints_retain_legacy_and_reject_unknown_versions(proof,application_state_dsn):
    import psycopg
    fixture,page,payload=proof; record=fixture.stage(payload)
    with psycopg.connect(application_state_dsn) as conn:
        with pytest.raises(psycopg.errors.CheckViolation):
            with conn.transaction():
                conn.execute("UPDATE agent.build_proposal SET payload=jsonb_set(payload,'{schema_version}','\"dmb_build_document_proposal_v99\"') WHERE action_id=%s",(record['action_id'],))
    assert fixture.proposals.get(fixture.world,record['action_id']).schema_version=='dmb_build_document_proposal_v2'


def test_native_review_accepts_canonical_single_paragraph_terminal_newline(proof):
    fixture,page,payload=proof
    payload['replacement_markdown']='The scouts returned without speaking.\n'
    record=fixture.stage(payload);action=record['action_id']
    review=fixture.review(action,{'operation':'open','expected_revision':0})
    canonical='The scouts returned without speaking.\n'
    saved=fixture.review(action,{'operation':'save','expected_revision':review['revision'],'markdown':canonical})
    assert saved['markdown']==canonical
    assert fixture.page()['content_sha256']==page['content_sha256']
    with pytest.raises(ValueError):
        fixture.review(action,{'operation':'save','expected_revision':saved['revision'],'markdown':'First.\n\nSecond.\n'})
    assert fixture.review(action)==saved


def test_direct_legacy_history_codecs_reject_prose_records(proof):
    """History uses the public legacy model directly, not the service fence."""
    from pydantic import ValidationError
    from application_state.build_proposal.types import BuildProposalRecord, BuildProseProposalRecord
    from application_state.build_proposal.review import BuildProposalReview, BuildProseProposalReview
    fixture, _, payload = proof
    record = fixture.stage(payload)
    review = fixture.review(record['action_id'], {'operation': 'open', 'expected_revision': 0})
    for legacy, explicit, value in [
        (BuildProposalRecord, BuildProseProposalRecord, record),
        (BuildProposalReview, BuildProseProposalReview, review),
    ]:
        with pytest.raises(ValidationError):
            legacy.model_validate(value)
        with pytest.raises(ValidationError):
            legacy.model_validate_json(json.dumps(value))
        assert explicit.model_validate(value).model_dump(mode='json') == value
        assert explicit.model_validate_json(json.dumps(value)).model_dump(mode='json') == value
    # Merely relabeling a future record must not erase its target provenance.
    with pytest.raises(ValidationError):
        BuildProposalRecord.model_validate({**record, 'schema_version': 'dmb_build_document_proposal_v1'})
    with pytest.raises(ValidationError):
        BuildProposalReview.model_validate({**review, 'schema': 'dmb_build_proposal_review_v2'})
