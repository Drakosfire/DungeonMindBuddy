"""Build work claims retain their own saved/draft citation authority."""
from uuid import uuid4

from jsonschema import Draft202012Validator, ValidationError as SchemaError

import pytest

from application_state.agent_conversation import types as t
from application_state.agent_conversation.native_completion import normalize_output, verify_completion, SurfaceNativeCompletionV1
from application_state.agent_conversation.native_writer import model_work_frame
from tests.test_surface_native_work_input import work_case, produce
from tests.test_surface_native_completion import answer
from tests.test_surface_native_execution import execution
from tests.test_surface_native_writer import body_case, work_submission
from tests.test_native_corpus_source_access import lane as lane
from application_state.agent_conversation.native_writer import model_frame
from application_state.agent_conversation.plan_writer_output_schema import native_output_format
from tests.test_plan_writer_output_schema import rules


def saved_row(frame):
    return next(row for row in frame['artifact_under_edit']['sections'] if row['text']=='Saved orchid 🌸.\r\n')


def saved_candidate(frame):
    row=saved_row(frame)
    return answer([dict(kind='saved_source_claim',text='The saved page mentions an orchid.',
        section_read_ids=[row['read_id']],supporting_quotes=['Saved orchid 🌸.'])])


@pytest.mark.parametrize('kind',['discussion','draft_reference_claim','saved_source_claim'])
def test_available_work_answer_is_not_an_abstention_when_native_graph_is_unavailable(kind):
    context,record,work=work_case('build')
    frame=model_work_frame(context,record,**work)
    candidate=(saved_candidate(frame) if kind=='saved_source_claim' else answer([
        dict(kind=kind,text='Let us discuss this available working draft.',**(
            dict(draft_record_id=frame['working_draft_context']['record_id']) if kind=='draft_reference_claim' else {}))]))
    stored,auth,proof,_=produce(context,record,work,candidate=candidate)
    result=normalize_output(context,stored,auth,**proof)
    assert result.answer_context_status=={'discussion':'discussion','draft_reference_claim':'authored_grounded',
        'saved_source_claim':'source_grounded'}[kind]
    assert not any(isinstance(segment,t.SurfaceLimitationV1) for segment in result.answer_segments)


@pytest.mark.parametrize('draft',[False,True])
def test_saved_claim_has_one_completion_citation_and_no_second_binding_event(draft):
    context,record,work=work_case('build',draft=draft)
    frame=model_work_frame(context,record,**work)
    stored,auth,proof,_=produce(context,record,work,candidate=saved_candidate(frame))
    result=normalize_output(context,stored,auth,**proof)
    citation,=result.saved_source_citations
    assert isinstance(result.answer_segments[0],t.SavedSourceClaimV1)
    assert result.answer_segments[0].content_sha256==context.work_context.source_basis.content_sha256
    assert citation.segment_index==0
    expected=next(e.event_id for e in record.events if isinstance(e,t.ValidatedBuildSectionReadV1)
        and str(e.read_id)==saved_row(frame)['read_id'])
    assert citation.section_event_ids==[expected] and not auth.native_read_event_ids
    assert not result.native_body_citations and not result.native_assertion_citations
    assert SurfaceNativeCompletionV1.model_validate_json(result.model_dump_json(by_alias=True))==result
    common=t.CompletionBindingEventV1(kind='completion_binding',event_id=uuid4(),sequence=len(stored.events),
        provider_attempt_id=auth.provider_attempt_id,completion_sha256=t.canonical_sha256(result),claim_graph_event_ids={})
    bound=execution(context.context_receipt_sha256,stored.policy,[*stored.events,common])
    assert verify_completion(result,context,bound,auth,**proof)==result
    old=t.BuildSectionAnswerBindingV1(kind='build_section_answer_binding_v1',event_id=uuid4(),sequence=len(stored.events),
        provider_attempt_id=auth.provider_attempt_id,envelope_sha256=auth.envelope_sha256,
        completion_sha256=t.canonical_sha256(result),bindings=result.saved_source_citations)
    with pytest.raises(ValueError):
        execution(context.context_receipt_sha256,stored.policy,[*stored.events,old])


@pytest.mark.parametrize('mutation',['unknown_read','unselected_read','missing_quote','wrong_quote','draft_quote',
    'duplicate_read','stale_draft','no_draft','extra_metadata','native_borrow'])
