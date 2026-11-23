"""Native output/citation component proof; no shared APP Turn activation."""
import asyncio
from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
import json
from types import SimpleNamespace as NS
from uuid import uuid4

import httpx
from openai import AsyncOpenAI
import pytest
from dungeonmind.contracts.vnext.domain import AssertionMetadata

from application_state.agent_conversation import types as t
from application_state.agent_conversation import native_plan_assertions as assertion_owner
from application_state.agent_conversation.surface_evidence_answer import ASSERTION_POLICY, native_fact_segment
from application_state.agent_conversation.native_completion import normalize_output, verify_completion, SurfaceNativeCompletionV1
from application_state.agent_conversation.native_writer import model_frame, model_work_frame
from application_state.agent_conversation.native_plan_assertions import POLICY
from apps.live_control_server.services.native_rules_capture import NativeProviderReply
from tests.test_surface_native_writer import body_case, published_case, published_lane as published_lane, authorize, work_submission, with_work_selection
from tests.test_native_corpus_source_access import lane as lane
from tests.test_surface_native_execution import execution, outcomes


async def sdk_reply(frame, answer, work_frame):
    sent=[]
    raw=json.dumps(answer)
    def wire(request):
        sent.append(request.content.decode())
        return httpx.Response(200,request=request,json={'id':'resp_native_component','object':'response',
            'created_at':1,'model':'gpt-6-luna','status':'completed','output':[
                {'type':'message','id':'msg_native_component','role':'assistant','status':'completed',
                 'content':[{'type':'output_text','text':raw,'annotations':[]}]}]})
    async with AsyncOpenAI(api_key='synthetic-not-secret',http_client=httpx.AsyncClient(
            transport=httpx.MockTransport(wire))) as client:
        response=await client.responses.create(model='gpt-6-luna',input=[dict(role='user',content=json.dumps(value)) for value in (frame,work_frame)],
            tools=[],stream=False,max_output_tokens=4096)
    assert response.status=='completed' and response.output_text==raw and len(sent)==1
    return sent[0],response.output_text


def answer(rows, *, limitations=(), gaps=()):
    return dict(schema=POLICY,answer_segments=rows,limitations=list(limitations),requested_detail_gaps=list(gaps))


def producing_case(context, record, candidate, *, work=None):
    record=with_work_selection(record)
    work=work_submission(context,record) if work is None else work
    identity={k:work[k] for k in ('world_id','conversation_id','turn_id','attempt')}
    frame=model_frame(context,record)
    raw_request,raw_output=asyncio.run(sdk_reply(frame,candidate,model_work_frame(context,record,**work)))
    stored,auth=authorize(context,record,raw_request,frame)
    api_request_id=f'generationengine:{auth.provider_attempt_id}'
    terminal=outcomes(auth,len(stored.events))
    terminal[-1]=terminal[-1].model_copy(update={'request_id':api_request_id,'response_sha256':sha256(raw_output.encode()).hexdigest()})
    stored=execution(context.context_receipt_sha256,stored.policy,[*stored.events,*terminal])
    capture=NativeProviderReply('synthetic-sdk-authorization',api_request_id,auth.provider,auth.model,auth.api_mode,
        auth.envelope_sha256,'stop','answered',raw_output,sha256(raw_output.encode()).hexdigest(),len(raw_output.encode()),())
    trace={**identity,'conversation_id':str(identity['conversation_id']),'turn_id':str(identity['turn_id']),
        'capture_status':'recording','observations':[{'kind':'context_snapshot','stage':'after','materials':[
            {'item_id':f'unvalidated-provider-answer:{auth.provider_attempt_id}:{context.context_receipt_sha256}',
             'role':'assistant','state':'model_context','text':raw_output}]}]}
    proof=dict(prepared_request_json=raw_request,raw_output_json=raw_output,capture=capture,trace=trace,**work)
    return stored,auth,proof


