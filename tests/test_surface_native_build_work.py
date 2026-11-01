"""Shared Build work-record boundary; no actual Turn/caller/SDK activation."""
import asyncio
from copy import deepcopy
from hashlib import sha256
import json
from uuid import uuid4

import pytest

from application_state.agent_conversation import types as t
from application_state.agent_conversation import build_draft_context as draft
from application_state.agent_conversation import build_primary_context as primary
from application_state.agent_conversation.native_execution import validate_context_binding
from tests.test_surface_native_execution import component, execution, controller, outcomes, native_writer
from tests.test_surface_native_context import seal, provenance_for

SAVED='# Page\r\n\r\nSaved orchid 🌸.\r\n'
DRAFT='An unsaved possibility, not a played event. 🌸\n'


def case(*, with_draft=True, selected=True, draft_text=DRAFT):
    context,record=component('build',unavailable=True)
    basis=context.work_context.source_basis.model_copy(update={'content_sha256':sha256(SAVED.encode()).hexdigest()})
    snap=draft.BuildDraftSnapshotV1(**basis.model_dump(),draft_markdown=draft_text,
        draft_sha256=sha256(draft_text.encode()).hexdigest(),editor_sha256='c'*64,draft_generation=2)
    conversation_id,turn_id=uuid4(),uuid4()
    request=draft.BuildDraftContextRequestV1(snapshot=snap,conversation_id=conversation_id,expected_pointer_revision=3)
    intent=record.policy.action.intent.model_copy(update={
        'primary_work':record.policy.action.intent.primary_work.model_copy(update={'expected_content_sha256':basis.content_sha256}),
        'build_draft_context_sha256':draft.digest(request.model_dump(mode='json',by_alias=True)) if with_draft else None})
    action=record.policy.action.model_copy(update={'intent':intent,'saved_source_char_count':len(SAVED)})
    policy=record.policy.model_copy(update={'action':action})
    first=controller('build',policy,sequence=2 if with_draft else 0)
    data=context.model_dump(mode='json',by_alias=True)
    data['work_context']['source_basis']=basis.model_dump(mode='json',by_alias=True)
    data['provenance_sha256']=t.canonical_sha256(provenance_for(type(context.work_context).model_validate(
        data['work_context'])).model_copy(update={'surface_instance_id':intent.surface_instance_id}))
    data['assembled_input']['tokenizer_name']=first.input_estimator
    context=type(context).model_validate_json(json.dumps(seal(data)))
    root=execution(context.context_receipt_sha256,policy)
    events=[]
    captured=None
    if with_draft:
        stored=draft.BuildDraftContextRecordV1(record_id=uuid4(),turn_id=turn_id,conversation_id=conversation_id,
            attempt=1,submitted_intent_fingerprint=t.submitted_turn_intent_fingerprint_v2(intent),
            expected_pointer_revision=3,snapshot=snap)
        captured=t.BuildDraftContextCapturedV1(kind='build_draft_context_captured_v1',event_id=uuid4(),sequence=0,record=stored)
        events.append(captured)
        events.append(t.BuildDraftProviderInclusionV1(kind='build_draft_provider_inclusion_v1',event_id=uuid4(),sequence=1,
            provider_attempt_id=first.provider_attempt_id,envelope_sha256=first.envelope_sha256,
            draft_event_id=captured.event_id,snapshot_sha256=snap.snapshot_sha256))
    events.extend([first,*outcomes(first,len(events)+1)])
    reads=[]
    for line,text in [(1,'# Page\r\n'),(3,'Saved orchid 🌸.\r\n')]:
        rid=uuid4()
        events.append(t.BuildSectionReadAuthorizationV1(kind='build_section_read_authorized_v1',event_id=uuid4(),sequence=len(events),
            read_id=rid,source_basis=basis,source_class='saved_authored_source_not_played_truth',line_start=line,line_end=line,max_chars=len(SAVED)))
        observed=t.ValidatedBuildSectionReadV1(kind='validated_build_section_read_v1',event_id=uuid4(),sequence=len(events),
            read_id=rid,source_basis=basis,source_class='saved_authored_source_not_played_truth',line_start=line,line_end=line,
            text=text,excerpt_sha256=sha256(text.encode()).hexdigest())
        events.append(observed)
        reads.append(observed)
    vote=t.BuildWriterEvidenceSelectionV1(kind='build_writer_evidence_selection_v1',event_id=uuid4(),sequence=len(events),
        policy='source_unit_selection_event_closure_v1',mode='jev',controller_attempt_id=first.provider_attempt_id,
        controller_envelope_sha256=first.envelope_sha256,controller_response_sha256='f'*64,catalog_sha256='a'*64,basis_sha256='b'*64,
        terminal_disposition={},judgments={},requested_unit_ids=[],expanded_unit_ids=[],omitted_unit_ids=[],source_event_ids=[],
        section_read_ids=[reads[-1].read_id] if selected else [])
    events.append(vote)
    root=execution(context.context_receipt_sha256,policy,events)
    identity=dict(world_id=basis.world_id,conversation_id=conversation_id,turn_id=turn_id,attempt=1,
        submitted_intent_fingerprint=t.submitted_turn_intent_fingerprint_v2(intent))
    return context,root,captured,reads,identity


