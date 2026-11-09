"""Closed opening semantics and real request-manifest ownership, without IO."""
import json
from hashlib import sha256
from uuid import uuid4

import pytest
from generationengine.types import ChoiceDecisionAnswer

from application_state.agent_conversation import types as t
from application_state.agent_conversation.native_context import NativePlanRequestAdmissionV1, SurfaceNativeContextReceiptV1
from application_state.agent_conversation.native_execution import NativePlanActionV2, validate_context_binding
from application_state.agent_conversation.native_plan_opening import (
    NativePlanOpeningInputV1, prepare_opening_decision, decode_opening_decision,
    request_manifest,
)
from application_state.agent_conversation.native_retrieval import NativePlanOpeningAuthorizedV1
from application_state.agent_conversation.jev_retrieval_contract import RetrievalCandidate
from tests.test_jev_retrieval_contract import request, result
from tests.test_surface_native_context import seal
from tests.test_surface_native_execution import component, execution, controller


def opening_input():
    values = request().model_dump(exclude={'schema_', 'revision'})
    return NativePlanOpeningInputV1(**(values | dict(page_title='Current Plan',
        target_available=False, target_capture_sha256=None, original_capture=None,
        placement_catalog=None, authored_references=None, source_authority_status='available',
        source_revision='HOST-SOURCE-PIN', graph_revision='HOST-GRAPH-PIN',
        candidates=(RetrievalCandidate(handle='saved-authored-page:host-id',
            label='Saved notes', kind='Saved authored Worldbuilding page'),
            RetrievalCandidate(handle='native-body:host-id', label='Matching source section', kind='Exact source section')))))


def answers(work, *, page='include', source='exclude', fallback='discover_more', plan='finish_if_selected_reads_succeed'):
    return result(answers={k: ChoiceDecisionAnswer(selected=v) for k, v in dict(
        requested_work=work, operation=fallback, post_read_plan=plan,
        candidate_0=page, candidate_1=source).items()})


def test_combined_wire_has_one_request_and_conditional_choices_without_host_pins():
    parent = opening_input()
    decision = prepare_opening_decision(parent)
    assert [q.name for q in decision.questions] == [
        'requested_work', 'operation', 'post_read_plan', 'candidate_0', 'candidate_1']
    assert decision.state['user_request'] == parent.question
    assert 'question' not in decision.state
    assert 'all applicable candidate relevance votes exclude' in decision.questions[1].question
    raw = json.dumps(decision.state)
    for private in (str(parent.request_id), str(parent.parent_attempt_id), parent.scope_sha256,
            parent.source_revision, parent.graph_revision, *(c.handle for c in parent.candidates)):
        assert private not in raw
    assert NativePlanOpeningInputV1.model_validate_json(parent.model_dump_json(by_alias=True)) == parent


@pytest.mark.parametrize('work,expected_operation,expected_handles', [
    ('discuss', 'select_candidates', ('saved-authored-page:host-id',)),
    ('clarify', 'discover_more', ()),
    ('different_destination', None, ()),
    ('write_unavailable', None, ()),
    ('review_connected_page', None, ()),
])
def test_work_controls_actual_vote_applicability_without_fabricated_finish(work, expected_operation, expected_handles):
    parent = opening_input()
    selected, batch = decode_opening_decision(parent, answers(work))
    assert selected == work
    if expected_operation is None:
        assert batch is None
    else:
        assert batch.operation == expected_operation
        assert batch.selected_handles == expected_handles


def test_clarify_preserves_applicable_source_and_ignores_only_declared_inactive_page_vote():
    _, batch = decode_opening_decision(opening_input(), answers('clarify', source='include'))
    assert batch.selected_handles == ('native-body:host-id',)
    assert batch.post_read_plan == 'finish_if_selected_reads_succeed'


@pytest.mark.parametrize('change', ['missing', 'extra', 'unknown_plan', 'unknown_candidate', 'wrong_provider'])
def test_combined_result_is_one_closed_real_result_even_when_work_is_inactive(change):
    actual = answers('different_destination')
    if change == 'missing':
        actual.answers.pop('post_read_plan')
    elif change == 'extra':
        actual.answers['other'] = ChoiceDecisionAnswer(selected='include')
    elif change == 'unknown_plan':
        actual.answers['post_read_plan'] = ChoiceDecisionAnswer(selected='invented')
    elif change == 'unknown_candidate':
        actual.answers['candidate_0'] = ChoiceDecisionAnswer(selected='invented')
    else:
        actual = actual.model_copy(update={'observation': actual.observation.model_copy(update={'provider': 'other'})})
    with pytest.raises(ValueError):
        decode_opening_decision(opening_input(), actual)