@pytest.mark.parametrize('surface',['build','plan'])
@pytest.mark.parametrize('full',[False,True])
@pytest.mark.parametrize('invalid_gap',[False,True])
def test_actual_sdk_native_body_answer_roundtrips_with_exact_original_citation(lane,surface,full,invalid_gap):
    context,record,read=body_case(surface,lane,full=full)
    handle=model_frame(context,record)['native_body_evidence']['excerpts'][0]['excerpt_handle']
    candidate=answer([dict(kind='native_body_claim',text='The check revealed an origin beyond this plane.',excerpt_handles=[handle])],
        gaps=[{"question_phrase": "an invented paraphrase"}] if invalid_gap else [])
    stored,auth,proof=producing_case(context,record,candidate)
    result=normalize_output(context,stored,auth,**proof)
    assert result.surface_id==surface and result.answer_context_status=='source_grounded_partial'
    assert any(getattr(row, "code", None) == "missing_requested_details"
               for row in result.answer_segments) == invalid_gap
    assert all(getattr(row, "question_phrase", None) is None for row in result.answer_segments)
    assert result.producing_provider_attempt_id==auth.provider_attempt_id
    (citation,)=result.native_body_citations
    assert citation.read_event_id==read.event_id and citation.provider_attempt_id==auth.provider_attempt_id
    assert citation.excerpt_sha256==read.excerpt.excerpt_sha256
    assert citation.selector_policy==('native_full_document_v1' if full else 'markdown_sections_v1')
    assert SurfaceNativeCompletionV1.model_validate_json(result.model_dump_json(by_alias=True))==result
    assert not {'citation_map','source_citations','graph_authority'}&set(result.model_dump())
    binding=t.CompletionBindingEventV1(kind='completion_binding',event_id=uuid4(),sequence=len(stored.events),
        provider_attempt_id=auth.provider_attempt_id,completion_sha256=t.canonical_sha256(result),claim_graph_event_ids={})
    bound=execution(context.context_receipt_sha256,stored.policy,[*stored.events,binding])
    assert verify_completion(result,context,bound,auth,**proof)==result


@pytest.mark.parametrize('surface',['build','plan'])
def test_actual_core_assertion_and_statement_answer_keep_qualifications_and_source_coordinates(published_lane,surface):
    context,record=published_case(surface,published_lane)
    frame=model_frame(context,record)
    statement=frame['native_statements']['statements'][0]['statement_handle']
    assertions=[r['assertion_handle'] for r in frame['native_assertions']['assertions']]
    candidate=answer([dict(kind='native_statement_report',text='A reported that B fled, with uncertainty.',statement_handles=[statement]),
        dict(kind='native_assertion_claim',text='The Graph preserves a provisional speculative belief.',assertion_handles=assertions)])
    stored,auth,proof=producing_case(context,record,candidate)
    result=normalize_output(context,stored,auth,**proof)
    assert result.answer_context_status=='graph_grounded_partial'
    assert result.native_clause_citations and result.native_assertion_citations
    claim=result.answer_segments[1]
    assert any(m.claim_mode=='dungeonbuddy.claim:belief' and m.standing=='provisional' for m in claim.qualifications)
    assert all(c.segment_index==1 and c.context_receipt_sha256==context.context_receipt_sha256 for c in result.native_assertion_citations)
    assert all(c.read_revision_id==context.native_query.authority.revision_id for c in result.native_assertion_citations)
    tampered=result.model_copy(deep=True)
    tampered.answer_segments[1].qualifications=[]
    with pytest.raises(ValueError):
        verify_completion(tampered,context,stored,auth,**proof)


@pytest.mark.parametrize('surface',['build','plan'])
@pytest.mark.parametrize('mutation',['output','capture_hash','capture_status','model','request_id','trace_turn','trace_producer',
    'trace_text','trace_duplicate','trace_attempt_type','ack_hash','no_response','changed_text','changed_extent','foreign_context','binding'])