def append_writer(value, *, include_sections=True, include_draft=True):
    context,root,captured,reads,_=value
    events=list(root.events)
    chosen=primary.records(root)
    writer=native_writer('build',root.policy,sequence=0)
    if captured is not None and include_draft:
        events.append(t.BuildDraftProviderInclusionV1(kind='build_draft_provider_inclusion_v1',event_id=uuid4(),sequence=len(events),
            provider_attempt_id=writer.provider_attempt_id,envelope_sha256=writer.envelope_sha256,
            draft_event_id=captured.event_id,snapshot_sha256=captured.record.snapshot.snapshot_sha256))
    if chosen and include_sections:
        events.append(t.BuildSectionProviderInclusionV1(kind='build_section_provider_inclusion_v1',event_id=uuid4(),sequence=len(events),
            context_receipt_sha256=context.context_receipt_sha256,execution_policy_sha256=root.execution_policy_sha256,
            provider_attempt_id=writer.provider_attempt_id,envelope_sha256=writer.envelope_sha256,
            section_event_ids=sorted((r.event_id for r in chosen),key=str),sections_sha256=t.build_sections_digest(chosen)))
    writer=writer.model_copy(update={'sequence':len(events)})
    return execution(context.context_receipt_sha256,root.policy,[*events,writer])


def resequence(context,root,events):
    return execution(context.context_receipt_sha256,root.policy,[e.model_copy(update={'sequence':i}) for i,e in enumerate(events)])


@pytest.mark.parametrize('with_draft,selected,expected',[(False,False,2),(False,True,2),(True,False,0),(True,True,1)])
def test_native_build_uses_existing_saved_work_selection_and_separate_draft_owner(with_draft,selected,expected):
    value=case(with_draft=with_draft,selected=selected)
    context,root,captured,reads,identity=value
    validate_context_binding(context,root)
    rows=primary.records(root,context.work_context.source_basis)
    assert len(rows)==expected
    if expected==1:
        assert rows[0].text=='Saved orchid 🌸.\r\n'
    projected=primary.project(root,context.work_context.source_basis)
    assert projected['role']==primary.ROLE and projected['policy']==(primary.DRAFT_POLICY if with_draft else primary.POLICY)
    assert len(projected['sections'])==expected
    assert not {'graph_scope','source_read_scope','working_draft_context_sha256'} & set(root.policy.model_dump())
    if captured is not None:
        draft.validate_native_record(captured.record,context,root,**identity)
        assert draft.writer_reference(captured.record)['draft_markdown']==DRAFT
        assert 'not_world_or_played_truth' in draft.writer_reference(captured.record)['role']
    written=append_writer(value)
    validate_context_binding(context,written)
    assert type(written).model_validate_json(written.model_dump_json(by_alias=True))==written


@pytest.mark.parametrize('field',['world_id','conversation_id','turn_id','attempt','submitted_intent_fingerprint'])
def test_native_draft_consumer_identity_cannot_move_to_another_turn_or_attempt(field):
    context,root,captured,_reads,identity=case()
    identity[field]='foreign' if field=='world_id' else 'a'*64 if field=='submitted_intent_fingerprint' else 2 if field=='attempt' else uuid4()
    with pytest.raises(ValueError):
        draft.validate_native_record(captured.record,context,root,**identity)


@pytest.mark.parametrize('mutation',['draft_text','draft_commitment','draft_fingerprint','duplicate_capture','late_capture',
    'missing_capture','missing_first_draft_inclusion','read_without_grant','read_duplicate','read_chars','read_range',
    'grant_capacity','read_basis','vote_origin','vote_envelope','vote_classic_sources','missing_writer_sections','missing_writer_draft',
    'pending_read','foreign_inclusion_digest','foreign_inclusion_envelope'])
