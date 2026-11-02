"""Related authored pages share their actual owner, not native fact authority."""
from hashlib import sha256
import json
from uuid import uuid4

from jsonschema import Draft202012Validator, ValidationError as SchemaError
import pytest

from application_state.agent_conversation import types as t
from application_state.agent_conversation import build_related_pages as related
from application_state.agent_conversation.native_writer import model_frame, model_work_frame, verify_input_records
from application_state.agent_conversation.native_completion import normalize_output, verify_completion
from application_state.agent_conversation.plan_writer_output_schema import native_output_format
from tests.test_surface_native_work_input import work_case, produce
from tests.test_surface_native_execution import execution
from tests.test_surface_native_completion import answer
from tests.test_plan_writer_output_schema import rules

BODY='# Neighbour\r\n\r\nA copper lamp awaits repair. 🌸\r\nKeep it dry.\r\n'


def case(*, mode='read', draft=True):
    context,record,work=work_case('build',draft=draft)
    pages=tuple(related.PagePointer(world_id=work['world_id'],document_id=uuid4(),registry_revision=3,
        title=title,visibility='internal') for title in ('Neighbour','Skipped page'))
    offered=None if mode=='absent' else () if mode=='empty' else pages
    policy=record.policy.model_copy(update={'action':record.policy.action.model_copy(update={'related_page_catalog':offered})})
    events=list(record.events)
    vote=events.pop()
    active=next(e for e in events if isinstance(e,t.ProviderAttemptAuthorizedEventV1))
    selection=None
    if offered is not None:
        selection=related.RelatedPagesSelection(event_id=uuid4(),sequence=len(events),
            controller_attempt_id=active.provider_attempt_id,controller_envelope_sha256=active.envelope_sha256,
            controller_response_sha256='f'*64,document_ids=[pages[0].document_id] if mode in {'read','pending'} else [])
        events.append(selection)
        if mode=='read':
            events.append(related.RelatedPageRead(event_id=uuid4(),sequence=len(events),read_id=uuid4(),
                selection_event_id=selection.event_id,page=related.PageReference(**pages[0].model_dump(),
                    content_sha256=sha256(BODY.encode()).hexdigest()),markdown=BODY))
    events.append(vote.model_copy(update={'sequence':len(events)}))
    return context,execution(context.context_receipt_sha256,policy,events),work


def candidate(frame):
    row=frame['related_authored_pages']['pages'][0]
    return answer([dict(kind='related_page_claim',text='The saved neighbour page proposes a lamp repair.',
        read_id=row['read_id'],supporting_quotes=['A copper lamp awaits repair. 🌸','Keep it dry.'])])


def resequence(context,record,events):
    return execution(context.context_receipt_sha256,record.policy,
        [e.model_copy(update={'sequence':i}) for i,e in enumerate(events)])


@pytest.mark.parametrize('draft',[False,True])
def test_sdk_related_page_input_and_output_reuse_exact_authored_owner(draft):
    context,record,work=case(draft=draft)
    frame=model_work_frame(context,record,**work)
    assert frame['related_authored_pages']['role']==related.ROLE
    assert frame['related_authored_pages']['availability'][1]['acquisition']=='not_read'
    stored,auth,proof,_=produce(context,record,work,candidate=candidate(frame))
    inclusion,= [e for e in stored.events if isinstance(e,related.RelatedPageInclusion)]
    related.validate_inclusion(inclusion,stored,proof['prepared_request_json'])
    evidence=verify_input_records(context,stored,auth,proof['prepared_request_json'],**work)
    result=normalize_output(context,stored,auth,**proof)
    claim,=result.answer_segments
    assert isinstance(claim,related.RelatedPageClaim)
    assert claim.page==evidence.related_pages[0].page
    assert result.answer_context_status=='authored_grounded'
    assert not auth.native_read_event_ids and not result.native_body_citations and not result.saved_source_citations
    assert verify_completion(result,context,stored,auth,**proof)==result


