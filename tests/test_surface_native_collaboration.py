"""Typed author reviews remain proposals, with their actual existing owners."""
import json
from uuid import uuid4

from jsonschema import Draft202012Validator
import pytest

from application_state.agent_conversation import types as t
from application_state.agent_conversation import build_draft_context as draft
from application_state.agent_conversation import build_intentional_response as semantic
from application_state.agent_conversation import plan_objective
from application_state.agent_conversation.collaboration import saved_excerpt
from application_state.agent_conversation.native_completion import normalize_output, verify_completion
from application_state.agent_conversation.native_writer import model_frame, model_work_frame
from application_state.agent_conversation.native_plan_assertions import POLICY
from application_state.agent_conversation.plan_writer_output_schema import native_output_format
from application_state.build_proposal.types import BuildWriteCapability
from tests.test_surface_native_execution import execution, build_resolution
from tests.test_surface_native_work_input import work_case, produce
from tests.test_surface_native_related_pages import case as related_case
from tests.test_plan_writer_output_schema import rules


def case(kind='questions',*,with_draft=True,with_related=False,capabilities=True,plan_contract=True):
    context,record,work=related_case(draft=with_draft) if with_related else work_case('build',draft=with_draft)
    label={'questions':'clarify_request','plan':'plan','connected_page':'review_connected_page',
        'relationship':'review_relationship','discuss':'discuss'}[kind]
    captured=draft.context_record(record) if with_draft else None
    cap=None
    if with_draft:
        snap=captured.record.snapshot
        cap=BuildWriteCapability(idempotency_key=uuid4(),conversation_id=work['conversation_id'],expected_pointer_revision=3,
            basis=dict(**context.work_context.source_basis.model_dump(),draft_sha256=snap.draft_sha256,
                editor_sha256=snap.editor_sha256,caret=0,draft_generation=snap.draft_generation,selection_generation=0),
            draft_markdown=snap.draft_markdown)
    action=record.policy.action
    intent=action.intent.model_copy(update={'build_write_capability_sha256':None if cap is None else t.canonical_sha256(cap.model_dump(mode='json'))})
    action=action.model_copy(update={'intent':intent,'write_capability':cap,'capabilities':semantic.Capabilities(
        ('answer_from_sources','propose_build_insertion') if cap else ('answer_from_sources',),
        ('questions','plan','connected_page','relationship') if capabilities else None, bool(cap),None)})
    policy=record.policy.model_copy(update={'action':action})
    events=[]
    for event in record.events:
        if isinstance(event,t.BuildDraftContextCapturedV1):
            event=event.model_copy(update={'record':event.record.model_copy(update={
                'submitted_intent_fingerprint':t.submitted_turn_intent_fingerprint_v2(intent)})})
        elif isinstance(event,t.BuildRequestedWorkResolutionV1):
            controller=next(e for e in record.events if isinstance(e,t.ProviderAttemptAuthorizedEventV1)
                and e.provider_attempt_id==event.controller_attempt_id)
            event=build_resolution(policy,controller,event.sequence,turn_id=work['turn_id'],requested=label)
        events.append(event)
    record=execution(context.context_receipt_sha256,policy,events)
    if kind=='plan' and plan_contract:
        contract=plan_objective.create(record,cap)
        assert contract is not None
        record=execution(context.context_receipt_sha256,policy,[*record.events,contract])
    return context,record,work


def output(frame,kind='questions',*,related=False):
    obj={'kind':'questions','questions':[{'text':'Which errand should we develop?'}]}
    if kind=='plan':
        obj=dict(kind='plan',objective='Develop the selected errand.',steps=[
            dict(text='Discuss the repair.',kind='discuss',selected=True),
            dict(text='Prepare writing after that choice.',kind='prepare_insertion',selected=False)])
    elif kind in {'connected_page','relationship'}:
        frame=draft.resolve_body_aliases(frame)
        row=(frame['related_authored_pages']['pages'][0] if related else
            next(row for row in frame['artifact_under_edit']['sections'] if 'Saved orchid' in row['text']))
        quote='A copper lamp awaits repair. 🌸' if related else 'Saved orchid 🌸.'
        if kind=='connected_page':
            obj=dict(kind=kind,title='Orchid Workshop',read_id=row['read_id'],quote=quote,
                person_label=None,relationships=[],instructions='Develop a possible workshop for author review.')
        else:
            obj=dict(kind=kind,read_id=row['read_id'],quote=quote,
                source=dict(label='Proposed keeper',kind='npc'),target=dict(label='Proposed trader',kind='npc'),
                predicate='works_with',label='proposed collaboration',context='Unpublished possibility for author review.')
    return dict(schema=POLICY,answer_segments=[],limitations=[],requested_detail_gaps=[],collaboration=obj)


