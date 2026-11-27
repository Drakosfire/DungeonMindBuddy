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
    NativePlanOpeningInputV1, NativePlanOpeningInputV2, prepare_opening_decision, decode_opening_decision,
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


def test_v2_evidence_relevance_changes_only_its_opening_guidance_and_preserves_historical_codec():
    from tests.application_state.test_plan_contextual_targets import family_catalog, heading, prose

    capture, catalog = family_catalog([heading('Workshop'), prose('Clay is fired.')])
    fields = opening_input().model_dump(exclude={'schema_'})
    fields.update(original_capture=capture, placement_catalog=catalog,
                  target_available=True, target_capture_sha256=capture.sha256)
    fields['candidates'][0]['kind'] += '; saved authored text'
    historical = NativePlanOpeningInputV2.model_validate(fields)
    encoded = historical.model_dump_json(by_alias=True)
    assert 'evidence_relevance_version' not in encoded
    assert NativePlanOpeningInputV2.model_validate_json(encoded).digest == historical.digest

    marked = historical.model_copy(update={'evidence_relevance_version': 'v1'})
    assert marked.digest != historical.digest
    before = prepare_opening_decision(historical)
    after = prepare_opening_decision(marked)
    assert 'evidence_relevance_version' not in after.model_dump_json()
    assert after.questions[0].question.startswith(before.questions[0].question)
    assert 'belongs in discussion' in after.questions[0].question
    assert after.questions[0].options == before.questions[0].options
    assert after.questions[1:] == before.questions[1:]
    assert after.state['candidates'][0]['kind'].startswith(before.state['candidates'][0]['kind'])
    assert 'A topic match alone' in after.state['candidates'][0]['kind']
    assert after.state['candidates'][1:] == before.state['candidates'][1:]
    assert {k: v for k, v in after.state.items() if k != 'candidates'} == {
        k: v for k, v in before.state.items() if k != 'candidates'
    }


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


def request_context(*, related=False, source_discovery_mode=None):
    context, record = component('plan')
    from application_state.agent_conversation.build_related_pages import PagePointer
    pages = (PagePointer(world_id=record.policy.action.intent.world_id, document_id=uuid4(),
        registry_revision=1, title='Saved notes', visibility='internal'),) if related else ()
    action = NativePlanActionV2.model_validate(record.policy.action.model_dump(by_alias=True) | dict(
        action_version='plan_saved_authored_pages_v2', related_page_catalog=pages,
        **({'source_discovery_mode': source_discovery_mode} if source_discovery_mode else {})))
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


def test_captured_plan_opening_ui_wire_uses_the_current_backend_response_model():
    from pathlib import Path
    from apps.live_control_server.models.agent_turn import AgentSurfaceNativeContextResponseV1
    wire = json.loads((Path(__file__).parents[1] / 'apps/live-control-ui/src/test/surface-native-plan-opening-http.json').read_text())
    context = AgentSurfaceNativeContextResponseV1.model_validate_json(json.dumps(wire['context']))
    assert type(context.receipt.assembled_input) is NativePlanRequestAdmissionV1
    assert context.receipt.work_context.surface_id == 'plan'
    assert context.completion.native_assertion_citations
    assert wire['source']['citation'] == context.completion.native_assertion_citations[0].model_dump(mode='json',by_alias=True)
    assert wire['source']['world_id'] == context.receipt.work_context.plan_basis.world_id