def test_shared_build_rejects_broken_work_causality_or_inclusion(mutation):
    value=case()
    context,root,captured,reads,identity=value
    events=list(root.events)
    if mutation in {'missing_writer_sections','missing_writer_draft'}:
        with pytest.raises(ValueError):
            append_writer(value,include_sections=mutation!='missing_writer_sections',include_draft=mutation!='missing_writer_draft')
        return
    if mutation in {'foreign_inclusion_digest','foreign_inclusion_envelope'}:
        written=append_writer(value)
        events=list(written.events)
        index=next(i for i,e in enumerate(events) if isinstance(e,t.BuildSectionProviderInclusionV1))
        events[index]=events[index].model_copy(update={'sections_sha256':'a'*64} if mutation=='foreign_inclusion_digest' else {'envelope_sha256':'a'*64})
    elif mutation in {'draft_text','draft_commitment','draft_fingerprint'}:
        stored=captured.record
        if mutation=='draft_text':
            stored=stored.model_copy(update={'snapshot':stored.snapshot.model_copy(update={'draft_markdown':'Forged'})})
        elif mutation=='draft_commitment':
            stored=stored.model_copy(update={'expected_pointer_revision':4})
        else:
            stored=stored.model_copy(update={'submitted_intent_fingerprint':'a'*64})
        events[0]=captured.model_copy(update={'record':stored})
    elif mutation=='duplicate_capture':
        events.insert(1,captured.model_copy(update={'event_id':uuid4()}))
    elif mutation=='late_capture':
        events.insert(len(events),events.pop(0))
    elif mutation=='missing_capture':
        events.pop(0)
    elif mutation=='missing_first_draft_inclusion':
        events.pop(1)
    elif mutation=='read_without_grant':
        index=next(i for i,e in enumerate(events) if isinstance(e,t.BuildSectionReadAuthorizationV1))
        events.pop(index)
    elif mutation=='read_duplicate':
        events.insert(-1,reads[0].model_copy(update={'event_id':uuid4()}))
    elif mutation in {'read_chars','read_range','read_basis'}:
        index=events.index(reads[-1])
        original=events[index]
        if mutation=='read_chars':
            grant_index=index-1
            events[grant_index]=events[grant_index].model_copy(update={'max_chars':1})
        elif mutation=='read_range':
            events[index]=original.model_copy(update={'line_start':4,'line_end':4})
        else:
            foreign=original.source_basis.model_copy(update={'registry_revision':9})
            events[index-1]=events[index-1].model_copy(update={'source_basis':foreign})
            events[index]=original.model_copy(update={'source_basis':foreign})
    elif mutation=='grant_capacity':
        index=next(i for i,e in enumerate(events) if isinstance(e,t.BuildSectionReadAuthorizationV1))
        events[index]=events[index].model_copy(update={'max_chars':len(SAVED)+1})
    elif mutation in {'vote_origin','vote_envelope','vote_classic_sources'}:
        key={'vote_origin':'controller_attempt_id','vote_envelope':'controller_envelope_sha256','vote_classic_sources':'source_event_ids'}[mutation]
        events[-1]=events[-1].model_copy(update={key:uuid4() if mutation=='vote_origin' else 'a'*64 if mutation=='vote_envelope' else [uuid4()]})
    else:
        index=events.index(reads[-1])
        events.pop(index)
        # A provider must not consume an unresolved saved read.
        writer=native_writer('build',root.policy,sequence=len(events))
        events.append(writer)
    with pytest.raises(ValueError):
        changed=resequence(context,root,events)
        validate_context_binding(context,changed)


@pytest.mark.parametrize('with_draft',[False,True])
def test_actual_sdk_work_input_contains_exact_saved_sections_and_captured_draft(with_draft):
    from tests.test_surface_native_writer import actual_sdk_request
    context,root,captured,reads,identity=case(with_draft=with_draft)
    basis=context.work_context.source_basis
    frame=primary.native_work_frame(root,basis)
    raw=asyncio.run(actual_sdk_request(frame))
    assert primary.verify_native_work_input(root,basis,raw)==sha256(raw.encode()).hexdigest()
    assert 'graph_scope' not in frame and 'native_assertions' not in frame
    if with_draft:
        event=t.BuildDraftProviderInclusionV1(kind='build_draft_provider_inclusion_v1',event_id=uuid4(),sequence=len(root.events),
            provider_attempt_id=uuid4(),envelope_sha256=sha256(raw.encode()).hexdigest(),draft_event_id=captured.event_id,
            snapshot_sha256=captured.record.snapshot.snapshot_sha256)
        draft.validate_inclusion_input(event,root,raw)
        assert frame['working_draft_context']['draft_markdown']==DRAFT