@pytest.mark.parametrize('kind,with_draft',[(kind,drafted) for kind in ('questions','plan','connected_page','relationship')
    for drafted in (False,True) if kind!='plan' or drafted])
def test_object_only_review_uses_actual_owners_without_invented_prose(kind,with_draft):
    context,record,work=case(kind,with_draft=with_draft)
    frame=model_work_frame(context,record,**work)
    raw=output(frame,kind)
    Draft202012Validator(native_output_format(model_frame(context,record),rules(),frame)['schema']).validate(raw)
    stored,auth,proof,_=produce(context,record,work,candidate=raw)
    completion=normalize_output(context,stored,auth,**proof)
    assert completion.answer_segments==[] and completion.answer_context_status=='discussion'
    assert completion.collaboration.model_dump(mode='json')==raw['collaboration']
    assert not completion.native_body_citations and not completion.saved_source_citations
    assert verify_completion(completion,context,stored,auth,**proof)==completion
    if kind=='plan':
        assert completion.collaboration.steps[1].selected is False
        assert frame[plan_objective.KEY]['kind']=='build_plan_output_contract_v2'
    if kind=='connected_page':
        from application_state.agent_conversation.connected_page_origins import execution_rows
        origin=saved_excerpt(completion.collaboration,execution_rows(stored,context.work_context.source_basis,auth.provider_attempt_id))
        assert origin['line_start']==3 and origin['revision']==context.work_context.source_basis.registry_revision


@pytest.mark.parametrize('kind',['questions','plan','connected_page','relationship'])
def test_actual_sdk_mixed_rules_schema_keeps_review_and_existing_definitions(kind):
    from tests.test_surface_native_rules import producing_case, normalize
    context,record,work=case(kind,with_related=kind=='connected_page')
    frame=model_work_frame(context,record,**work)
    def change(candidate):
        candidate['base_output']=output(frame,kind,related=kind=='connected_page')
    result_case=producing_case(None,'build',context_record=(context,record),work_override=work,candidate_mutation=change)
    body=json.loads(result_case[4].prepared_request_json)
    fmt=body['text']['format']
    assert fmt['strict'] is True
    validator=Draft202012Validator(fmt['schema'])
    validator.check_schema(fmt['schema'])
    validator.validate(json.loads(result_case[4].raw_output_json))
    result=normalize(result_case)
    assert result.base_completion.collaboration.kind==kind
    assert not result.base_completion.answer_segments and result.composition.rules_segments
    assert result.assistant_text and not result.graph_used


@pytest.mark.parametrize('mutation',['wrong_kind','missing','null','duplicate_question','plan_without_contract',
    'unselected_read','draft_quote','wrong_quote','ambiguous_quote','model_metadata','capability_absent','empty_total'])
def test_typed_review_cannot_substitute_kind_capability_capture_or_saved_support(mutation):
    kind='plan' if mutation=='plan_without_contract' else 'connected_page' if mutation in {
        'unselected_read','draft_quote','wrong_quote','ambiguous_quote','model_metadata'} else 'questions'
    context,record,work=case(kind,with_related=mutation=='ambiguous_quote',capabilities=mutation!='capability_absent',plan_contract=mutation!='plan_without_contract')
    frame=model_work_frame(context,record,**work)
    raw=output(frame,kind,related=mutation=='ambiguous_quote')
    if mutation=='wrong_kind':
        raw['collaboration']=dict(kind='plan',objective='Wrong requested kind.',steps=[dict(text='Discuss.',kind='discuss',selected=True)])
    elif mutation=='missing':
        raw.pop('collaboration')
    elif mutation=='null':
        raw['collaboration']=None
    elif mutation=='duplicate_question':
        raw['answer_segments']=[dict(kind='discussion',text=raw['collaboration']['questions'][0]['text'])]
    elif mutation=='unselected_read':
        raw['collaboration']['read_id']=str(uuid4())
    elif mutation=='draft_quote':
        raw['collaboration']['quote']='An unsaved possibility'
    elif mutation=='wrong_quote':
        raw['collaboration']['quote']='Saved orchids 🌸.'
    elif mutation=='ambiguous_quote':
        raw['collaboration']['quote']='a'
    elif mutation=='model_metadata':
        raw['collaboration']['origin']={'line_start':999}
    elif mutation=='empty_total':
        context,record,work=case('discuss')
        raw['collaboration']=None
    stored,auth,proof,_=produce(context,record,work,candidate=raw)
    with pytest.raises(ValueError):
        normalize_output(context,stored,auth,**proof)


@pytest.mark.parametrize('field',['selection_sha256','draft_record_id','working_snapshot_sha256',
    'destination_capability_sha256','plan_schema_sha256'])