def test_controller_selected_source_mode_preserves_legacy_hash_and_real_opening_gate():
    from application_state.agent_conversation.native_corpus import (
        controller_selected_source_discovery, request_source_discovery_enabled,
    )
    from application_state.agent_conversation.native_plan_opening import validate_opening_prefix

    legacy_context, legacy = request_context()
    legacy_action = legacy.policy.action
    legacy_wire = legacy_action.model_dump(mode='json', by_alias=True)
    assert 'source_discovery_mode' not in legacy_wire
    assert t.canonical_sha256(legacy_action) == t.canonical_sha256(legacy_wire)
    assert request_source_discovery_enabled(legacy_context, legacy)
    with pytest.raises(ValueError, match='settled request-owned discovery'):
        validate_opening_prefix(legacy_context, (), execution=legacy)

    context, record = request_context(source_discovery_mode='controller_selection_v1')
    assert validate_context_binding(context, record) == record
    assert controller_selected_source_discovery(record)
    assert not request_source_discovery_enabled(context, record)
    assert record.policy.action.model_dump(mode='json')['source_discovery_mode'] == 'controller_selection_v1'
    assert validate_opening_prefix(context, (), execution=record) is None
    old_auth = controller('plan', record.policy)
    opening = NativePlanOpeningAuthorizedV1.model_validate(old_auth.model_dump(by_alias=True) | {
        'kind': 'native_plan_opening_authorized_v1'})
    admitted = execution(context.context_receipt_sha256, record.policy, [opening])
    assert validate_context_binding(context, admitted) == admitted
    forged = request_grant(context, record)
    with pytest.raises(ValueError, match='Request discovery'):
        execution(context.context_receipt_sha256, record.policy, [forged])
    with pytest.raises(ValueError, match='automatic request grant'):
        validate_opening_prefix(context, (forged,), execution=record)
    with pytest.raises(ValueError):
        NativePlanActionV2.model_validate(legacy_wire | {'source_discovery_mode': 'unknown'})


def test_controller_selected_mode_cannot_be_bound_to_legacy_sdk_admission():
    context, record = component('plan')
    wire = record.policy.action.model_dump(mode='json', by_alias=True)
    action = NativePlanActionV2.model_validate(wire | {
        'action_version': 'plan_saved_authored_pages_v2', 'related_page_catalog': [],
        'source_discovery_mode': 'controller_selection_v1',
    })
    changed = execution(context.context_receipt_sha256, record.policy.model_copy(update={'action': action}))
    with pytest.raises(ValueError, match='requires current Plan request admission'):
        validate_context_binding(context, changed)


def test_controller_selected_navigation_offers_search_without_automatic_acquisition(monkeypatch):
    from types import SimpleNamespace
    from apps.live_control_server.services.corpus_source_navigation import NativeBodyNavigation
    from apps.live_control_server.integrations.dungeonmind import native_corpus_source
    from application_state.agent_conversation.native_corpus import native_corpus_search_handle

    def navigation(mode):
        context, record = request_context(source_discovery_mode=mode)
        turn = SimpleNamespace(graph_context_receipt=context, graph_context_execution=record,
                               user_text=record.policy.action.intent.message)
        adapter = SimpleNamespace(fence=SimpleNamespace(turn=turn), native_corpus_context=None)
        source = object.__new__(NativeBodyNavigation)
        source.adapter = adapter
        source._source_display = {}
        source._direct_sources = {}
        monkeypatch.setattr(source, '_source_choices', lambda: {})
        monkeypatch.setattr(source, '_acquired_extents', lambda: ())
        monkeypatch.setattr(source, '_keyword_offers', lambda: ())
        monkeypatch.setattr(source, '_scoped_offers', lambda rows, search: tuple(rows))
        monkeypatch.setattr(source, '_commit', lambda *_a, **_kw: pytest.fail('Unexpected authorization or read'))
        return source, turn

    monkeypatch.setattr(native_corpus_source, 'capture_native_sources',
                        lambda **_kw: pytest.fail('Unexpected source acquisition'))
    current, turn = navigation('controller_selection_v1')
    current.discover_initial()
    offered = current.offered()
    assert [item.handle for item in offered] == [native_corpus_search_handle(
        sha256(turn.user_text.encode()).hexdigest())]
    from application_state.agent_conversation.native_corpus import NativeBodySearchAuthorizedV1
    execution = turn.graph_context_execution
    interrupted = NativeBodySearchAuthorizedV1(event_id=uuid4(), sequence=0,
        provider_attempt_id=uuid4(), context_receipt_sha256=execution.context_receipt_sha256,
        execution_policy_sha256=execution.execution_policy_sha256,
        authority=turn.graph_context_receipt.source_authority,
        query_sha256=sha256(turn.user_text.encode()).hexdigest())
    turn.graph_context_execution = execution.model_copy(update={'events': [interrupted]})
    current.discover_initial()  # Never repeats an interrupted explicit search.
    with pytest.raises(ValueError, match='unresolved durable grant'):
        current.offered()
    legacy, _ = navigation(None)
    with pytest.raises(ValueError, match='requires initial source discovery'):
        legacy.offered()