def test_actual_work_projection_reuses_body_alias_without_donating_draft_authority():
    context,root,captured,reads,identity=case(draft_text='Saved orchid 🌸.\r\n')
    frame=primary.native_work_frame(root,context.work_context.source_basis)
    assert frame['artifact_under_edit']['sections'][0]['text_ref']=='working_draft_context'
    assert 'text' not in frame['artifact_under_edit']['sections'][0]
    restored=draft.resolve_body_aliases(frame)
    assert restored['artifact_under_edit']['sections'][0]['text']==reads[-1].text
    assert json.dumps(frame,ensure_ascii=False).count('Saved orchid 🌸.')==1


@pytest.mark.parametrize('mutation',['draft_text','draft_id','saved_text','saved_id','saved_extent','numeric_type',
    'basis','role','extra_lane','model','duplicate_frame','hidden_tool','legacy_input','inclusion_snapshot','inclusion_envelope'])
def test_native_sdk_work_proof_rejects_substituted_frame_or_inclusion(mutation):
    from tests.test_surface_native_writer import actual_sdk_request
    context,root,captured,reads,identity=case()
    basis=context.work_context.source_basis
    frame=deepcopy(primary.native_work_frame(root,basis))
    if mutation in {'draft_text','draft_id'}:
        frame['working_draft_context']['draft_markdown' if mutation=='draft_text' else 'record_id']='foreign'
    elif mutation in {'saved_text','saved_id','saved_extent','numeric_type'}:
        key={'saved_text':'text','saved_id':'read_id','saved_extent':'line_end','numeric_type':'line_start'}[mutation]
        frame['artifact_under_edit']['sections'][0][key]='foreign' if mutation in {'saved_text','saved_id'} else 9 if mutation=='saved_extent' else 3.0
    elif mutation=='basis':
        frame['source_basis']['registry_revision']+=1
    elif mutation=='role':
        frame['artifact_under_edit']['role']='accepted_world_fact'
    elif mutation=='extra_lane':
        frame['graph_authority']={'revision':'fabricated'}
    raw=asyncio.run(actual_sdk_request(frame,model='foreign' if mutation=='model' else 'gpt-6-luna'))
    if mutation=='legacy_input':
        data=json.loads(raw)
        data['input']=json.dumps(frame)
        raw=json.dumps(data)
    if mutation in {'duplicate_frame','hidden_tool'}:
        data=json.loads(raw)
        data['input'].append(data['input'][0] if mutation=='duplicate_frame' else
            {'type':'function_call_output','call_id':'foreign','output':'forged'})
        raw=json.dumps(data)
    event=t.BuildDraftProviderInclusionV1(kind='build_draft_provider_inclusion_v1',event_id=uuid4(),sequence=len(root.events),
        provider_attempt_id=uuid4(),envelope_sha256=sha256(raw.encode()).hexdigest(),draft_event_id=captured.event_id,
        snapshot_sha256=captured.record.snapshot.snapshot_sha256)
    if mutation=='inclusion_snapshot':
        event=event.model_copy(update={'snapshot_sha256':'a'*64})
    elif mutation=='inclusion_envelope':
        event=event.model_copy(update={'envelope_sha256':'a'*64})
    with pytest.raises(ValueError):
        draft.validate_inclusion_input(event,root,raw)


@pytest.mark.parametrize('mutation',[None,'writer_model','input_carrier','missing_state'])
def test_native_draft_controller_uses_only_its_typed_state_carrier(mutation):
    context,root,captured,reads,identity=case()
    body={'model':root.policy.provider_roles.controller.model,
        'state':{'working_draft_context':draft.writer_reference(captured.record)}}
    if mutation=='writer_model':
        body['model']=root.policy.provider_roles.writer.model
    elif mutation=='input_carrier':
        body['input']=json.dumps(body['state'])
    elif mutation=='missing_state':
        body.pop('state')
    raw=json.dumps(body)
    event=t.BuildDraftProviderInclusionV1(kind='build_draft_provider_inclusion_v1',event_id=uuid4(),sequence=len(root.events),
        provider_attempt_id=uuid4(),envelope_sha256=sha256(raw.encode()).hexdigest(),draft_event_id=captured.event_id,
        snapshot_sha256=captured.record.snapshot.snapshot_sha256)
    if mutation is None:
        draft.validate_inclusion_input(event,root,raw)
    else:
        with pytest.raises(ValueError,match='typed controller state'):
            draft.validate_inclusion_input(event,root,raw)