@pytest.mark.parametrize('mode',['absent','empty','skip'])
def test_absent_empty_and_unread_catalog_never_offer_related_fact_selectors(mode):
    context,record,work=case(mode=mode)
    frame=model_work_frame(context,record,**work)
    assert ('related_authored_pages' in frame)==(mode!='absent')
    if mode!='absent':
        assert frame['related_authored_pages']['pages']==[]
    validator=Draft202012Validator(native_output_format(model_frame(context,record),rules(),frame)['schema'])
    with pytest.raises(SchemaError):
        validator.validate(answer([dict(kind='related_page_claim',text='An unread page.',read_id=str(uuid4()),
            supporting_quotes=['A copper lamp awaits repair. 🌸'])]))
    stored,auth,proof,_=produce(context,record,work,candidate=answer([dict(kind='discussion',text='No related text supplied.')]))
    assert normalize_output(context,stored,auth,**proof).answer_context_status=='discussion'


def test_pending_selected_page_cannot_reach_the_writer():
    context,record,work=case(mode='pending')
    with pytest.raises(ValueError,match='all selected saved reads'):
        model_work_frame(context,record,**work)


@pytest.mark.parametrize('mutation',['wrong_read','wrong_quote','draft_quote','missing_quote','model_metadata','saved_borrow',
    'native_borrow','changed_input','missing_inclusion','changed_inclusion','changed_page_pin'])
def test_related_claim_cannot_borrow_another_read_or_change_its_producing_evidence(mutation):
    context,record,work=case()
    frame=model_work_frame(context,record,**work)
    output=candidate(frame)
    row=output['answer_segments'][0]
    if mutation=='wrong_read':
        row['read_id']=str(uuid4())
    elif mutation in {'wrong_quote','draft_quote'}:
        row['supporting_quotes']=['The lamp is already repaired.' if mutation=='wrong_quote' else 'An unsaved possibility']
    elif mutation=='missing_quote':
        row.pop('supporting_quotes')
    elif mutation=='model_metadata':
        row['page']=frame['related_authored_pages']['pages'][0]['page']
    elif mutation in {'saved_borrow','native_borrow'}:
        output=answer([dict(kind='saved_source_claim',text='A saved claim.',section_read_ids=[row['read_id']],
            supporting_quotes=row['supporting_quotes'])] if mutation=='saved_borrow' else [dict(kind='native_body_claim',
                text='A native claim.',excerpt_handles=[row['read_id']])])
    def mutate(physical):
        if mutation=='changed_input':
            physical['related_authored_pages']['pages'][0]['markdown']='Changed saved body'
    stored,auth,proof,_=produce(context,record,work,candidate=output,mutate=mutate)
    if mutation in {'missing_inclusion','changed_inclusion'}:
        events=list(stored.events)
        index=next(i for i,e in enumerate(events) if isinstance(e,related.RelatedPageInclusion))
        if mutation=='missing_inclusion':
            events.pop(index)
        else:
            events[index]=events[index].model_copy(update={'envelope_sha256':'a'*64})
        with pytest.raises(ValueError,match='producing exact input'):
            resequence(context,stored,events)
    elif mutation=='changed_page_pin':
        result=normalize_output(context,stored,auth,**proof)
        claim=result.answer_segments[0]
        result=result.model_copy(update={'answer_segments':[claim.model_copy(update={'page':claim.page.model_copy(
            update={'registry_revision':99})})]})
        with pytest.raises(ValueError):
            verify_completion(result,context,stored,auth,**proof)
    else:
        with pytest.raises(ValueError):
            normalize_output(context,stored,auth,**proof)