def test_controller_selected_search_still_requires_exact_acknowledged_handle(monkeypatch):
    from types import SimpleNamespace
    from application_state.agent_conversation import native_reads, build_pending_native
    from application_state.agent_conversation.native_corpus import (
        initial_source_discovery_enabled, initial_source_discovery_required, native_corpus_search_handle,
    )
    from application_state.agent_conversation.native_execution import NativePlanOpeningSelectedV2

    context, record = request_context(source_discovery_mode='controller_selection_v1')
    choice = NativePlanOpeningSelectedV2.model_construct(
        event_id=uuid4(), sequence=0, requested_work='discuss', operation='finish_retrieval')
    current = record.model_copy(update={'events': [choice]})
    assert initial_source_discovery_enabled(current)
    assert not initial_source_discovery_required(current)
    turn = SimpleNamespace(user_text=record.policy.action.intent.message)
    monkeypatch.setattr(native_reads, '_owner', lambda *_a, **_kw: (context, current))
    monkeypatch.setattr(build_pending_native, 'read_source_authority',
                        lambda *_args: context.source_authority)
    selected = SimpleNamespace(operation='select_candidates',
        selected_handles=(native_corpus_search_handle(sha256(turn.user_text.encode()).hexdigest()),),
        controller_attempt_id=uuid4())
    monkeypatch.setattr(build_pending_native, 'read_selection', lambda *_args: selected)
    event = native_reads.authorize_body_search_locked(turn, event_id=uuid4())
    assert event.provider_attempt_id == selected.controller_attempt_id
    assert event.query_sha256 == sha256(turn.user_text.encode()).hexdigest()
    assert event.authority == context.source_authority
    for bad in (SimpleNamespace(operation='finish_retrieval', selected_handles=selected.selected_handles),
                SimpleNamespace(operation='select_candidates', selected_handles=('foreign',))):
        monkeypatch.setattr(build_pending_native, 'read_selection', lambda *_args, bad=bad: bad)
        with pytest.raises(ValueError, match='not selected'):
            native_reads.authorize_body_search_locked(turn, event_id=uuid4())

    legacy_action = record.policy.action.model_copy(update={'source_discovery_mode': None})
    legacy = current.model_copy(update={'policy': record.policy.model_copy(update={'action': legacy_action})})
    assert initial_source_discovery_enabled(legacy) and initial_source_discovery_required(legacy)
    monkeypatch.setattr(native_reads, '_owner', lambda *_a, **_kw: (context, legacy))
    with pytest.raises(ValueError, match='initial work'):
        native_reads.authorize_body_search_locked(turn, event_id=uuid4())


def test_controller_selected_mode_rejects_legacy_automatic_work_grant():
    from application_state.agent_conversation.native_corpus import (
        NativeInitialSourceSearchAuthorizedV1, validate_initial_source_search,
    )
    from application_state.agent_conversation.native_execution import NativePlanRequestedWorkSelectedV3

    context, record = request_context()
    work = NativePlanRequestedWorkSelectedV3.model_construct(
        event_id=uuid4(), sequence=0, requested_work='discuss')
    legacy = record.model_copy(update={'events': [work]})
    grant = NativeInitialSourceSearchAuthorizedV1(event_id=uuid4(), sequence=1,
        work_selection_event_id=work.event_id, context_receipt_sha256=legacy.context_receipt_sha256,
        execution_policy_sha256=legacy.execution_policy_sha256, authority=context.source_authority,
        query_sha256=sha256(record.policy.action.intent.message.encode()).hexdigest())
    assert validate_initial_source_search(legacy, grant) is None
    action = record.policy.action.model_copy(update={'source_discovery_mode': 'controller_selection_v1'})
    changed = legacy.model_copy(update={'policy': record.policy.model_copy(update={'action': action})})
    with pytest.raises(ValueError, match='original readonly work'):
        validate_initial_source_search(changed, grant)


def _guidance_wire(parent):
    from application_state.agent_conversation.jev_retrieval_contract import MODEL
    decision = prepare_opening_decision(parent)
    return {"model": MODEL, "state": decision.state, "questions": {
        q.name: {"type": "choice", "instructions": q.question,
                 "criteria": {option: (q.option_descriptions or {}).get(option) for option in q.options}}
        for q in decision.questions}}


