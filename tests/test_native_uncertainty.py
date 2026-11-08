import pytest

from application_state.agent_conversation.native_uncertainty import project_uncertainties


def project(items, **changes):
    options = dict(raw_segments=[{'kind': 'native_body_claim', 'text': 'Two accounts differ.'}],
                   citation_indices={0}, user_question='Where and when did they rest?',
                   host_partial=False, empty_answer=False)
    return project_uncertainties(items, **(options | changes))


def test_missing_flags_are_single_generic_notice_with_raw_phrase_preserved():
    items = [{'kind': 'missing_detail', 'question_phrase': 'Where'},
             {'kind': 'missing_detail', 'question_phrase': 'when'}]
    result = project(items, host_partial=True)
    assert [s.code for s in result] == ['missing_requested_details', 'partial_retrieval']
    assert result[0].question_phrase is None
    assert result[0].text == 'The retrieved evidence does not establish all the requested details.'
    assert items[0]['question_phrase'] == 'Where'


@pytest.mark.parametrize('index', [True, 0.0, '0', -1, 1])
def test_conflict_index_must_be_strict_existing_base_index(index):
    with pytest.raises(ValueError):
        project([{'kind': 'source_conflict', 'explanation_segment_index': index}])


@pytest.mark.parametrize('kind', ['proposal', 'discussion', 'authored_excerpt',
                                'session_summary', 'draft_reference_claim', 'related_page_claim'])
def test_noneligible_segments_cannot_explain_conflict(kind):
    with pytest.raises(ValueError):
        project([{'kind': 'source_conflict', 'explanation_segment_index': 0}],
                raw_segments=[{'kind': kind}])


def test_conflict_requires_existing_owner_citation_and_distinct_reference():
    item = {'kind': 'source_conflict', 'explanation_segment_index': 0}
    with pytest.raises(ValueError):
        project([item], citation_indices=set())
    with pytest.raises(ValueError):
        project([item, item])
    assert [s.code for s in project([item])] == ['unresolved_conflict']


@pytest.mark.parametrize('items', [None, {}, [{'kind': 'partial_retrieval'}],
                                  [{'kind': 'missing_detail', 'question_phrase': 'foreign'}],
                                  [{'kind': 'missing_detail', 'question_phrase': 'Where', 'extra': 1}]])
def test_closed_shape_and_exact_question_binding(items):
    with pytest.raises(ValueError):
        project(items)


def test_empty_answer_cannot_invent_a_warning_but_collaboration_needs_none():
    with pytest.raises(ValueError):
        project([], empty_answer=True)
    assert project([]) == []
    assert project([{'kind': 'missing_detail', 'question_phrase': 'Where'}],
                   empty_answer=True)[0].code == 'missing_requested_details'


@pytest.mark.parametrize('mixed', [False, True])
def test_bound_producing_marker_selects_current_or_historical_policy(mixed):
    from application_state.agent_conversation.native_uncertainty import producing_policy, POLICY, FORMAT
    from application_state.agent_conversation.native_plan_assertions import POLICY as old
    for name, policy in [(FORMAT, POLICY), ('surface_native_evidence_selectors_v1', old)]:
        base = {'properties': {'schema': {'const': policy}}}
        schema = ({'properties': {'schema': {'const': 'dmb_rules_mixed_answer_v1'}},
                   '$defs': {'Base': base}} if mixed else base)
        body = {'text': {'format': {'type': 'json_schema', 'strict': True,
                                   'name': name, 'schema': schema}}}
        assert producing_policy(body) == policy
        base['properties']['schema']['const'] = 'foreign'
        with pytest.raises(ValueError, match='disagree'):
            producing_policy(body)
    assert producing_policy({}) == old


@pytest.mark.parametrize('format_', [None, {}, {'name': 'foreign'},
                                    {'name': 'surface_native_evidence_selectors_v2', 'schema': {}}])
def test_present_unknown_or_malformed_codec_cannot_be_historical_fallback(format_):
    from application_state.agent_conversation.native_uncertainty import producing_policy
    with pytest.raises(ValueError):
        producing_policy({'text': {'format': format_}})


@pytest.mark.parametrize('schema', [{'properties': None}, {'properties': {'schema': None}},
                                  {'properties': {'schema': {'const': 'dmb_rules_mixed_answer_v1'}}, '$defs': None}])
def test_malformed_schema_slots_fail_closed(schema):
    from application_state.agent_conversation.native_uncertainty import producing_policy, FORMAT
    with pytest.raises(ValueError):
        producing_policy({'text': {'format': dict(type='json_schema', name=FORMAT, strict=True, schema=schema)}})


def test_current_prompt_has_one_output_channel_and_only_offered_native_kinds():
    from application_state.agent_conversation.native_uncertainty import INSTRUCTIONS
    assert '"uncertainties":[]' in INSTRUCTIONS
    for obsolete_example in ['"kind":"graph_claim"', '"kind":"native_source_claim"',
                             'review_revision', '"limitations":[]', '"requested_detail_gaps":[]']:
        assert obsolete_example not in INSTRUCTIONS
    assert 'do not call a detail missing' in INSTRUCTIONS
    assert 'host derives retrieval qualification' in INSTRUCTIONS


def test_current_factory_and_retained_reconstruction_use_one_factual_grammar():
    from tests.test_surface_native_work_input import work_case
    from tests.test_plan_writer_output_schema import rules
    from application_state.agent_conversation.native_writer import model_frame, model_work_frame
    from application_state.agent_conversation.plan_writer_output_schema import native_output_format, retained_native_output_format
    from application_state.agent_conversation.native_plan_assertions import POLICY as old
    from application_state.agent_conversation.native_uncertainty import FORMAT, POLICY
    context, record, work = work_case('plan')
    frame = model_frame(context, record)
    work_frame = model_work_frame(context, record, **work)
    current = native_output_format(frame, rules(), work_frame)
    assert current['name'] == FORMAT
    assert set(current['schema']['properties']) == {'schema', 'answer_segments', 'uncertainties'}
    assert retained_native_output_format(frame, rules(), work_frame, {'text': {'format': current}}) == current
    historical_marker = dict(type='json_schema', name='surface_native_evidence_selectors_v1', strict=True,
                             schema={'properties': {'schema': {'const': old}}})
    historical = retained_native_output_format(frame, rules(), work_frame, {'text': {'format': historical_marker}})
    assert historical['schema']['properties']['schema']['const'] == old
    assert historical['schema']['properties']['answer_segments'] == current['schema']['properties']['answer_segments']
    assert set(historical['schema']['properties']) == {'schema', 'answer_segments', 'limitations', 'requested_detail_gaps'}
    assert current['schema']['properties']['schema']['const'] == POLICY
