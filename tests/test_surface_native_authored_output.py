"""Shared Plan saved excerpts/session summaries reuse existing exact owners."""
from uuid import uuid4

from jsonschema import Draft202012Validator, ValidationError as SchemaError
import pytest

from application_state.agent_conversation import types as t
from application_state.agent_conversation.native_completion import normalize_output, verify_completion, SurfaceNativeCompletionV1
from application_state.agent_conversation.native_writer import model_frame, model_work_frame, verify_input_records
from application_state.agent_conversation.plan_writer_output_schema import native_output_format
from application_state.agent_conversation.authored_excerpt_blocks import restore_selection_blocks
from tests.test_surface_native_work_input import work_case, produce
from tests.test_surface_native_completion import answer
from tests.test_plan_writer_output_schema import rules


def selected_rows(frame):
    plan=next(row['selection_id'] for row in frame['committed_plan_blocks'] if row['selection_id'])
    sessions=[row['selection_id'] for session in frame['session_evidence'] for source in session['sources']
        for row in source['text_blocks'] if row['selection_id']]
    return plan,sessions


def candidate_for(frame):
    plan,sessions=selected_rows(frame)
    return answer([dict(kind='authored_excerpt',selection_id=plan),
        dict(kind='authored_excerpt',selection_id=sessions[0]),
        dict(kind='session_summary',text='The saved notes leave a possibility unresolved and keep the question open.',
            selection_ids=sessions)])


def test_saved_plan_and_session_output_keep_exact_literal_bytes_and_session_owners():
    context,record,work=work_case('plan')
    frame=model_work_frame(context,record,**work)
    stored,auth,proof,_=produce(context,record,work,candidate=candidate_for(frame))
    evidence=verify_input_records(context,stored,auth,proof['prepared_request_json'],**work)
    result=normalize_output(context,stored,auth,**proof)
    assert result.answer_context_status=='authored_grounded_partial'
    plan,note,summary=result.answer_segments[:3]
    assert isinstance(plan,t.SurfaceAuthoredExcerptV1) and isinstance(summary,t.SessionSummaryV1)
    assert plan.source_kind=='plan' and plan.text==frame['committed_plan_blocks'][0]['text']
    assert '\r\n' in plan.text and plan.owner_sha256==context.work_context.plan_basis.content_sha256
    assert plan.revision==str(context.work_context.plan_basis.work_revision_id)
    assert note.source_kind=='session' and note.text==restore_selection_blocks(frame['session_evidence'][0]['sources'][0]['text_blocks'])
    assert len(summary.supports)==2
    assert {s.entry_kind for s in summary.supports}=={'scene_note','closing_reflections'}
    assert all(s.object_id==work['work_proof']['session_evidence'][0]['run_id'] for s in summary.supports)
    assert all(s.revision=='3' and s.checkpoint_content_sha256=='e'*64 for s in summary.supports)
    assert evidence.authored and all(source.text!='A live draft.' for source in evidence.authored)
    assert not result.native_body_citations and not result.native_clause_citations and not result.native_assertion_citations
    assert SurfaceNativeCompletionV1.model_validate_json(result.model_dump_json(by_alias=True))==result
    assert verify_completion(result,context,stored,auth,**proof)==result


@pytest.mark.parametrize('mutation',['foreign_selector','prior_scope','literal_text','duplicate','plan_summary',
    'native_selector','draft_selector','native_claim','session_ids_duplicate'])