def test_build_work_output_rejects_unexposed_reads_and_draft_source_borrowing(mutation):
    context,record,work=work_case('build',selected=mutation!='unselected_read',draft=mutation!='no_draft')
    frame=model_work_frame(context,record,**work)
    if mutation=='unselected_read':
        read=next(e for e in record.events if isinstance(e,t.ValidatedBuildSectionReadV1))
        candidate=answer([dict(kind='saved_source_claim',text='The saved page.',section_read_ids=[str(read.read_id)],
            supporting_quotes=['# Page'])])
    elif mutation in {'stale_draft','no_draft'}:
        candidate=answer([dict(kind='draft_reference_claim',text='A draft reference.',draft_record_id=str(uuid4()))])
    else:
        candidate=saved_candidate(frame)
        row=candidate['answer_segments'][0]
        if mutation=='unknown_read':
            row['section_read_ids']=[str(uuid4())]
        elif mutation=='missing_quote':
            row.pop('supporting_quotes')
        elif mutation=='wrong_quote':
            row['supporting_quotes']=['Saved orchids 🌸.']
        elif mutation=='draft_quote':
            row['supporting_quotes']=['An unsaved possibility']
        elif mutation=='duplicate_read':
            row['section_read_ids']*=2
            row['supporting_quotes']*=2
        elif mutation=='extra_metadata':
            row['content_sha256']='a'*64
        elif mutation=='native_borrow':
            candidate=answer([dict(kind='native_body_claim',text='A Graph fact.',excerpt_handles=[saved_row(frame)['read_id']])])
    stored,auth,proof,_=produce(context,record,work,candidate=candidate)
    with pytest.raises(ValueError):
        normalize_output(context,stored,auth,**proof)


def test_current_layout_quote_rule_is_reused_without_changing_saved_utf8():
    context,record,work=work_case('build')
    frame=model_work_frame(context,record,**work)
    candidate=saved_candidate(frame)
    candidate['answer_segments'][0]['supporting_quotes']=['Saved   orchid 🌸.']
    stored,auth,proof,_=produce(context,record,work,candidate=candidate)
    result=normalize_output(context,stored,auth,**proof)
    assert result.saved_source_citations and saved_row(frame)['text']=='Saved orchid 🌸.\r\n'


@pytest.mark.parametrize('mutation',['text_hash','read','index','source_digest'])
def test_saved_citation_cannot_change_after_exact_output_acceptance(mutation):
    context,record,work=work_case('build')
    frame=model_work_frame(context,record,**work)
    stored,auth,proof,_=produce(context,record,work,candidate=saved_candidate(frame))
    result=normalize_output(context,stored,auth,**proof).model_copy(deep=True)
    if mutation=='source_digest':
        result.answer_segments[0]=result.answer_segments[0].model_copy(update={'content_sha256':'a'*64})
    else:
        key={'text_hash':'text_sha256','read':'section_event_ids','index':'segment_index'}[mutation]
        result.saved_source_citations[0]=result.saved_source_citations[0].model_copy(update={key:
            'a'*64 if mutation=='text_hash' else [uuid4()] if mutation=='read' else 1})
    with pytest.raises(ValueError):
        verify_completion(result,context,stored,auth,**proof)


@pytest.mark.parametrize('draft',[False,True])
def test_finite_build_work_schema_only_offers_current_saved_reads_and_draft(draft):
    context,record,work=work_case('build',draft=draft)
    frame=model_work_frame(context,record,**work)
    validator=Draft202012Validator(native_output_format(model_frame(context,record),rules(),frame)['schema'])
    validator.validate(saved_candidate(frame))
    validator.validate(answer([dict(kind='discussion',text='Let us discuss.')]))
    candidate=saved_candidate(frame)
    candidate['answer_segments'][0]['section_read_ids']=[str(uuid4())]
    with pytest.raises(SchemaError):
        validator.validate(candidate)
    if draft:
        validator.validate(answer([dict(kind='draft_reference_claim',text='This draft.',
            draft_record_id=frame['working_draft_context']['record_id'])]))
    else:
        with pytest.raises(SchemaError):
            validator.validate(answer([dict(kind='draft_reference_claim',text='A different copy.',draft_record_id=str(uuid4()))]))


def test_mixed_rules_and_saved_claim_keep_one_reply_and_distinct_read_authorities():
    from tests.test_surface_native_rules import producing_case, normalize
    context,record,work=work_case('build')
    frame=model_work_frame(context,record,**work)
    def change(candidate):
        candidate['base_output']=saved_candidate(frame)
    case=producing_case(None,'build',context_record=(context,record),work_override=work,candidate_mutation=change)
    result=normalize(case)
    assert result.base_completion.saved_source_citations and not result.graph_used
    assert result.composition.rules_segments
    assert case[4].raw_output_json==case[5].text


def test_native_fact_still_inherits_native_partial_status_when_work_discussion_is_present(lane):
    context,record,_=body_case('build',lane)
    work=work_submission(context,record)
    handle=model_frame(context,record)['native_body_evidence']['excerpts'][0]['excerpt_handle']
    stored,auth,proof,_=produce(context,record,work,candidate=answer([
        dict(kind='discussion',text='Here is what the source says.'),
        dict(kind='native_body_claim',text='The check revealed another plane.',excerpt_handles=[handle])]))
    result=normalize_output(context,stored,auth,**proof)
    assert result.answer_context_status=='source_grounded_partial' and result.native_body_citations
    assert any(isinstance(segment,t.SurfaceLimitationV1) for segment in result.answer_segments)


def test_explicit_work_answer_gap_is_preserved():
    context,record,work=work_case('build')
    stored,auth,proof,_=produce(context,record,work,candidate=answer([
        dict(kind='discussion',text='The requested information remains missing.')],limitations=['missing_requested_details']))
    result=normalize_output(context,stored,auth,**proof)
    assert result.answer_context_status=='insufficient_evidence'
    assert any(isinstance(segment,t.SurfaceLimitationV1) for segment in result.answer_segments)
