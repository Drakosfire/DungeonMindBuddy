"""Actual Plan work records, without a synthetic Turn or legacy Graph scope."""
from copy import deepcopy
from hashlib import sha256
import json
from uuid import uuid4

import pytest

from application_state.agent_conversation import types as t
from application_state.agent_conversation.plan_jev_graph_packet import project_native_plan_work
from application_state.agent_conversation.authored_excerpt_blocks import restore_selection_blocks
from tests.test_surface_native_execution import component, execution, decision_prefix
from tests.test_surface_native_context import provenance_for, seal
from tests.application_state.test_plan_placement import original_capture, catalog_for

BODY='## Objective\r\n\r\nKeep the alternatives open.\r\n\r\n## Beat\r\nA possible arrival.\r\n'


def case(*, requested='discuss', placement='captured', captured=True, dirty=True, sessions=True):
    context,record=component('plan',unavailable=True)
    original=original_capture() if captured else None
    conversation_id=uuid4()
    basis=context.work_context.plan_basis.model_copy(update={'content_sha256':sha256(BODY.encode()).hexdigest()})
    if original is not None:
        changes=dict(world_id=basis.world_id,conversation_id=conversation_id,document_id=basis.document_id,
            base_revision=basis.object_revision,base_content_sha256=basis.content_sha256)
        if not dirty:
            changes.update(draft_markdown=BODY,draft_sha256=sha256(BODY.encode()).hexdigest())
        original=original.model_copy(update=changes)
        catalog=catalog_for(original)
    else:
        catalog=None
    work=context.work_context.model_copy(update={'plan_basis':basis})
    provenance=provenance_for(work).model_copy(update={'surface_instance_id':record.policy.action.intent.surface_instance_id})
    session=dict(world_id=basis.world_id,run_id=str(uuid4()),review_revision=3,title='Closing review',
        ended_at='2026-11-01T12:00:00Z',session_content_sha256='e'*64,sources=[
            dict(kind='scene_note',element_id='scene:one',text='We left an unresolved possibility.\n'),
            dict(kind='closing_reflections',element_id=None,text='Keep the question open.\n')])
    session['sha256']=t.canonical_sha256(session)
    if sessions:
        ref=t.HistoricalReference(resolution='resolved',kind='session_evidence_v1',object_id=session['run_id'],
            revision='3',content_sha256=session['sha256'])
        provenance=provenance.model_copy(update={'supporting_work':[*provenance.supporting_work,ref]})
    data=context.model_dump(mode='json',by_alias=True)
    data.update(work_context=work.model_dump(mode='json',by_alias=True),provenance_sha256=t.canonical_sha256(provenance))
    data['assembled_input']['tokenizer_name']='synthetic'
    context=type(context).model_validate_json(json.dumps(seal(data)))
    intent=record.policy.action.intent.model_copy(update={
        'primary_work':record.policy.action.intent.primary_work.model_copy(update={'expected_content_sha256':basis.content_sha256}),
        'plan_authoring_capture_sha256':original.sha256 if original is not None else None,
        'plan_placement_catalog_sha256':catalog.sha256 if catalog is not None else None})
    action=record.policy.action.model_copy(update={'intent':intent,'authoring_capture':original,'placement_catalog':catalog})
    record=execution(context.context_receipt_sha256,record.policy.model_copy(update={'action':action}))
    events,_=decision_prefix('plan',context,record)
    chosen=events[3]
    events[3]=chosen.model_copy(update=dict(requested_work=requested,
        original_capture_sha256=original.sha256 if original is not None else None,
        placement_catalog_sha256=catalog.sha256 if catalog is not None else None,
        original_capture=original.model_dump(mode='json',by_alias=True) if original is not None else None,
        placement_catalog=catalog.model_dump(mode='json',by_alias=True) if catalog is not None else None,
        placement_selector=placement if requested=='write_current_page' and catalog is not None else None,
        target_capture_sha256=catalog.resolve(original,placement).sha256 if requested=='write_current_page' and catalog is not None else None))
    record=execution(context.context_receipt_sha256,record.policy,events)
    proof=dict(plan_markdown=BODY,session_evidence=[session] if sessions else [],
        dialogue=[dict(role='assistant',content='Earlier discussion is reference, not an edit.')])
    return context,record,provenance,uuid4(),proof,conversation_id