def test_saved_selection_cannot_borrow_draft_native_or_foreign_authority(mutation):
    context,record,work=work_case('plan')
    frame=model_work_frame(context,record,**work)
    plan,sessions=selected_rows(frame)
    candidate=answer([dict(kind='authored_excerpt',selection_id=plan)])
    if mutation=='foreign_selector':
        candidate['answer_segments'][0]['selection_id']='foreign'
    elif mutation=='prior_scope':
        other=dict(work,idempotency_key=uuid4())
        candidate['answer_segments'][0]['selection_id']=selected_rows(model_work_frame(context,record,**other))[0]
    elif mutation=='literal_text':
        candidate['answer_segments'][0]['text']='Invented literal'
    elif mutation=='duplicate':
        candidate['answer_segments']*=2
    elif mutation=='plan_summary':
        candidate['answer_segments']=[dict(kind='session_summary',text='A played event.',selection_ids=[plan])]
    elif mutation=='native_selector':
        candidate['answer_segments']=[dict(kind='authored_excerpt',selection_id='native:unavailable')]
    elif mutation=='draft_selector':
        candidate['answer_segments']=[dict(kind='authored_excerpt',selection_id='current_page_draft')]
    elif mutation=='native_claim':
        candidate['answer_segments']=[dict(kind='native_body_claim',text='A World fact.',excerpt_handles=[plan])]
    else:
        candidate['answer_segments']=[dict(kind='session_summary',text='An unresolved recollection.',selection_ids=[sessions[0]]*2)]
    stored,auth,proof,_=produce(context,record,work,candidate=candidate)
    with pytest.raises(ValueError):
        normalize_output(context,stored,auth,**proof)


@pytest.mark.parametrize('mutation',['quote_bytes','owner','summary_entry','summary_revision','summary_text','surface'])
def test_reopened_authored_completion_must_reconstruct_the_same_producing_output(mutation):
    context,record,work=work_case('plan')
    stored,auth,proof,frame=produce(context,record,work,candidate=candidate_for(model_work_frame(context,record,**work)))
    result=normalize_output(context,stored,auth,**proof).model_copy(deep=True)
    if mutation=='surface':
        result=result.model_copy(update={'surface_id':'build'})
    elif mutation in {'quote_bytes','owner'}:
        result.answer_segments[0]=result.answer_segments[0].model_copy(update={
            'text' if mutation=='quote_bytes' else 'owner_sha256':'Changed' if mutation=='quote_bytes' else 'f'*64})
    elif mutation=='summary_text':
        result.answer_segments[2]=result.answer_segments[2].model_copy(update={'text':'A different assertion.'})
    else:
        summary=result.answer_segments[2]
        summary.supports[0]=summary.supports[0].model_copy(update={
            'element_id' if mutation=='summary_entry' else 'revision':'foreign' if mutation=='summary_entry' else '4'})
    with pytest.raises(ValueError):
        verify_completion(result,context,stored,auth,**proof)


@pytest.mark.parametrize('surface',['build','plan'])
def test_dynamic_finite_output_uses_only_the_verified_saved_work_selectors(surface):
    context,record,work=work_case(surface)
    frame=model_work_frame(context,record,**work)
    native=model_frame(context,record)
    fmt=native_output_format(native,rules(),frame)
    validator=Draft202012Validator(fmt['schema'])
    if surface=='plan':
        validator.validate(candidate_for(frame))
        invalid=candidate_for(frame)
        invalid['answer_segments'][0]['selection_id']='current_page_draft'
        with pytest.raises(SchemaError):
            validator.validate(invalid)
    else:
        with pytest.raises(SchemaError):
            validator.validate(answer([dict(kind='authored_excerpt',selection_id='foreign-plan')]))


@pytest.mark.parametrize('mixed',[False,True])
def test_rules_and_authored_output_share_one_captured_response_and_saved_support(mixed):
    from tests.test_surface_native_rules import producing_case, normalize
    context,record,work=work_case('plan')
    frame=model_work_frame(context,record,**work)
    def replace_base(candidate):
        if mixed:
            candidate['base_output']=candidate_for(frame)
        else:
            candidate.clear()
            candidate.update(candidate_for(frame))
    case=producing_case(None,'plan',context_record=(context,record),work_override=work,
        unused=not mixed,candidate_mutation=replace_base)
    result=normalize(case)
    assert result.base_completion.answer_context_status=='authored_grounded_partial'
    assert bool(result.composition.rules_segments)==mixed
    assert not result.graph_used
    assert case[4].raw_output_json==case[5].text
