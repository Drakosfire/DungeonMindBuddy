"""Prospective contract invariants; none of these tests establishes APP/runtime adoption."""
from copy import deepcopy
import json

import pytest
from generationengine.types import DecisionRequest

from application_state.agent_conversation.build_draft_answer import normalize
from evals.utterance_intent import semantic_contract as c
from evals.utterance_intent import semantic_proof as p
from evals.utterance_intent.proof import sdk_request


def case(name='opener'):
    name, question, expected = next(row for row in p.FRESH if row[0] == name)
    return {'id': name, 'question': question, 'cohort': 'synthetic', 'expected_work': [expected]}


def actual(label='discuss', other=None):
    probabilities = {key: 0.0 for key in c.WORK}
    probabilities[label] = 1.0
    if other:
        probabilities.update(other)
    return {'answers': {'requested_work': {'selected': label, 'probabilities': probabilities}}}


def neutral(text='Ready. What would you like to try?'):
    return {'answer_context_status': 'discussion', 'answer_segments': [{'kind': 'discussion', 'text': text}],
            'limitations': [], 'requested_detail_gaps': [], 'collaboration': None}


def prepared(name='opener'):
    row = case(name)
    resolution = c.resolve(row['expected_work'][0], p.capabilities(row))
    request, packet = c.writer_request(p.discussion_packet(row), resolution)
    return request, packet, resolution


def test_semantic_menu_remains_real_and_auxiliary_questions_survive_without_editor():
    control = p.synthetic_control('Make a table.')
    control['state']['decision']['state']['interaction']['allowed_operations'] = ['answer_from_sources']
    control['questions']['rules_query'] = {'type': 'choice', 'instructions': 'Rules?', 'criteria': {'read': None, 'skip': None}}
    original = deepcopy(control)
    candidate = c.candidate(control)
    request = DecisionRequest.model_validate(sdk_request(candidate))
    assert len(request.questions[0].options) == 14
    assert request.questions[0].name == 'requested_work'
    assert 'cannot_select' not in request.questions[0].options
    assert candidate['questions']['rules_query'] == control['questions']['rules_query']
    assert control == original
    assert 'build_encounter' in request.questions[0].options


@pytest.mark.parametrize('label', sorted(c.UNAVAILABLE))
def test_unavailable_creation_preserves_requested_intent_and_never_resolves_to_page_prose(label):
    resolution = c.resolve(label, c.Capabilities(c.OPERATIONS, c.REVIEWS, True))
    assert resolution['requested_work'] == label and resolution['intent_family'] == 'create'
    assert resolution['operation'] == 'answer_from_sources'
    assert resolution['purpose'] == 'explain_capability'
    assert not any('map' in x or 'mechanic' in x for x in resolution['available_followups'])


def test_current_conversation_does_not_erase_available_followup_writing():
    resolution = c.resolve('discuss', c.Capabilities(c.OPERATIONS, c.REVIEWS, True))
    assert resolution['operation'] == 'answer_from_sources'
    assert 'prepare_current_page_writing' in resolution['available_followups']
    missing = c.resolve('write_current_page', c.Capabilities(('answer_from_sources',), (), False))
    assert missing['requested_work'] == 'write_current_page'
    assert missing['barrier'] == 'current_page_target_absent'
    assert 'prepare_current_page_writing' not in missing['available_followups']


def test_uncaptured_review_is_not_falsely_labeled_unavailable():
    unknown = c.resolve('plan', c.Capabilities(c.OPERATIONS))
    absent = c.resolve('plan', c.Capabilities(c.OPERATIONS, (), False))
    assert unknown['barrier'] == 'review_capability_not_captured'
    assert absent['barrier'] == 'requested_review_not_offered'


@pytest.mark.parametrize('mutate', [
    lambda a: a['answers']['requested_work'].update(selected='cannot_select'),
    lambda a: a['answers']['requested_work']['probabilities'].update(discuss=float('nan')),
    lambda a: a['answers']['requested_work']['probabilities'].update(discuss=True),
    lambda a: a['answers']['requested_work']['probabilities'].update(discuss=.5, plan=.5),
    lambda a: a['answers']['requested_work']['probabilities'].pop('plan'),
])
def test_invalid_semantic_results_fail_closed_instead_of_clarification(mutate):
    response = actual()
    mutate(response)
    with pytest.raises(ValueError):
        c.selected(response)