def project(value):
    return project_native_plan_work(*value[:5],conversation_id=value[5])


@pytest.mark.parametrize('requested,placement,captured',[
    ('discuss','captured',True),('clarify','captured',True),('different_destination','captured',True),
    ('write_current_page','captured',True),('write_current_page','after:0',True),('discuss','captured',False)])
def test_shared_plan_work_keeps_exact_saved_draft_session_and_resolved_location(requested,placement,captured):
    value=case(requested=requested,placement=placement,captured=captured)
    frame=project(value)
    assert frame['requested_work']==requested
    assert restore_selection_blocks(frame['committed_plan_blocks'])==BODY
    assert frame['dialogue_reference']==value[4]['dialogue']
    assert len(frame['authored_sources'])==3
    assert restore_selection_blocks(frame['session_evidence'][0]['sources'][0]['text_blocks'])=='We left an unresolved possibility.\n'
    assert not {'graph_scope','graph_records','graph_authority','context_receipt_sha256'} & set(frame)
    if captured:
        assert frame['current_page_draft']['state']=='unsaved_working_draft'
        assert frame['current_page_draft']['markdown']=='A live draft.'
        assert frame['focused_edit_target']['kind']==('insert_at_boundary' if placement=='after:0' else 'insert_at_caret')
        assert frame['focused_edit_target'].get('location')==('After Objective' if requested=='write_current_page' and placement=='after:0'
            else 'Captured caret' if requested=='write_current_page' else None)
    else:
        assert 'focused_edit_target' not in frame


def test_identical_draft_reuses_saved_blocks_without_donating_source_authority():
    value=case(dirty=False)
    # Turn submission and PlanAction reservation are distinct existing owners.
    # The latter's key remains in the captured action; only the Turn key salts
    # these source selectors. Projection never reserves either owner.
    assert value[3] != value[1].policy.action.authoring_capture.idempotency_key
    frame=project(value)
    assert frame['current_page_draft']==dict(state='same_as_committed',primary_authoring_context=True,
        body_path=['committed_plan_blocks'])
    assert frame['authored_sources'][0]['source_kind']=='plan'
    replay=project(value)
    assert replay==frame
    changed=list(value)
    changed[3]=uuid4()
    assert project(changed)['committed_plan_blocks'][0]['selection_id']!=frame['committed_plan_blocks'][0]['selection_id']


@pytest.mark.parametrize('mutation',['saved_text','session_text','session_hash','foreign_session','missing_session',
    'duplicate_session','dialogue_role','hidden_proof','conversation','saved_revision','provenance','capture_dialogue'])
def test_shared_plan_work_rejects_foreign_or_changed_work_without_graph_aliases(mutation):
    value=list(case(requested='write_current_page',placement='after:0'))
    value[4]=deepcopy(value[4])
    if mutation=='saved_text':
        value[4]['plan_markdown']+='Changed'
    elif mutation in {'session_text','session_hash','foreign_session'}:
        session=value[4]['session_evidence'][0]
        if mutation=='session_text':
            session['sources'][0]['text']='An unsupported played outcome.'
        elif mutation=='foreign_session':
            session['world_id']='foreign'
        else:
            session['sources'][0]['text']='Changed'
            session.pop('sha256')
            session['sha256']=t.canonical_sha256(session)
    elif mutation=='missing_session':
        value[4]['session_evidence']=[]
    elif mutation=='duplicate_session':
        value[4]['session_evidence']*=2
    elif mutation=='dialogue_role':
        value[4]['dialogue'][0]['role']='system'
    elif mutation=='hidden_proof':
        value[4]['graph_packets']={}
    elif mutation=='conversation':
        value[5]=uuid4()
    elif mutation=='saved_revision':
        value[0].work_context.plan_basis.object_revision+=1
    elif mutation=='provenance':
        value[2]=value[2].model_copy(update={'surface_id':'build'})
    else:
        # Reference dialogue cannot replace the original captured work.
        action=value[1].policy.action
        capture=action.authoring_capture.model_copy(update={'conversation_id':uuid4()})
        value[1]=value[1].model_copy(update={'policy':value[1].policy.model_copy(update={
            'action':action.model_copy(update={'authoring_capture':capture})})})
    with pytest.raises(ValueError):
        project(value)