@pytest.mark.parametrize('mutation',['current_page','foreign_world','changed_body','unselected_page','late_read','duplicate_read'])
def test_related_owner_rejects_invalid_catalog_read_identity_or_order(mutation):
    context,record,work=case()
    if mutation in {'current_page','foreign_world'}:
        action=record.policy.action
        page=action.related_page_catalog[0]
        if mutation=='current_page':
            action=action.model_copy(update={'intent':action.intent.model_copy(update={
                'primary_work':action.intent.primary_work.model_copy(update={'object_id':str(page.document_id)})})})
        else:
            page=page.model_copy(update={'world_id':'foreign'})
        policy=record.policy.model_copy(update={'action':action.model_copy(update={'related_page_catalog':(page,)})})
        with pytest.raises(ValueError,match='Related page catalog'):
            execution(context.context_receipt_sha256,policy,record.events)
        return
    events=list(record.events)
    index=next(i for i,e in enumerate(events) if isinstance(e,related.RelatedPageRead))
    read=events[index]
    if mutation=='changed_body':
        events[index]=read.model_copy(update={'markdown':'Changed'})
    elif mutation=='unselected_page':
        events[index]=read.model_copy(update={'page':read.page.model_copy(update={
            'document_id':record.policy.action.related_page_catalog[1].document_id})})
    elif mutation=='late_read':
        events.append(events.pop(index))
    else:
        events.insert(index+1,read.model_copy(update={'event_id':uuid4(),'read_id':uuid4()}))
    with pytest.raises(ValueError):
        resequence(context,record,events)


@pytest.mark.parametrize('mutation',[None,'response','capture','vote','world','current_page'])
def test_same_actual_controller_vote_proof_owner_accepts_native_execution_without_a_legacy_turn(mutation):
    context,record,work=case()
    offered=record.policy.action.related_page_catalog
    event=next(e for e in record.events if isinstance(e,related.RelatedPagesSelection))
    request=dict(state={'interaction':{'related_page_catalog':[p.model_dump(mode='json') for p in offered]}},
        questions={related.question_name(i):dict(instructions=related.question_text(p),criteria={'read':{},'skip':{}})
            for i,p in enumerate(offered)})
    response=dict(answers={related.question_name(i):dict(kind='choice',selected='read' if i==0 else 'skip',
        probabilities={'read':float(i==0),'skip':float(i!=0)}) for i in range(len(offered))},
        observation=dict(latency_ms=0,retry_count=0,state='completed'))
    proof=dict(request_json=json.dumps(request),response_json=json.dumps(response))
    event=event.model_copy(update={'controller_envelope_sha256':sha256(proof['request_json'].encode()).hexdigest(),
        'controller_response_sha256':sha256(proof['response_json'].encode()).hexdigest()})
    trace={'observations':[{'kind':'context_snapshot','materials':[{
        'item_id':f'unvalidated-controller-decision:{event.controller_attempt_id}:request',
        'text':proof['response_json']}]}]}
    if mutation=='response':
        proof['response_json']+=' '
    if mutation=='capture':
        trace['observations']=[]
    if mutation=='vote':
        event=event.model_copy(update={'document_ids':[]})
    identity=dict(world_id=work['world_id'],current_document_id=context.work_context.source_basis.document_id)
    if mutation=='world':
        identity['world_id']='foreign'
    if mutation=='current_page':
        identity['current_document_id']=offered[0].document_id
    if mutation is None:
        related.validate_selection_records(record,event,proof,trace,**identity)
    else:
        with pytest.raises(ValueError):
            related.validate_selection_records(record,event,proof,trace,**identity)


def test_related_page_cannot_be_acquired_after_its_writer_input_was_frozen():
    context,record,_=case()
    events=list(record.events)
    index=next(i for i,e in enumerate(events) if isinstance(e,related.RelatedPageRead))
    events.insert(index,related.RelatedPageInclusion(event_id=uuid4(),sequence=index,
        provider_attempt_id=uuid4(),envelope_sha256='a'*64,read_ids=[]))
    with pytest.raises(ValueError,match='cannot change after'):
        resequence(context,record,events)
