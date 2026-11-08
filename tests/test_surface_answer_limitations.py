"""Current and retained limitation projection contracts, without providers."""
from copy import deepcopy
from itertools import permutations

import pytest

from application_state.agent_conversation.source_writer_output import project_surface_limitations


def project(codes=(), gaps=(), *, question='first and second', derive=True, partial=False, empty=False):
    return project_surface_limitations(list(codes), list(gaps), user_question=question,
        derive_missing=derive, host_partial=partial, empty_answer=empty, strict_gap_array=True)


@pytest.mark.parametrize('codes', [p for n in range(4) for p in permutations(
    ('unresolved_conflict','partial_retrieval','missing_requested_details'),n)])
def test_supplied_code_order_and_host_partial_are_preserved(codes):
    result=project(codes,partial=True)
    expected=list(codes)+([] if 'partial_retrieval' in codes else ['partial_retrieval'])
    assert [s.code for s in result]==expected
    assert all(s.question_phrase is None for s in result)


def test_derivation_and_original_gap_order_preserve_retained_duplicate_caveats():
    codes=['unresolved_conflict'];gaps=[{'question_phrase':'second'},{'question_phrase':'first'}]
    before=deepcopy((codes,gaps))
    result=project_surface_limitations(codes,gaps,user_question='first and second',
        derive_missing=True,host_partial=True,empty_answer=False,strict_gap_array=True)
    assert [(s.code,s.question_phrase) for s in result]==[
        ('unresolved_conflict',None),('missing_requested_details',None),
        ('partial_retrieval',None),('missing_requested_details','second'),('missing_requested_details','first')]
    assert (codes,gaps)==before
    assert result[1].text=='The retrieved evidence does not establish all the requested details.'
    assert result[-1].text=='The selected source excerpts do not establish: “first”.'


def test_historical_missing_flag_requirement_is_not_silently_upgraded():
    with pytest.raises(ValueError,match='Gaps require'):
        project(gaps=[{'question_phrase':'first'}],derive=False)
    assert len(project(['missing_requested_details'],[{'question_phrase':'first'}],derive=False))==2


def test_empty_answer_fallback_and_collaboration_only_are_distinct():
    assert project()==[]  # Existing collaboration/discussion can be sufficient.
    assert [s.code for s in project(empty=True)]==['missing_requested_details']
    assert [s.code for s in project(partial=True,empty=True)]==['partial_retrieval']
    assert [s.code for s in project(['partial_retrieval'])]==['partial_retrieval']


def test_exact_phrase_escaping_and_serialized_fields_remain_stable():
    result=project(gaps=[{'question_phrase':'rest-location'}],question='Which rest-location?',derive=True)
    assert result[-1].model_dump(mode='json')=={
        'kind':'limitation','code':'missing_requested_details',
        'text':'The selected source excerpts do not establish: “rest\\-location”.',
        'question_phrase':'rest-location'}


@pytest.mark.parametrize('codes,gaps,question',[
    (['unknown'],[],'first'),(['partial_retrieval','partial_retrieval'],[],'first'),
    ([1],[],'first'),('partial_retrieval',[],'first'),([],{},'first'),
    ([],[{'question_phrase':'absent'}],'first'),
    ([],[{'question_phrase':'first'}],'first first'),
    ([],[{'question_phrase':'first'},{'question_phrase':'first and'}],'first and second'),
    ([],[{'question_phrase':' first '}],' first '),
    ([],[{'question_phrase':'first\nsecond'}],'first\nsecond'),
    ([],[],''),
])
def test_malformed_or_unsafe_declarations_remain_rejected(codes,gaps,question):
    with pytest.raises(ValueError):
        project_surface_limitations(codes,gaps,user_question=question,
            derive_missing=True,host_partial=False,empty_answer=False,strict_gap_array=True)


@pytest.mark.parametrize('gaps',[{},'',[],()])
def test_existing_surface_iterable_decoding_and_native_array_requirement(gaps):
    kwargs=dict(user_question='first',derive_missing=True,host_partial=False,empty_answer=True)
    assert [s.code for s in project_surface_limitations([],gaps,strict_gap_array=False,**kwargs)]==['missing_requested_details']
    if isinstance(gaps,list):
        assert project_surface_limitations([],gaps,strict_gap_array=True,**kwargs)
    else:
        with pytest.raises(ValueError):
            project_surface_limitations([],gaps,strict_gap_array=True,**kwargs)
