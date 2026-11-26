"""Reader-first current-page scope; this slice never emits the new choice."""
from types import SimpleNamespace
from hashlib import sha256
import asyncio
import json

import pytest

from application_state.agent_conversation import build_intentional_response as semantic
from application_state.agent_conversation.build_source_free import pending_work_requests_evidence
from application_state.agent_conversation.native_build_work_view import source_backed_discussion
from tests.test_build_source_free_routing import pending_execution, pending_execution_pair, pending_work_prefix


def _request(options, guidance):
    return {'questions': {'source_need': {'type': 'choice', 'instructions': guidance,
                                         'criteria': dict.fromkeys(options)}}}


def _response(options, selected):
    return {'answers': {'source_need': {'selected': selected,
        'probabilities': {option: float(option == selected) for option in options}}}}


def test_reader_recognizes_frozen_old_and_future_choices_without_emitting_future():
    old = semantic.SOURCE_NEED_OPTIONS
    future = semantic.FUTURE_CURRENT_PAGE_SOURCE_NEED_OPTIONS
    for choice in old:
        assert semantic.source_need(_request(old, semantic.SOURCE_NEED_GUIDANCE),
                                    _response(old, choice)) == choice
        assert semantic.source_need(_request(future, semantic.FUTURE_CURRENT_PAGE_SOURCE_NEED_GUIDANCE),
                                    _response(future, choice)) == choice
    assert semantic.source_need(_request(future, semantic.FUTURE_CURRENT_PAGE_SOURCE_NEED_GUIDANCE),
                                _response(future, 'current_saved_page')) == 'current_saved_page'
    assert 'current_saved_page' not in semantic.SOURCE_NEED_OPTIONS
    assert semantic.SOURCE_NEED_GUIDANCE != semantic.FUTURE_CURRENT_PAGE_SOURCE_NEED_GUIDANCE


def test_reader_rejects_changed_question_and_invented_or_tied_vote():
    old = semantic.SOURCE_NEED_OPTIONS
    future = semantic.FUTURE_CURRENT_PAGE_SOURCE_NEED_OPTIONS
    with pytest.raises(ValueError):
        semantic.source_need(_request(future, semantic.FUTURE_CURRENT_PAGE_SOURCE_NEED_GUIDANCE + ' altered'),
                             _response(future, 'current_saved_page'))
    with pytest.raises(ValueError):
        semantic.source_need(_request(old, semantic.SOURCE_NEED_GUIDANCE),
                             _response(future, 'current_saved_page'))
    tied = _response(future, 'current_saved_page')
    tied['answers']['source_need']['probabilities']['source_lookup'] = 1.0
    with pytest.raises(ValueError):
        semantic.source_need(_request(future, semantic.FUTURE_CURRENT_PAGE_SOURCE_NEED_GUIDANCE), tied)


def test_future_scope_preserves_evidence_routing_and_unavailable_action_barrier():
    _, policy = pending_execution_pair()
    work = pending_work_prefix(policy, scope='source_lookup')[-1]
    for label in ('discuss', 'other_creation'):
        resolution = semantic.resolution_for(policy, label, source_scope='current_saved_page')
        row = type(work).model_validate(work.model_dump(mode='python') | {
            'requested_work': label, 'intent_family': resolution['intent_family'],
            'operation': resolution['operation'], 'resolution': resolution})
        assert pending_work_requests_evidence(row, policy)
        if label == 'other_creation':
            assert resolution['barrier'] == 'requested_executor_not_offered'
            assert not pending_work_requests_evidence(row.model_copy(update={
                'resolution': resolution | {'barrier': 'invented'}}), policy)


def test_pending_execution_roundtrips_future_scope_but_legacy_policy_rejects_it():
    receipt, policy = pending_execution_pair()
    events = pending_work_prefix(policy, scope='current_saved_page')
    stored = pending_execution(receipt, policy, events)
    restored = type(stored).model_validate_json(stored.model_dump_json(by_alias=True))
    assert restored.events[-1].resolution['source_scope'] == 'current_saved_page'
    from tests.test_surface_native_execution import component
    _, legacy = component('build')
    with pytest.raises(ValueError, match='requires pending Build'):
        semantic.resolution_for(legacy.policy, 'discuss', source_scope='current_saved_page')