def test_native_completion_rejects_producer_capture_or_citation_substitution(lane,surface,mutation):
    context,record,_=body_case(surface,lane)
    handle=model_frame(context,record)['native_body_evidence']['excerpts'][0]['excerpt_handle']
    stored,auth,proof=producing_case(context,record,answer([dict(kind='native_body_claim',text='The check revealed another plane.',excerpt_handles=[handle])]))
    result=normalize_output(context,stored,auth,**proof)
    proof=deepcopy(proof)
    if mutation=='output':
        proof['raw_output_json']+='\n'
    elif mutation=='capture_hash':
        proof['capture']=replace(proof['capture'],text_sha256='a'*64)
    elif mutation=='capture_status':
        proof['capture']=replace(proof['capture'],finish_reason='length')
    elif mutation=='model':
        proof['capture']=replace(proof['capture'],model='foreign-model')
    elif mutation=='request_id':
        proof['capture']=replace(proof['capture'],api_request_id='foreign-request')
    elif mutation=='trace_turn':
        proof['trace']['turn_id']=str(uuid4())
    elif mutation=='trace_producer':
        proof['trace']['observations'][0]['materials'][0]['item_id']='unvalidated-provider-answer:foreign'
    elif mutation=='trace_text':
        proof['trace']['observations'][0]['materials'][0]['text']='Different output'
    elif mutation=='trace_duplicate':
        proof['trace']['observations'].append(deepcopy(proof['trace']['observations'][0]))
    elif mutation=='trace_attempt_type':
        proof['trace']['attempt']=True
    elif mutation=='ack_hash':
        events=list(stored.events)
        events[-1]=events[-1].model_copy(update={'response_sha256':'a'*64})
        stored=execution(context.context_receipt_sha256,stored.policy,events)
    elif mutation=='no_response':
        stored=execution(context.context_receipt_sha256,stored.policy,stored.events[:-1])
    elif mutation=='changed_text':
        result=result.model_copy(update={'answer_segments':[t.SourcePassageClaimV1(kind='source_passage_claim',text='Different answer')]})
    elif mutation=='changed_extent':
        result.native_body_citations[0]=result.native_body_citations[0].model_copy(update={'line_end':999})
    elif mutation=='foreign_context':
        result=result.model_copy(update={'context_receipt_sha256':'a'*64})
    else:
        binding=t.CompletionBindingEventV1(kind='completion_binding',event_id=uuid4(),sequence=len(stored.events),
            provider_attempt_id=auth.provider_attempt_id,completion_sha256='a'*64,claim_graph_event_ids={})
        stored=execution(context.context_receipt_sha256,stored.policy,[*stored.events,binding])
    with pytest.raises(ValueError):
        verify_completion(result,context,stored,auth,**proof)


@pytest.mark.parametrize('surface',['build','plan'])
def test_unavailable_read_cannot_supply_fact_and_proposal_still_requires_actual_producer(lane,surface):
    context,record,_=body_case(surface,lane,failed=True)
    stored,auth,proof=producing_case(context,record,answer([dict(kind='proposal',label='invented_idea',text='We could investigate further.')]))
    result=normalize_output(context,stored,auth,**proof)
    assert result.answer_context_status=='creative_proposal'
    assert any(isinstance(s,t.SurfaceLimitationV1) and s.code=='partial_retrieval' for s in result.answer_segments)
    assert not result.native_body_citations and result.producing_provider_attempt_id==auth.provider_attempt_id
    with pytest.raises(ValueError):
        normalize_output(context,stored,auth,**(proof|{'capture':None}))
    stored,auth,proof=producing_case(context,record,answer([dict(kind='native_body_claim',text='Unsupported',excerpt_handles=['foreign'])]))
    with pytest.raises(ValueError,match='producing excerpt'):
        normalize_output(context,stored,auth,**proof)


@pytest.mark.parametrize('surface',['build','plan'])
def test_unavailable_native_capabilities_without_reads_remain_visible(lane,surface):
    from tests.test_surface_native_execution import component, controller, decision_prefix, choice
    from tests.test_surface_native_context import seal
    context,record=component(surface,unavailable=True)
    data=context.model_dump(mode='json',by_alias=True)
    data['assembled_input']['tokenizer_name']=controller(surface,record.policy).input_estimator
    context=type(context).model_validate_json(json.dumps(seal(data)))
    record=execution(context.context_receipt_sha256,record.policy)
    events,active=decision_prefix(surface,context,record)
    events.append(choice(context,record,active,len(events),'finish_retrieval'))
    record=execution(context.context_receipt_sha256,record.policy,events)
    stored,auth,proof=producing_case(context,record,answer([dict(kind='proposal',label='invented_idea',text='We could investigate.')]))
    result=normalize_output(context,stored,auth,**proof)
    assert any(isinstance(s,t.SurfaceLimitationV1) and s.code=='partial_retrieval' for s in result.answer_segments)


@pytest.mark.parametrize('surface',['build','plan'])
def test_native_writer_requires_selected_ack_and_exact_sdk_capture(lane,surface):
    context,record,_=body_case(surface,lane)
    handle=model_frame(context,record)['native_body_evidence']['excerpts'][0]['excerpt_handle']
    stored,auth,proof=producing_case(context,record,answer([dict(kind='native_body_claim',text='The check revealed another plane.',excerpt_handles=[handle])]))
    events=list(stored.events)
    events[-1]=events[-1].model_copy(update={'response_sha256':None})
    # Shared writer acknowledgement means verified selected output, not merely
    # HTTP receipt. A crash before selection stays sdk_entered/unknown.
    with pytest.raises(ValueError,match='selected output acknowledgement'):
        execution(context.context_receipt_sha256,stored.policy,events)
    assert normalize_output(context,stored,auth,**proof).native_body_citations
    with pytest.raises(ValueError):
        normalize_output(context,stored,auth,**(proof|{'capture':replace(proof['capture'],text_sha256='a'*64)}))