def test_neutral_ack_needs_no_fabricated_gap_suggestion_or_page_recap():
    request, packet, resolution = prepared()
    result = c.validate_output(json.dumps(neutral()), packet, resolution)
    assert result['answer_context_status'] == 'discussion'
    assert result['answer_segments'] == [{'kind': 'connective', 'text': 'Ready. What would you like to try?'}]
    assert 'discussion' in request.json_schema['properties']['answer_context_status']['enum']
    historical = deepcopy(packet)
    historical.pop('response_contract')
    old = neutral()
    old['answer_context_status'] = 'insufficient_evidence'
    with pytest.raises(ValueError, match='explicit qualification'):
        normalize(json.dumps(old), historical)


def test_new_enum_does_not_admit_a_foreign_draft_reference():
    _, packet, resolution = prepared()
    body = neutral()
    body['answer_segments'] = [{'kind': 'draft_reference_claim', 'text': 'Some claim.',
                               'draft_record_id': '20000000-0000-4000-8000-000000000001'}]
    with pytest.raises(Exception):
        c.validate_output(json.dumps(body), packet, resolution)


def test_new_enum_does_not_launder_grounded_content_as_neutral():
    _, packet, resolution = prepared('current_fact')
    body = neutral()
    body['answer_segments'] = [{'kind': 'draft_reference_claim', 'text': 'Ari owns the forge.', 'draft_record_id': p.DRAFT_ID}]
    result = c.validate_output(json.dumps(body), packet, resolution)
    assert result['answer_context_status'] == 'authored_grounded'


def test_tampered_resolution_is_rejected_before_writer_request():
    _, packet, resolution = prepared()
    forged = deepcopy(resolution)
    forged['capabilities']['operations'] = ['answer_from_sources']
    packet['response_contract'] = forged
    with pytest.raises(ValueError, match='closed captured contract'):
        c.validate_output(json.dumps(neutral()), packet, forged)


def test_questions_and_plans_require_the_exact_resolved_typed_object():
    _, packet, resolution = prepared('questions')
    with pytest.raises(ValueError, match='was not produced'):
        c.validate_output(json.dumps(neutral()), packet, resolution)
    body = neutral('Let’s choose the focus.')
    body['collaboration'] = {'kind': 'questions', 'questions': [{'text': 'Landing or market?'}]}
    assert c.validate_output(json.dumps(body), packet, resolution)['collaboration']['kind'] == 'questions'
    body['collaboration'] = {'kind': 'plan', 'steps': [{'text': 'Start writing.', 'kind': 'prepare_insertion'}]}
    with pytest.raises(ValueError, match='differs from resolved'):
        c.validate_output(json.dumps(body), packet, resolution)


def test_review_neutral_ack_does_not_bypass_exact_quote_validation():
    _, packet, resolution = prepared('connected')
    body = neutral('Prepared the review.')
    body['collaboration'] = {'kind': 'connected_page', 'title': "Jo's Ropes", 'read_id': p.READ_ID,
        'quote': 'Invented support.', 'person_label': 'Jo', 'relationships': ['owns', 'operates'], 'instructions': ''}
    with pytest.raises(ValueError, match='exact occurrence'):
        c.validate_output(json.dumps(body), packet, resolution)
    body['collaboration']['quote'] = "Jo | Jo's Ropes | Owns and operates the rope shop. Worked at Ari's forge for one summer."
    assert c.validate_output(json.dumps(body), packet, resolution)['collaboration']['kind'] == 'connected_page'


def test_synthetic_revision_has_a_selection_and_no_expected_labels_in_writer_input():
    row = case('revision')
    resolution = c.resolve('write_current_page', p.capabilities(row))
    request = p.writing_request(row, resolution)
    packet = json.loads(request.user_prompt)
    assert packet['source_basis']['selection']['text'] == p.DRAFT.splitlines()[1]
    assert 'expected_work' not in packet and 'expected_operation' not in packet


def test_failure_usage_is_retained_and_unknown_usage_is_not_zero():
    rows = [{'cohort': 'synthetic', 'variant': 'semantic', 'expected_operation': 'answer_from_sources',
             'expected_work': ['discuss'], 'error': {'type': 'Failure'}, 'calls': [
                 {'response': None, 'failure_observation': {'input_tokens': 11, 'output_tokens': 3}},
                 {'response': None, 'failure_observation': None}]}]
    group = p.summarize(rows)[0]
    assert group['provider_call_attempts'] == 2 and group['calls_with_unknown_usage'] == 1
    assert group['known_input_tokens'] == 11 and group['known_output_tokens'] == 3