def request_context(*, related=False):
    context, record = component('plan')
    from application_state.agent_conversation.build_related_pages import PagePointer
    pages = (PagePointer(world_id=record.policy.action.intent.world_id, document_id=uuid4(),
        registry_revision=1, title='Saved notes', visibility='internal'),) if related else ()
    action = NativePlanActionV2.model_validate(record.policy.action.model_dump(by_alias=True) | dict(
        action_version='plan_saved_authored_pages_v2', related_page_catalog=pages))
    policy = record.policy.model_copy(update={'action': action})
    admission = NativePlanRequestAdmissionV1(manifest_sha256='0' * 64,
        submitted_intent_sha256=t.canonical_sha256(action.intent), dialogue_sha256=t.canonical_sha256([]),
        tokenizer_name='synthetic', tokenizer_version='v1',
        context_window_limit=128000, output_token_reserve=200)
    manifest = request_manifest(action=action, work_context=context.work_context,
        source_authority_sha256=policy.source_authority_sha256, native_query_sha256=policy.native_query_sha256,
        provenance_sha256=context.provenance_sha256, provider_roles=policy.provider_roles,
        provider_input_accounting=policy.provider_input_accounting, admission=admission)
    admission = admission.model_copy(update={'manifest_sha256': t.canonical_sha256(manifest)})
    wire = context.model_dump(mode='json', by_alias=True)
    wire['assembled_input'] = admission.model_dump(mode='json')
    context = SurfaceNativeContextReceiptV1.model_validate(seal(wire))
    return context, execution(context.context_receipt_sha256, policy)


def test_request_manifest_admits_empty_execution_without_inventing_provider_measurements():
    context, record = request_context()
    assert validate_context_binding(context, record) == record
    fields = context.assembled_input.model_dump()
    assert not {'assembled_input_sha256', 'provider_envelope_input_tokens', 'provider_model_name'} & fields.keys()
    assert record.events == []


def test_request_manifest_binds_typed_saved_page_capabilities_without_raw_model_exposure():
    context, record = request_context(related=True)
    assert validate_context_binding(context, record) == record
    page = record.policy.action.related_page_catalog[0]
    changed_action = record.policy.action.model_copy(update={'related_page_catalog': (
        page.model_copy(update={'title': 'Changed metadata'}),)})
    changed = execution(context.context_receipt_sha256, record.policy.model_copy(update={'action': changed_action}))
    with pytest.raises(ValueError, match='manifest'):
        validate_context_binding(context, changed)


@pytest.mark.parametrize('field,value', [('dialogue_sha256', 'f' * 64),
    ('submitted_intent_sha256', 'f' * 64), ('output_token_reserve', 201), ('tokenizer_name', 'other')])
def test_resealed_root_cannot_replace_request_manifest_owners(field, value):
    context, record = request_context()
    wire = context.model_dump(mode='json', by_alias=True)
    wire['assembled_input'][field] = value
    changed = SurfaceNativeContextReceiptV1.model_validate(seal(wire))
    changed_record = execution(changed.context_receipt_sha256, record.policy)
    with pytest.raises(ValueError, match='request admission'):
        validate_context_binding(changed, changed_record)


def test_first_provider_budget_owner_requires_real_opening_kind_not_manifest_envelope_equality():
    context, record = request_context()
    old = controller('plan', record.policy)
    actual = NativePlanOpeningAuthorizedV1.model_validate(old.model_dump(by_alias=True) | dict(
        kind='native_plan_opening_authorized_v1', event_id=uuid4()))
    # This is the budget owner alone, not SDK authorization or a stored attempt.
    t.validate_provider_envelope_accounting(context.assembled_input, record, actual)
    for bad in (old, actual.model_copy(update={'input_tokens': 128001}),
            actual.model_copy(update={'input_estimator': 'other'})):
        with pytest.raises(ValueError):
            t.validate_provider_envelope_accounting(context.assembled_input, record, bad)


def request_grant(context, record, **changes):
    return t.NativePlanRequestSearchAuthorizedV1(**(dict(event_id=uuid4(), sequence=0,
        request_manifest_sha256=context.assembled_input.manifest_sha256,
        context_receipt_sha256=context.context_receipt_sha256,
        execution_policy_sha256=record.execution_policy_sha256, authority=context.source_authority,
        query_sha256=sha256(record.policy.action.intent.message.encode()).hexdigest()) | changes))


def test_actual_request_grant_can_precede_first_provider_but_cannot_substitute_for_observation():
    context, record = request_context()
    grant = request_grant(context, record)
    granted = execution(context.context_receipt_sha256, record.policy, [grant])
    assert validate_context_binding(context, granted) == granted
    old = controller('plan', record.policy, sequence=1)
    opening = NativePlanOpeningAuthorizedV1.model_validate(old.model_dump(by_alias=True) | dict(
        kind='native_plan_opening_authorized_v1'))
    with pytest.raises(ValueError, match='unresolved|settle'):
        execution(context.context_receipt_sha256, record.policy, [grant, opening])


@pytest.mark.parametrize('change', ['manifest', 'question', 'duplicate'])
def test_request_grant_cannot_change_manifest_query_or_repeat(change):
    context, record = request_context()
    grant = request_grant(context, record)
    changes = {'request_manifest_sha256': 'f' * 64} if change == 'manifest' else {'query_sha256': 'f' * 64}
    with pytest.raises(ValueError):
        events = [grant, request_grant(context, record, sequence=1)] if change == 'duplicate' else [grant.model_copy(update=changes)]
        validate_context_binding(context, execution(context.context_receipt_sha256, record.policy, events))