@pytest.mark.parametrize('surface',['build','plan'])
def test_retained_completion_reuses_exact_native_body_citation_owner(lane,surface,monkeypatch):
    context,record,_=body_case(surface,lane)
    handle=model_frame(context,record)['native_body_evidence']['excerpts'][0]['excerpt_handle']
    stored,auth,proof=producing_case(context,record,answer([dict(kind='native_body_claim',
        text='The check revealed another plane.',excerpt_handles=[handle])]))
    completion=normalize_output(context,stored,auth,**proof)
    binding=t.CompletionBindingEventV1(kind='completion_binding',event_id=uuid4(),sequence=len(stored.events),
        provider_attempt_id=auth.provider_attempt_id,completion_sha256=t.canonical_sha256(completion),claim_graph_event_ids={})
    stored=execution(context.context_receipt_sha256,stored.policy,[*stored.events,binding])
    from application_state.agent_conversation import native_writer

    expected_prefix = execution(context.context_receipt_sha256, stored.policy, stored.events[:auth.sequence])
    expected_frame = model_frame(context, expected_prefix)
    project = native_writer._model_frame_from_validated_prefix
    projected = []

    def verify_owned_prefix(receipt, prefix, **options):
        assert receipt == context and receipt is not context
        assert prefix == expected_prefix
        assert prefix.events[0] is not stored.events[0]
        frame = project(receipt, prefix, **options)
        assert frame == expected_frame
        projected.append(frame)
        return frame

    monkeypatch.setattr(native_writer, "_model_frame_from_validated_prefix", verify_owned_prefix)
    t.validate_execution_completion(completion,context,stored,auth.provider_attempt_id,{})
    assert projected == [expected_frame]
    changed=completion.model_copy(deep=True)
    changed.native_body_citations[0]=changed.native_body_citations[0].model_copy(update={'native_source_revision_id':'foreign'})
    event=binding.model_copy(update={'completion_sha256':t.canonical_sha256(changed)})
    modified=execution(context.context_receipt_sha256,stored.policy,[*stored.events[:-1],event])
    with pytest.raises(ValueError,match='citation'):
        t.validate_execution_completion(changed,context,modified,auth.provider_attempt_id,{})


@pytest.mark.parametrize('surface',['build','plan'])
def test_retained_completion_reuses_exact_native_assertion_and_statement_owners(published_lane,surface):
    context,record=published_case(surface,published_lane)
    frame=model_frame(context,record)
    stored,auth,proof=producing_case(context,record,answer([
        dict(kind='native_statement_report',text='A reported that B fled.',
            statement_handles=[frame['native_statements']['statements'][0]['statement_handle']]),
        dict(kind='native_assertion_claim',text='A provisional belief remains qualified.',
            assertion_handles=[r['assertion_handle'] for r in frame['native_assertions']['assertions']])]))
    completion=normalize_output(context,stored,auth,**proof)
    binding=t.CompletionBindingEventV1(kind='completion_binding',event_id=uuid4(),sequence=len(stored.events),
        provider_attempt_id=auth.provider_attempt_id,completion_sha256=t.canonical_sha256(completion),claim_graph_event_ids={})
    stored=execution(context.context_receipt_sha256,stored.policy,[*stored.events,binding])
    t.validate_execution_completion(completion,context,stored,auth.provider_attempt_id,{})
    changed=completion.model_copy(deep=True)
    changed.native_assertion_citations[0]=changed.native_assertion_citations[0].model_copy(update={'read_revision_id':'foreign'})
    event=binding.model_copy(update={'completion_sha256':t.canonical_sha256(changed)})
    modified=execution(context.context_receipt_sha256,stored.policy,[*stored.events[:-1],event])
    with pytest.raises(ValueError,match='support'):
        t.validate_execution_completion(changed,context,modified,auth.provider_attempt_id,{})


