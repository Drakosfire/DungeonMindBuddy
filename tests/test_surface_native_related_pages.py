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
    assert not any(isinstance(e,related.RelatedPageInclusion) for e in stored.events)
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
    'native_borrow','changed_input','changed_page_pin'])
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
    if mutation=='changed_page_pin':
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
    request=dict(state={'decision':{'state':{'interaction':{'related_page_catalog':[p.model_dump(mode='json') for p in offered]}}}},
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
    events.append(events.pop(index))
    with pytest.raises(ValueError,match='cannot change after'):
        resequence(context,record,events)


"""Exact SDK source selections replace regenerated quote witnesses, not source authority."""
from copy import deepcopy
import json
import pytest
from jsonschema import Draft202012Validator
from application_state.agent_conversation import types as t
from application_state.agent_conversation import build_related_pages as related
from application_state.agent_conversation.native_build_work_view import semantic_frame, selection_aliases
from application_state.agent_conversation.native_writer import model_work_frame, model_frame, verify_input_records
from application_state.agent_conversation.native_completion import normalize_output, verify_completion
from application_state.agent_conversation.plan_writer_output_schema import native_output_format
from tests.test_surface_native_work_input import produce
from tests.test_surface_native_execution import execution
from tests.test_surface_native_completion import answer
from tests.test_plan_writer_output_schema import rules


def proof_case(*, historical=False, edit=None, selector='related', quotes=False):
    context, record, work = case(draft=False)
    host = model_work_frame(context, record, **work)
    view = semantic_frame(host, record, supplied_source_references=not historical)
    aliases = selection_aliases(host)
    rid = host['related_authored_pages']['pages'][0]['read_id']
    if selector == 'related':
        claim = dict(kind='related_page_claim', text='The saved neighbour proposes a lamp repair.', read_id=aliases[rid])
    else:
        claim = dict(kind='saved_source_claim', text='The selected saved section is authored context.',
                     section_read_ids=[aliases[host['artifact_under_edit']['sections'][0]['read_id']]])
    if quotes:
        claim['supporting_quotes'] = ['“A copper lamp awaits repair. 🌸”']
    if edit:
        edit(claim, host)
    candidate = answer([claim])
    if not historical:
        Draft202012Validator(native_output_format(model_frame(context, record), rules(), host | view, build_local=True)['schema']).validate(candidate)
    def project(value):
        value.clear(); value.update(deepcopy(view))
    stored, old, proof, _ = produce(context, record, work, mutate=project, candidate=candidate)
    from application_state.agent_conversation.native_execution import NativeBuildWriterAuthorizedV2
    auth = NativeBuildWriterAuthorizedV2.model_validate_json(json.dumps(old.model_dump(mode='json', by_alias=True) | {
        'kind': 'native_build_writer_authorized_v2', 'work_frame_sha256': t.canonical_sha256(host)}))
    stored = execution(context.context_receipt_sha256, stored.policy,
        [auth if event.event_id == auth.event_id else event for event in stored.events])
    return context, stored, auth, proof, work, host, view


@pytest.mark.parametrize('selector', ['related', 'saved'])
def test_actual_sdk_selected_reference_binds_existing_exact_owner(selector):
    context, stored, auth, proof, work, host, view = proof_case(selector=selector)
    evidence = verify_input_records(context, stored, auth, proof['prepared_request_json'], **work)
    assert evidence.supplied_source_references
    result = normalize_output(context, stored, auth, **proof)
    assert verify_completion(result, context, stored, auth, **proof) == result
    claim, = result.answer_segments
    if selector == 'related':
        assert claim.page == evidence.related_pages[0].page
        assert evidence.related_pages[0].markdown == BODY
    else:
        assert claim.content_sha256 == host['source_basis']['content_sha256']
        assert len(result.saved_source_citations) == 1


def test_historical_quoted_contract_still_refuses_added_punctuation():
    context, stored, auth, proof, work, host, view = proof_case(historical=True, quotes=True)
    with pytest.raises(ValueError, match='quote is absent'):
        normalize_output(context, stored, auth, **proof)


@pytest.mark.parametrize('change', ['unknown', 'wrong_kind', 'host_identity', 'extra_quotes'])
def test_finite_schema_refuses_unknown_cross_kind_host_ids_and_copied_quotes(change):
    def edit(claim, host):
        if change == 'unknown': claim['read_id'] = 'source999'
        elif change == 'wrong_kind': claim['read_id'] = selection_aliases(host)[host['artifact_under_edit']['sections'][0]['read_id']]
        elif change == 'host_identity': claim['read_id'] = host['related_authored_pages']['pages'][0]['read_id']
        else: claim['supporting_quotes'] = ['arbitrary']
    from jsonschema import ValidationError
    with pytest.raises(ValidationError):
        proof_case(edit=edit)


@pytest.mark.parametrize('kind', ['saved_source_claim', 'related_page_claim'])
@pytest.mark.parametrize('selection', ['unknown', 'wrong_kind', 'duplicate', 'empty'])
def test_normalization_independently_refuses_unadmitted_and_mixed_source_choices(kind, selection):
    from application_state.agent_conversation.build_draft_answer import normalize_native_segment
    from application_state.agent_conversation.build_primary_context import records
    context, record, work = case(draft=False)
    from application_state.agent_conversation.native_build_work_view import resolve_selectors
    host = model_work_frame(context, record, **work)
    pages = related.records(record)
    sections = records(record, context.work_context.source_basis)
    actual = str(pages[0].read_id) if kind == 'related_page_claim' else str(sections[0].read_id)
    wrong = str(sections[0].read_id) if kind == 'related_page_claim' else str(pages[0].read_id)
    if kind == 'related_page_claim' and selection in {'duplicate', 'empty'}:
        value = [] if selection == 'empty' else [actual, actual]
    else:
        value = 'unadmitted' if selection == 'unknown' else wrong if selection == 'wrong_kind' else actual
    claim = dict(kind=kind, text='A proposed authored detail.')
    if kind == 'related_page_claim': claim['read_id'] = value
    else: claim['section_read_ids'] = [] if selection == 'empty' else [value, value] if selection == 'duplicate' else [value]
    with pytest.raises(ValueError):
        normalize_native_segment(claim, draft_record=None, saved_sections=sections, related_pages=pages,
            source_basis=context.work_context.source_basis, index=0, supplied_source_references=True)


@pytest.mark.parametrize('quote', [None, [], ['“Formatted quote”']])
def test_new_policy_never_infers_or_repairs_model_quote_witnesses(quote):
    from application_state.agent_conversation.build_draft_answer import normalize_native_segment
    context, record, work = case(draft=False)
    pages = related.records(record)
    with pytest.raises(ValueError, match='cannot carry regenerated quotes'):
        normalize_native_segment(dict(kind='related_page_claim', text='An authored claim.',
            read_id=str(pages[0].read_id), supporting_quotes=quote), draft_record=None,
            saved_sections=[], related_pages=pages, source_basis=context.work_context.source_basis,
            index=0, supplied_source_references=True)