def test_pending_selection_validates_the_actual_future_request_and_vote():
    from tests.test_surface_native_build_decision import sdk_case
    _, original, event, proof, trace, work = sdk_case()
    _, policy = pending_execution_pair()
    request = json.loads(proof['request_json'])
    response = json.loads(proof['response_json'])
    decision = request['state']['decision']
    decision['state']['user_question'] = policy.action.intent.message
    decision['state']['interaction']['allowed_operations'] = list(policy.action.capabilities.operations)
    decision['state']['interaction']['capability_sha256'] = policy.action.intent.build_write_capability_sha256
    decision['request_id'] = 'select:' + semantic.digest(decision['state'])
    options = semantic.FUTURE_CURRENT_PAGE_SOURCE_NEED_OPTIONS
    request['questions']['source_need'] = _request(options, semantic.FUTURE_CURRENT_PAGE_SOURCE_NEED_GUIDANCE)['questions']['source_need']
    response['answers']['source_need'] = {'kind': 'choice', 'confidence': 1.0,
        **_response(options, 'current_saved_page')['answers']['source_need']}
    proof = {'request_json': json.dumps(request), 'response_json': json.dumps(response)}
    request_hash = sha256(proof['request_json'].encode()).hexdigest()
    response_hash = sha256(proof['response_json'].encode()).hexdigest()
    auth = original.events[0].model_copy(update={'envelope_sha256': request_hash})
    prefix = SimpleNamespace(policy=policy, events=[auth, *original.events[1:]])
    event = event.model_copy(update={'controller_envelope_sha256': request_hash,
        'controller_response_sha256': response_hash, 'machine_request_id': decision['request_id'],
        'broker_operation_id': semantic.operation_id_for(work['turn_id'], 1, decision['request_id'], 'discuss'),
        'resolution': semantic.resolution_for(policy, 'discuss', source_scope='current_saved_page')})
    trace['observations'][0]['materials'][0]['text'] = proof['response_json']
    semantic.validate_selection_records(prefix, event, proof, trace,
        user_text=policy.action.intent.message, turn_id=work['turn_id'], attempt=1)
    with pytest.raises(ValueError):
        semantic.validate_selection_records(prefix, event, proof | {'request_json': proof['request_json'] + ' '}, trace,
            user_text=policy.action.intent.message, turn_id=work['turn_id'], attempt=1)


def test_reader_refuses_to_resume_future_scope_before_any_app_or_native_acquisition():
    from apps.live_control_server.services.build_pending_app_pages import acquire_pending_app_pages
    from apps.live_control_server.services.build_pending_source import prepare_pending_native_source
    receipt, policy = pending_execution_pair(with_source=True)
    execution = pending_execution(receipt, policy, pending_work_prefix(policy, scope='current_saved_page'))
    # No discovery, source preparation, access or read owners exist here: a
    # guard after any attempted acquisition would raise a different exception.
    adapter = SimpleNamespace(_broker_receipt=lambda: receipt, _broker_execution=lambda: execution)
    with pytest.raises(ValueError, match='requires its producer'):
        asyncio.run(acquire_pending_app_pages(adapter, object()))
    with pytest.raises(ValueError, match='requires its producer'):
        prepare_pending_native_source(adapter)


def test_source_backed_presentation_requires_actual_supplied_material():
    _, policy = pending_execution_pair()
    work = pending_work_prefix(policy, scope='source_lookup')[-1]
    work = work.model_copy(update={'resolution': semantic.resolution_for(
        policy, 'discuss', source_scope='current_saved_page')})
    execution = SimpleNamespace(policy=policy, events=[work])
    host = {'artifact_under_edit': {'sections': []}}
    assert not source_backed_discussion(host, execution)
    host['related_authored_pages'] = {'pages': [{'text': 'actual supplied material'}]}
    assert source_backed_discussion(host, execution)