def test_existing_plan_contract_rejects_changed_selection_draft_destination_or_schema(field):
    context,record,_=case('plan')
    events=list(record.events)
    event=events[-1]
    events[-1]=event.model_copy(update={field:uuid4() if field=='draft_record_id' else 'b'*64})
    with pytest.raises(ValueError):
        execution(context.context_receipt_sha256,record.policy,events)


def test_review_is_bound_to_exact_final_captured_output():
    context,record,work=case('questions')
    frame=model_work_frame(context,record,**work)
    stored,auth,proof,_=produce(context,record,work,candidate=output(frame))
    completion=normalize_output(context,stored,auth,**proof).model_copy(deep=True)
    completion=completion.model_copy(update={'collaboration':completion.collaboration.model_copy(update={
        'questions':[completion.collaboration.questions[0].model_copy(update={'text':'Changed afterward?'})]})})
    with pytest.raises(ValueError):
        verify_completion(completion,context,stored,auth,**proof)


@pytest.mark.parametrize('kind',['questions','plan','connected_page','relationship'])
def test_actual_sdk_object_only_without_rules_retains_the_review_directly(kind):
    from tests.test_surface_native_rules import producing_case, normalize
    context,record,work=case(kind)
    frame=model_work_frame(context,record,**work)
    def change(candidate):
        candidate.clear()
        candidate.update(output(frame,kind))
    produced=producing_case(None,'build',unused=True,context_record=(context,record),
        work_override=work,candidate_mutation=change)
    result=normalize(produced)
    assert result.base_completion.collaboration.kind==kind
    assert result.composition is None and result.assistant_text==''
    assert not result.graph_used and not result.claim_graph_event_ids


@pytest.mark.parametrize('mutation',['dropped','dict','opaque','invalid_typed','fake_text','approved'])
def test_object_only_composition_requires_the_actual_typed_normalized_base(mutation):
    from types import SimpleNamespace
    from application_state.agent_conversation.rules_authority_output import parse_answer
    from tests.test_surface_native_rules import producing_case, normalize
    context,record,work=case()
    frame=model_work_frame(context,record,**work)
    def change(candidate):
        candidate['base_output']=output(frame)
    produced=producing_case(None,'build',context_record=(context,record),work_override=work,candidate_mutation=change)
    result=normalize(produced)
    base=result.base_completion
    segments=()
    disposition='unclaimed'
    if mutation=='dropped':
        base=None
    elif mutation=='dict':
        base=base.model_dump(mode='json')
    elif mutation=='opaque':
        base=SimpleNamespace(answer_segments=(),collaboration=base.collaboration)
    elif mutation=='invalid_typed':
        base=base.model_copy(update={'collaboration':None})
    elif mutation=='fake_text':
        segments=('Invented paragraph',)
    else:
        disposition='approved'
    refs=next(e.support_refs for e in produced[2].events if e.kind=='provider_included')
    with pytest.raises(ValueError):
        parse_answer(produced[4].raw_output_json).composition(base_completion=base,
            base_segments=segments,base_disposition=disposition,supplied_refs=refs)


def test_mixed_object_only_base_still_requires_its_raw_partition_marker():
    from tests.test_surface_native_rules import producing_case, normalize
    context,record,work=case()
    frame=model_work_frame(context,record,**work)
    def change(candidate):
        candidate['base_output']=output(frame)
        candidate['ordered_refs']=[dict(domain='rules',segment_index=0)]
    produced=producing_case(None,'build',context_record=(context,record),work_override=work,candidate_mutation=change)
    with pytest.raises(ValueError,match='exactly one marker'):
        normalize(produced)


@pytest.mark.parametrize('mutation',['dropped','text','graph','claim_map','composition_dropped_with_text'])
def test_no_composition_wrapper_cannot_discard_text_or_claim_acceptance(mutation):
    from dataclasses import replace
    from application_state.agent_conversation.native_rules_output import NativeRulesNormalizedOutputV1
    context,record,work=case()
    frame=model_work_frame(context,record,**work)
    stored,auth,proof,_=produce(context,record,work,candidate=output(frame))
    completion=normalize_output(context,stored,auth,**proof)
    result=NativeRulesNormalizedOutputV1(completion,{},None,'',False)
    updates={
        'dropped':dict(base_completion=None), 'text':dict(assistant_text='Unmapped text'),
        'graph':dict(graph_used=True), 'claim_map':dict(claim_graph_event_ids={'fake':[uuid4()]}),
        'composition_dropped_with_text':dict(base_completion=completion.model_copy(update={
            'answer_segments':[t.PlanWorldGraphProposalSegmentV1(kind='proposal',label='invented_idea',text='Unplayed possibility.')]})),
    }
    with pytest.raises(ValueError):
        replace(result,**updates[mutation])