def test_work_guidance_reader_preserves_historical_wire_and_marks_only_new_choice_descriptions():
    from uuid import UUID
    from application_state.agent_conversation.plan_authoring import validate_requested_work_wire
    parent = opening_input().model_copy(update={"request_id": UUID(int=1), "parent_attempt_id": UUID(int=2)})
    original = parent.model_dump(mode="json", by_alias=True)
    assert "work_choice_guidance_version" not in original
    assert NativePlanOpeningInputV1.model_validate(original) == parent
    old = _guidance_wire(parent)
    historic = {k: v for k, v in old.items() if k != "model"}
    assert sha256(json.dumps(historic, sort_keys=True, separators=(",", ":")).encode()).hexdigest() == "88e91668123b365d58010da5e75d83b3457c5c1062b661adf3fc517e70a5c487"
    marked = NativePlanOpeningInputV1.model_validate(original | {"work_choice_guidance_version": "v1"})
    assert marked.digest != parent.digest
    new = _guidance_wire(marked)
    assert old["state"] == new["state"]
    assert "work_choice_guidance_version" not in json.dumps(new)
    assert {k: v for k, v in old["questions"].items() if k != "requested_work"} == {k: v for k, v in new["questions"].items() if k != "requested_work"}
    old_q, new_q = old["questions"]["requested_work"], new["questions"]["requested_work"]
    assert old_q["instructions"] == new_q["instructions"]
    assert old_q["criteria"].keys() == new_q["criteria"].keys()
    assert all(value is None for value in old_q["criteria"].values())
    assert all(isinstance(value, str) and value for value in new_q["criteria"].values())
    for owner, wire in ((parent, old), (marked, new)):
        validate_requested_work_wire(owner, json.dumps(wire).encode())
    for owner, wire in ((parent, new), (marked, old)):
        with pytest.raises(ValueError, match="wire differs"):
            validate_requested_work_wire(owner, json.dumps(wire).encode())


def test_work_guidance_reader_rejects_unknown_and_other_opening_versions():
    from pydantic import ValidationError
    parent = opening_input()
    original = parent.model_dump(mode="json", by_alias=True)
    with pytest.raises(ValidationError):
        NativePlanOpeningInputV1.model_validate(original | {"work_choice_guidance_version": "v2"})
    newer = original | {"schema": "dmb_native_plan_opening_input_v2"}
    unmarked = NativePlanOpeningInputV2.model_validate(newer)
    with pytest.raises(ValidationError, match="only to the V1 opening"):
        NativePlanOpeningInputV2.model_validate(newer | {"work_choice_guidance_version": "v1"})
    with pytest.raises(ValueError, match="Unsupported work-choice guidance version"):
        prepare_opening_decision(unmarked.model_copy(update={"work_choice_guidance_version": "v1"}))


@pytest.mark.parametrize('operation', ['discuss', 'write_current_page'])
def test_work_guidance_reader_keeps_explicit_operation_choice_set(operation):
    parent = opening_input().model_copy(update={'plan_requested_operation': operation})
    marked = parent.model_copy(update={'work_choice_guidance_version': 'v1'})
    old = prepare_opening_decision(parent).questions[0]
    new = prepare_opening_decision(marked).questions[0]
    assert new.options == old.options
    assert set(new.option_descriptions) == set(new.options)


def test_work_guidance_reader_validates_exact_prepared_dispatch():
    from uuid import uuid4
    from generationengine.decision_dispatch import PreparedDecisionDispatch
    from application_state.agent_conversation.jev_retrieval_contract import MODEL, PROVIDER
    from application_state.agent_conversation.plan_authoring import validate_prepared_requested_work

    parent = opening_input().model_copy(update={'work_choice_guidance_version': 'v1'})
    body = json.dumps(_guidance_wire(parent), separators=(',', ':')).encode()
    prepared = PreparedDecisionDispatch(attempt_id=str(uuid4()), provider=PROVIDER,
        provider_transport='vercel_ai_gateway', model=MODEL, method='POST',
        url='https://ai-gateway.vercel.sh/typesafe/v1/systemone', body=body,
        body_sha256=sha256(body).hexdigest(), body_size=len(body))
    validate_prepared_requested_work(parent, prepared)
    with pytest.raises(ValueError, match='wire differs'):
        validate_prepared_requested_work(parent.model_copy(update={'work_choice_guidance_version': None}), prepared)