# Repeated native Graph reads retain each source citation.
def duplicate_fixture_metadata():
    return AssertionMetadata(
        visibility={'kind': 'labels_any', 'labels': ['dungeonbuddy.visibility:gm']},
        epistemic_basis='asserted', claim_mode='dungeonbuddy.claim:fact',
        standing='established', temporal_scope={'kind': 'unknown'},
    )


def duplicate_fixture_cite(receipt, auth, event, read, span, *, index):
    return NS(segment_index=index, read_event_id=event.event_id,
              assertion_id=read.assertion.assertion_id, evidence_ref_id=span.evidence_ref_id)


def test_repeated_assertion_reads_keep_each_citation_and_validate_closure(monkeypatch):
    monkeypatch.setattr(assertion_owner, 'citation', duplicate_fixture_cite)
    assertion = NS(assertion_id='assertion-A', metadata=duplicate_fixture_metadata())
    first, second = NS(event_id='first'), NS(event_id='second')
    a = NS(assertion=assertion, spans=(NS(evidence_ref_id='span-A'),))
    b = NS(assertion=assertion, spans=(NS(evidence_ref_id='span-B'),))
    support = NS(native_assertions=(('handle-A', first, a), ('handle-B', second, b)),
                 native_statements=(), body_excerpts=())
    row = {'kind': 'native_assertion_claim', 'text': 'A supported fact.',
           'assertion_handles': ['handle-A', 'handle-B']}
    claim, _, _, citations = native_fact_segment(row, policy=ASSERTION_POLICY, receipt=None,
        auth=NS(provider_attempt_id='synthetic'), support=support, index=0)
    assert claim.assertion_ids == ['assertion-A']
    assert len(claim.qualifications) == 1
    assert [(c.read_event_id, c.evidence_ref_id) for c in citations] == [
        ('first', 'span-A'), ('second', 'span-B')]
    reads = {('first', 'assertion-A'): (first, a), ('second', 'assertion-A'): (second, b)}
    completion = NS(answer_segments=[claim], native_assertion_citations=citations)
    assertion_owner.validate_citation_records(completion, None, None, reads)
    completion.native_assertion_citations = citations[:1]
    with pytest.raises(ValueError, match='omitted a supporting span'):
        assertion_owner.validate_citation_records(completion, None, None, reads)
    completion.native_assertion_citations = [NS(segment_index=0, read_event_id='foreign',
        assertion_id='assertion-A', evidence_ref_id='span-A')]
    with pytest.raises(ValueError, match='lacks exact included support'):
        assertion_owner.validate_citation_records(completion, None, None, reads)


def test_duplicate_or_unknown_handles_remain_rejected():
    support = NS(native_assertions=(('handle-A', NS(), NS()),), native_statements=(), body_excerpts=())
    for handles in (['handle-A', 'handle-A'], ['handle-A', 'foreign']):
        with pytest.raises(ValueError, match='exact included assertion handles'):
            native_fact_segment({'kind': 'native_assertion_claim', 'text': 'A fact.',
                'assertion_handles': handles}, policy=ASSERTION_POLICY, receipt=None,
                auth=NS(provider_attempt_id='synthetic'), support=support, index=0)


def test_distinct_assertions_remain_distinct(monkeypatch):
    monkeypatch.setattr(assertion_owner, 'citation', duplicate_fixture_cite)
    first, second = NS(event_id='first'), NS(event_id='second')
    a = NS(assertion=NS(assertion_id='assertion-B', metadata=duplicate_fixture_metadata()),
           spans=(NS(evidence_ref_id='span-B'),))
    b = NS(assertion=NS(assertion_id='assertion-A', metadata=duplicate_fixture_metadata()),
           spans=(NS(evidence_ref_id='span-A'),))
    support = NS(native_assertions=(('handle-B', first, a), ('handle-A', second, b)),
                 native_statements=(), body_excerpts=())
    claim, _, _, citations = native_fact_segment(
        {'kind': 'native_assertion_claim', 'text': 'Two supported facts.',
         'assertion_handles': ['handle-B', 'handle-A']}, policy=ASSERTION_POLICY,
        receipt=None, auth=NS(provider_attempt_id='synthetic'), support=support, index=0)
    assert claim.assertion_ids == ['assertion-A', 'assertion-B']
    assertion_owner.validate_citation_records(NS(answer_segments=[claim], native_assertion_citations=citations),
        None, None, {('first', 'assertion-B'): (first, a), ('second', 'assertion-A'): (second, b)})
