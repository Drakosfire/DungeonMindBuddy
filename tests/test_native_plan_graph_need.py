"""Focused reader checks for the unactivated Plan Graph-need codec."""
import json
from hashlib import sha256

import pytest
from generationengine.types import ChoiceDecisionAnswer
from application_state.agent_conversation.jev_retrieval_contract import RetrievalDialogue
from application_state.agent_conversation.native_plan_graph_need import (
    NativePlanGraphNeedInputV1, decode_decision, prepare_decision, validate_input_binding, validate_wire,
)
from application_state.agent_conversation.native_plan_opening import opening_dialogue_sha256
from tests.test_jev_retrieval_contract import result
from tests.test_native_assertion_source_locators import core_read


def parent():
    return NativePlanGraphNeedInputV1(pending_query_sha256='a'*64, admission_sha256='b'*64,
        question='What did we decide?', dialogue=(RetrievalDialogue(role='user', content='Élan\nblue bead'),),
        current_work='# Crépuscule\n\nA quiet scene.\n')


def pins(value):
    return dict(pending_sha256='a'*64, admission_sha256='b'*64, question=value.question,
        dialogue_sha256=opening_dialogue_sha256(value.dialogue),
        work_sha256=sha256(value.current_work.encode('utf-8')).hexdigest())


def wire(value):
    request = prepare_decision(value)
    body = {'state': request.state, 'model': request.model, 'questions': {
        item.name: {'type': 'choice', 'instructions': item.question,
            'criteria': {option: item.option_descriptions[option] for option in item.options}}
        for item in request.questions}}
    return json.dumps(body, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode('utf-8')


def test_exact_wire_excludes_host_pins_and_preserves_unicode():
    value = parent()
    raw = wire(value)
    validate_input_binding(value, **pins(value))
    validate_wire(value, raw)
    assert b'a'*64 not in raw and b'b'*64 not in raw
    assert 'Crépuscule'.encode() in raw and 'Élan'.encode() in raw
    with pytest.raises(ValueError):
        validate_wire(value, raw + b' ')
    with pytest.raises(ValueError):
        validate_wire(value, raw.replace(b'blue bead', b'red bead'))


@pytest.mark.parametrize('field,bad', [
    ('pending_sha256', 'c'*64), ('admission_sha256', 'c'*64),
    ('question', 'Changed question'), ('dialogue_sha256', 'c'*64), ('work_sha256', 'c'*64),
])
def test_context_binding_rejects_substitution(field, bad):
    value = parent(); fields = pins(value); fields[field] = bad
    with pytest.raises(ValueError, match='committed request'):
        validate_input_binding(value, **fields)


@pytest.mark.parametrize('choice', ['require_graph', 'no_graph', 'uncertain'])
def test_valid_choice_without_optional_distribution(choice):
    answer = ChoiceDecisionAnswer(selected=choice)
    assert decode_decision(parent(), result(answers={'graph_need': answer})) == choice


@pytest.mark.parametrize('distribution', [
    {'no_graph': .5, 'require_graph': .5}, {'no_graph': .1, 'require_graph': .9},
    {'require_graph': .9}, {'no_graph': float('nan')}, {'no_graph': 1.1}, {'no_graph': .9, 'other': .1},
])
def test_tied_or_invalid_probabilities_cannot_produce_decision(distribution):
    answer = ChoiceDecisionAnswer(selected='no_graph', probabilities=distribution)
    with pytest.raises(ValueError):
        decode_decision(parent(), result(answers={'graph_need': answer}))


def test_actual_sdk_prepared_wire_matches_reader_without_network():
    import asyncio
    import httpx2
    from apps.live_control_server.services.plan_jev_dispatch import decision_client
    value = parent(); seen = []
    async def authorize(prepared):
        validate_wire(value, prepared.body)
        seen.append(prepared.body)
        return True
    async def record(_event):
        return True
    class Wire(httpx2.AsyncBaseTransport):
        async def handle_async_request(self, request):
            assert request.content == seen[0]
            return httpx2.Response(200, request=request, json={'model': 'typesafe-ai/jev-1.14.0',
                'answers': {'graph_need': {'type': 'choice', 'choice': 'no_graph', 'confidence': 1,
                    'probabilities': {'require_graph': 0, 'no_graph': 1, 'uncertain': 0}}},
                'usage': {'input_tokens': 10, 'output_tokens': 1}})
    async def run():
        client = decision_client(authorize=authorize, record=record, transport=Wire(), api_key='synthetic-not-secret')
        try:
            return await client.decide(prepare_decision(value))
        finally:
            await client.aclose()
    assert decode_decision(value, asyncio.run(run())) == 'no_graph'
    assert len(seen) == 1


def test_retained_result_reconstructs_choice_and_rejects_tampering():
    from application_state.agent_conversation.native_plan_graph_need import decode_retained_result
    source = result(answers={'graph_need': ChoiceDecisionAnswer(selected='no_graph')})
    raw = source.model_dump_json(); digest = sha256(raw.encode('utf-8')).hexdigest()
    assert decode_retained_result(parent(), raw, digest) == 'no_graph'
    with pytest.raises(ValueError):
        decode_retained_result(parent(), raw.replace('no_graph', 'require_graph'), digest)
    changed = raw.replace('"answers":{', '"answers":{"unexpected":{},')
    with pytest.raises(ValueError):
        decode_retained_result(parent(), changed, sha256(changed.encode()).hexdigest())
    with pytest.raises(ValueError):
        decode_retained_result(parent(), raw + ' ', sha256((raw + ' ').encode()).hexdigest())


def pending_receipt():
    from application_state.agent_conversation.native_context import SurfaceNativeContextReceiptV1
    from tests.test_surface_native_context import seal, wire
    data = wire('plan')
    data['native_query'] = {'schema': 'dmb_native_plan_graph_query_pending_v1',
        'authority': data['native_query']['authority'] | {'scope_mode': 'world', 'campaign_id': None},
        'question': 'What did the check reveal?'}
    data['assembled_input'] = {'assembler_version': 'native_plan_request_admission_v1',
        'manifest_sha256': '1'*64, 'submitted_intent_sha256': '2'*64,
        'dialogue_sha256': '3'*64, 'tokenizer_name': 'test', 'tokenizer_version': '1',
        'context_window_limit': 1000, 'output_token_reserve': 100}
    return SurfaceNativeContextReceiptV1.model_validate(seal(data))



def test_plan_pending_pin_keeps_source_authority_without_graph_acquisition(monkeypatch):
    from types import SimpleNamespace
    from apps.live_control_server.services import native_graph_reads as reads
    receipt = pending_receipt()
    authority = receipt.native_query.authority
    source = SimpleNamespace(authority=authority)
    binding = SimpleNamespace(managed_world_id=authority.managed_world_id,
        native_world_id=authority.native_world_id, binding_version=authority.binding_version)
    monkeypatch.setattr(reads, 'resolve_managed_world_binding', lambda _: binding)
    monkeypatch.setattr(reads, 'prepare_query', lambda *a, **kw: pytest.fail('Unexpected Graph discovery'))
    query = reads.pending_plan_query(authority.managed_world_id, 'A new question?', source)
    assert type(query) is type(receipt.native_query)
    assert query.authority == authority and query.question == 'A new question?'
    with pytest.raises(ValueError, match='authority differ'):
        reads.pending_plan_query('other-world', 'A new question?', source)


def test_pending_receipt_roundtrips_and_requires_plan_admission_and_same_authority():
    from application_state.agent_conversation.native_context import SurfaceNativeContextReceiptV1
    from tests.test_surface_native_context import seal, wire
    value = pending_receipt()
    assert SurfaceNativeContextReceiptV1.model_validate_json(value.model_dump_json(by_alias=True)) == value
    data = value.model_dump(mode='json', by_alias=True)
    data['native_query']['authority']['revision_id'] = 'other-revision'
    with pytest.raises(ValueError, match='commitments differ'):
        SurfaceNativeContextReceiptV1.model_validate(seal(data))
    data = value.model_dump(mode='json', by_alias=True)
    data['assembled_input'] = wire('plan')['assembled_input']
    with pytest.raises(ValueError, match='request-owned Plan'):
        SurfaceNativeContextReceiptV1.model_validate(seal(data))


def pending_execution(choice):
    from types import SimpleNamespace
    from uuid import uuid4
    from application_state.agent_conversation import types as t
    from application_state.agent_conversation.native_execution import NativePlanActionV2
    from application_state.agent_conversation.native_plan_graph_need import (
        NativePlanGraphNeedInputV1, NativePlanGraphNeedObservedV1, canonical_wire,
    )
    from application_state.agent_conversation.native_retrieval import NativePlanGraphNeedAuthorizedV1
    from application_state.agent_conversation.rules_authority_types import canonical_sha256
    from tests.test_surface_native_context import WORK_MARKDOWN
    context = pending_receipt()
    dialogue = (RetrievalDialogue(role='user', content='Earlier synthetic context.'),)
    admission = context.assembled_input.model_copy(update={'dialogue_sha256': opening_dialogue_sha256(dialogue)})
    context = context.model_copy(update={'assembled_input': admission})
    query = context.native_query
    semantic = NativePlanGraphNeedInputV1(pending_query_sha256=canonical_sha256(query),
        admission_sha256=canonical_sha256(admission), question=query.question, dialogue=dialogue,
        current_work=WORK_MARKDOWN)
    action = NativePlanActionV2.model_construct(intent=SimpleNamespace(message=query.question,
        graph_request=SimpleNamespace(revision_pin=None)))
    role = SimpleNamespace(identity=lambda: ('typesafe', 'typesafe-ai/jev-1.14.0', 'decision'))
    execution = SimpleNamespace(policy=SimpleNamespace(action=action, provider_roles=SimpleNamespace(controller=role)),
        context_receipt_sha256='4'*64, execution_policy_sha256='5'*64, events=[])
    attempt, request_id = uuid4(), uuid4()
    auth = NativePlanGraphNeedAuthorizedV1.model_construct(event_id=uuid4(), sequence=0,
        provider_attempt_id=attempt, decision_request_id=request_id, provider='typesafe',
        model='typesafe-ai/jev-1.14.0', api_mode='decision', parent_request_sha256=semantic.digest,
        parent_json=semantic.model_dump_json(by_alias=True),
        envelope_sha256=sha256(canonical_wire(semantic)).hexdigest())
    lifecycle = [t.ProviderOutcomeEventV1(kind='provider_outcome', event_id=uuid4(), sequence=n,
        provider_attempt_id=attempt, outcome=outcome) for n, outcome in ((1, 'sdk_entered'), (2, 'response_received'))]
    raw = result(answers={'graph_need': ChoiceDecisionAnswer(selected=choice)}).model_dump_json()
    observed = NativePlanGraphNeedObservedV1(event_id=uuid4(), sequence=3, controller_attempt_id=attempt,
        decision_request_id=request_id, context_receipt_sha256=execution.context_receipt_sha256,
        execution_policy_sha256=execution.execution_policy_sha256, parent=semantic,
        envelope_sha256=auth.envelope_sha256, result_json=raw, result_sha256=sha256(raw.encode()).hexdigest(),
        choice=choice)
    execution.events = [auth, *lifecycle, observed]
    return context, execution, observed


def test_no_graph_closure_requires_acknowledged_decision_and_blocks_late_start():
    from uuid import uuid4
    from application_state.agent_conversation.native_plan_graph_need import (
        NativePlanGraphQueryAuthorizedV1, NativePlanGraphQueryClosedV1, validate_pending_graph,
    )
    context, execution, observed = pending_execution('no_graph')
    closed = NativePlanGraphQueryClosedV1(event_id=uuid4(), sequence=4, need_event_id=observed.event_id,
        pending_query_sha256=observed.parent.pending_query_sha256)
    execution.events.append(closed)
    assert validate_pending_graph(context, execution) is None
    execution.events.pop(2)
    with pytest.raises(ValueError, match='acknowledged SDK lifecycle'):
        validate_pending_graph(context, execution)
    context, execution, observed = pending_execution('no_graph')
    execution.events.append(NativePlanGraphQueryAuthorizedV1(event_id=uuid4(), sequence=4,
        need_event_id=observed.event_id, pending_query_sha256=observed.parent.pending_query_sha256))
    with pytest.raises(ValueError, match='Graph-need decision'):
        validate_pending_graph(context, execution)


def test_pending_or_uncertain_graph_cannot_authorize_writer():
    from application_state.agent_conversation.native_execution import NativeWriterAuthorizedV1
    from application_state.agent_conversation.native_plan_graph_need import validate_pending_graph
    context, execution, _ = pending_execution('uncertain')
    execution.events.append(NativeWriterAuthorizedV1.model_construct(sequence=4))
    with pytest.raises(ValueError, match='writer requires'):
        validate_pending_graph(context, execution)


def current_pending_context():
    from application_state.agent_conversation import types as t
    from application_state.agent_conversation.native_context import NativePlanGraphQueryPendingV1, SurfaceNativeContextReceiptV1
    from application_state.agent_conversation.native_plan_opening import request_manifest
    from tests.test_native_plan_opening import request_context
    from tests.test_surface_native_context import seal
    from tests.test_surface_native_execution import execution
    context, record = request_context(source_discovery_mode='controller_selection_v1')
    pending = NativePlanGraphQueryPendingV1(authority=context.native_query.authority,
        question=record.policy.action.intent.message)
    policy = record.policy.model_copy(update={'native_query_sha256': t.canonical_sha256(pending)})
    admission = context.assembled_input
    manifest = request_manifest(action=policy.action, work_context=context.work_context,
        source_authority_sha256=policy.source_authority_sha256, native_query_sha256=policy.native_query_sha256,
        provenance_sha256=context.provenance_sha256, provider_roles=policy.provider_roles,
        provider_input_accounting=policy.provider_input_accounting, admission=admission)
    admission = admission.model_copy(update={'manifest_sha256': t.canonical_sha256(manifest)})
    data = context.model_dump(mode='json', by_alias=True)
    data['native_query'] = pending.model_dump(mode='json', by_alias=True)
    data['assembled_input'] = admission.model_dump(mode='json', by_alias=True)
    context = SurfaceNativeContextReceiptV1.model_validate(seal(data))
    return context, execution(context.context_receipt_sha256, policy)


def test_pending_receipt_and_empty_execution_bind_at_actual_native_boundary():
    from application_state.agent_conversation.native_execution import validate_context_binding
    context, record = current_pending_context()
    assert validate_context_binding(context, record) == record
    assert type(context).model_validate_json(context.model_dump_json(by_alias=True)) == context
    assert type(record).model_validate_json(record.model_dump_json(by_alias=True)) == record


def actual_need_execution(choice='no_graph'):
    from uuid import uuid4
    from application_state.agent_conversation import types as t
    from application_state.agent_conversation.native_execution import validate_context_binding
    from application_state.agent_conversation.native_plan_graph_need import (
        NativePlanGraphNeedInputV1, NativePlanGraphNeedObservedV1, NativePlanGraphQueryClosedV1, canonical_wire,
    )
    from application_state.agent_conversation.native_retrieval import NativePlanGraphNeedAuthorizedV1
    from application_state.agent_conversation.rules_authority_types import canonical_sha256
    from tests.test_surface_native_context import WORK_MARKDOWN
    from tests.test_surface_native_execution import controller, execution, outcomes
    context, record = current_pending_context()
    value = NativePlanGraphNeedInputV1(pending_query_sha256=canonical_sha256(context.native_query),
        admission_sha256=canonical_sha256(context.assembled_input), question=record.policy.action.intent.message,
        dialogue=(), current_work=WORK_MARKDOWN)
    base = controller('plan', record.policy, semantic=True)
    auth = NativePlanGraphNeedAuthorizedV1.model_validate(base.model_dump(mode='json') | {
        'kind': 'native_plan_graph_need_authorized_v1', 'parent_request_sha256': value.digest,
        'parent_json': value.model_dump_json(by_alias=True),
        'envelope_sha256': sha256(canonical_wire(value, expected_model=base.model)).hexdigest()})
    typed = result(answers={'graph_need': ChoiceDecisionAnswer(selected=choice)})
    typed = typed.model_copy(update={'observation': typed.observation.model_copy(update={
        'resolved_model': auth.model, 'response_model': auth.model})})
    raw = typed.model_dump_json()
    observed = NativePlanGraphNeedObservedV1(event_id=uuid4(), sequence=3,
        controller_attempt_id=auth.provider_attempt_id, decision_request_id=auth.decision_request_id,
        context_receipt_sha256=context.context_receipt_sha256, execution_policy_sha256=record.execution_policy_sha256,
        parent=value, envelope_sha256=auth.envelope_sha256, result_json=raw,
        result_sha256=sha256(raw.encode()).hexdigest(), choice=choice)
    return context, record, auth, outcomes(auth, 1), observed


def actual_closed_execution():
    from uuid import uuid4
    from application_state.agent_conversation.native_plan_graph_need import NativePlanGraphQueryClosedV1
    from tests.test_surface_native_execution import execution
    context, record, auth, lifecycle, observed = actual_need_execution()
    closed = NativePlanGraphQueryClosedV1(event_id=uuid4(), sequence=4, need_event_id=observed.event_id,
        pending_query_sha256=observed.parent.pending_query_sha256)
    retained = execution(context.context_receipt_sha256, record.policy, [auth, *lifecycle, observed, closed])
    return context, retained


def test_no_graph_closure_roundtrips_through_actual_execution_and_context_validation():
    from application_state.agent_conversation.native_execution import validate_context_binding
    context, retained = actual_closed_execution()
    assert validate_context_binding(context, retained) == retained
    reopened = type(retained).model_validate_json(retained.model_dump_json(by_alias=True))
    assert validate_context_binding(context, reopened) == retained


def test_no_graph_writer_projection_does_not_claim_complete_graph():
    from application_state.agent_conversation.native_writer import model_frame
    context, retained = actual_closed_execution()
    frame = model_frame(context, retained)
    assert frame['native_statements']['status'] == 'not_requested'
    assert frame['native_statements']['statements'] == []
    assert frame['native_assertions'] is None
    assert frame['native_body_evidence']['coverage']['global_completeness'] == 'not_established'


def test_graph_settlement_requires_exact_started_query_and_pinned_authority():
    from uuid import uuid4
    from application_state.agent_conversation.native_plan_assertions import NativePlanQueryV2
    from application_state.agent_conversation.native_plan_graph_need import (
        NativePlanGraphQueryAuthorizedV1, NativePlanGraphQueryStartedV1, NativePlanGraphQuerySettledV1,
        NativePlanGraphQueryFailedV1, validate_pending_graph,
    )
    from tests.test_surface_native_context import wire
    context, execution, observed = pending_execution('require_graph')
    grant = NativePlanGraphQueryAuthorizedV1(event_id=uuid4(), sequence=4, need_event_id=observed.event_id,
        pending_query_sha256=observed.parent.pending_query_sha256)
    start = NativePlanGraphQueryStartedV1(event_id=uuid4(), sequence=5, authorization_event_id=grant.event_id)
    data = wire('plan')['native_query']; data['authority']['scope_mode'] = 'world'; data['authority']['campaign_id'] = None
    query = NativePlanQueryV2.model_validate(data)
    settled = NativePlanGraphQuerySettledV1(event_id=uuid4(), sequence=6, started_event_id=start.event_id, query=query)
    execution.events.extend([grant, start, settled])
    assert validate_pending_graph(context, execution) == query
    bad = query.model_copy(update={'question': 'Different question'})
    execution.events[-1] = settled.model_copy(update={'query': bad})
    with pytest.raises(ValueError, match='pinned authority or question'):
        validate_pending_graph(context, execution)
    execution.events[-1] = NativePlanGraphQueryFailedV1(event_id=uuid4(), sequence=6,
        started_event_id=start.event_id, reason='uncertain_owner_result')
    assert validate_pending_graph(context, execution) == context.native_query
    execution.events.append(settled.model_copy(update={'sequence': 7}))
    with pytest.raises(ValueError):
        validate_pending_graph(context, execution)


@pytest.mark.parametrize('event_name', [
    'BuildAuthoredReferenceAuthorizedV2', 'BuildAuthoredReferenceReadV2', 'BuildAuthoredReferenceReadV3',
])
def test_authored_graph_access_before_settlement_is_rejected(event_name):
    from application_state.agent_conversation import authored_graph_references as refs
    from application_state.agent_conversation.native_plan_graph_need import validate_pending_graph
    context, execution, _ = pending_execution('require_graph')
    execution.events.append(getattr(refs, event_name).model_construct(sequence=4))
    with pytest.raises(ValueError, match='prior exact query settlement'):
        validate_pending_graph(context, execution)


def test_graph_reads_before_settlement_are_rejected():
    from application_state.agent_conversation import types as t
    from application_state.agent_conversation.native_plan_graph_need import validate_pending_graph
    context, execution, _ = pending_execution('require_graph')
    execution.events.append(t.NativePlanStatementReadAuthorizedV1.model_construct(sequence=4))
    with pytest.raises(ValueError, match='prior exact query settlement'):
        validate_pending_graph(context, execution)


def test_unobserved_authorization_must_already_match_original_work_and_wire():
    from application_state.agent_conversation.native_plan_graph_need import validate_pending_graph
    context, execution, _ = pending_execution('no_graph')
    auth = execution.events[0]
    execution.events = [auth]
    assert validate_pending_graph(context, execution) == context.native_query
    execution.events = [auth.model_copy(update={'envelope_sha256': 'f'*64})]
    with pytest.raises(ValueError, match='exact prepared parent'):
        validate_pending_graph(context, execution)
    execution.events = [auth.model_copy(update={'parent_json': auth.parent_json.replace('unplayed possibility', 'changed possibility')})]
    with pytest.raises(ValueError, match='committed request'):
        validate_pending_graph(context, execution)


# The fixture supplies a unique synthetic World; the retained-clone runner owns
# the App database and does not reset or enumerate its contents.
from tests.test_agent_native_corpus_sources import source_adapter, lane  # noqa: E402,F401


def _admitted_pending_turn(source_adapter, monkeypatch):
    from uuid import uuid4
    from application_state.agent_conversation import types as t
    from application_state.agent_conversation.native_context import NativePlanGraphQueryPendingV1, PlanWorkContextV1
    from application_state.agent_conversation.native_plan_statements import NativePlanQueryAuthorityV1
    from apps.live_control_server.services import agent_turn_service as owner, plan_source_turn
    from tests.test_surface_native_context import provenance_for
    a = source_adapter
    monkeypatch.setattr('apps.live_control_server.services.build_related_pages.discover', lambda *_a, **_k: [])
    request = a.request.model_copy(update={'plan_context_policy': t.PlanContextPolicyV2(
        policy='auto_plan_world', graph_source='reviewed_native_graph')})
    intent = owner._submitted_turn_intent(request, world_id=a.world_id)
    work_context = PlanWorkContextV1(plan_basis=plan_source_turn._plan_basis(a.work),
        plan_context_policy=request.plan_context_policy, playable_target=None)
    provenance = provenance_for(work_context).model_copy(update={'surface_instance_id': request.surface.instance_id})
    authority = a.native_source_authority
    graph_authority = NativePlanQueryAuthorityV1(**{k: getattr(authority, k) for k in (
        'managed_world_id', 'native_world_id', 'binding_version', 'revision_id', 'domain_ref', 'profile_ref',
        'acquisition_epoch')}, scope_mode='world', campaign_id=None)
    pending = NativePlanGraphQueryPendingV1(authority=graph_authority, question=request.message)
    receipt, execution, _ = plan_source_turn.freeze_plan_request(request, a.work, None, a.budget,
        authority=authority, native_query=pending, provenance=provenance, submitted_intent=intent, dialogue=())
    service = a.service
    pointer = service.get_world_pointer(a.world_id)
    conversation = service.new_conversation(t.ConversationCommand(world_id=a.world_id, command_id=uuid4(),
        expected_pointer_revision=pointer.revision, expected_active_conversation_id=pointer.active_conversation_id))
    submission = t.TurnSubmission(world_id=a.world_id, conversation_id=conversation.conversation_id,
        idempotency_key=uuid4(), expected_conversation_revision=1, user_text=request.message, provenance=provenance,
        submitted_intent_v2=intent, graph_context_receipt=receipt, graph_context_execution=execution)
    created = service.accept_turn(submission)
    reopened = service.inspect_turn(world_id=a.world_id, turn_id=created.turn_id)
    assert reopened.graph_context_receipt == receipt
    assert reopened.graph_context_execution == execution
    return service, created


@pytest.mark.parametrize('source_adapter', [{'unique_world': True, 'sources': [('first', '# Synthetic\n')]}], indirect=True)
def test_pending_receipt_is_admitted_and_reopened_from_app_database(source_adapter, monkeypatch):
    _admitted_pending_turn(source_adapter, monkeypatch)


@pytest.mark.parametrize('source_adapter', [{'unique_world': True, 'sources': [('first', '# Synthetic\n')]}], indirect=True)
@pytest.mark.parametrize('event_class', [
    'NativePlanGraphNeedAuthorizedV1', 'NativePlanGraphNeedObservedV1', 'NativePlanGraphQueryAuthorizedV1',
    'NativePlanGraphQueryStartedV1', 'NativePlanGraphQueryClosedV1', 'NativePlanGraphQueryFailedV1',
    'NativePlanGraphQuerySettledV1',
])
def test_materialized_plan_graph_events_are_refused_without_persistence(source_adapter, monkeypatch, event_class):
    from uuid import uuid4
    from application_state.agent_conversation import native_plan_graph_need, native_retrieval
    from application_state.errors import ApplicationStateValidationError
    service, created = _admitted_pending_turn(source_adapter, monkeypatch)
    turn = service.claim_turn(created.world_id, created.conversation_id, created.turn_id,
        expected_revision=created.revision).turn
    event_type = getattr(native_plan_graph_need, event_class, None) or getattr(native_retrieval, event_class)
    event = event_type.model_construct(event_id=uuid4(), sequence=0)
    with pytest.raises(ApplicationStateValidationError, match='producer is not active'):
        service._append_graph_execution_event(turn.world_id, turn.conversation_id, turn.turn_id,
            expected_revision=turn.revision, expected_attempt=turn.attempt, event=None,
            duplicate_key='event_id', native_source_materializer=lambda _conn, _turn: event)
    reopened = service.inspect_turn(world_id=turn.world_id, turn_id=turn.turn_id)
    assert reopened.revision == turn.revision
    assert reopened.graph_context_execution == turn.graph_context_execution
    # Model an already-known event to prove the refusal happens before the
    # duplicate-return shortcut. The actual database remains unchanged.
    duplicate_execution = turn.graph_context_execution.model_copy(update={'events': [event]})
    duplicate_turn = turn.model_copy(update={'graph_context_execution': duplicate_execution})
    with monkeypatch.context() as patch:
        patch.setattr(service, '_lock_execution_append_turn', lambda *_args: duplicate_turn)
        with pytest.raises(ApplicationStateValidationError, match='producer is not active'):
            service._append_graph_execution_event(turn.world_id, turn.conversation_id, turn.turn_id,
                expected_revision=turn.revision, expected_attempt=turn.attempt, event=None,
                duplicate_key='event_id', native_source_materializer=lambda _conn, _turn: event)
    reopened = service.inspect_turn(world_id=turn.world_id, turn_id=turn.turn_id)
    assert reopened.revision == turn.revision
    assert reopened.graph_context_execution == turn.graph_context_execution


def test_typed_execution_settles_exact_graph_query_and_rejects_late_failure():
    from uuid import uuid4
    from application_state.agent_conversation.native_execution import effective_native_query, validate_context_binding
    from application_state.agent_conversation.native_plan_assertions import NativePlanQueryV2
    from application_state.agent_conversation.native_plan_graph_need import (
        NativePlanGraphQueryAuthorizedV1, NativePlanGraphQueryStartedV1,
        NativePlanGraphQuerySettledV1, NativePlanGraphQueryFailedV1,
    )
    from tests.test_surface_native_context import wire
    from tests.test_surface_native_execution import execution
    context, record, auth, lifecycle, observed = actual_need_execution('require_graph')
    grant = NativePlanGraphQueryAuthorizedV1(event_id=uuid4(), sequence=4, need_event_id=observed.event_id,
        pending_query_sha256=observed.parent.pending_query_sha256)
    start = NativePlanGraphQueryStartedV1(event_id=uuid4(), sequence=5, authorization_event_id=grant.event_id)
    data = wire('plan')['native_query']; data['authority']['scope_mode'] = 'world'; data['authority']['campaign_id'] = None
    query = NativePlanQueryV2.model_validate(data)
    settlement = NativePlanGraphQuerySettledV1(event_id=uuid4(), sequence=6, started_event_id=start.event_id, query=query)
    events = [auth, *lifecycle, observed, grant, start, settlement]
    retained = execution(context.context_receipt_sha256, record.policy, events)
    assert validate_context_binding(context, retained) == retained
    assert effective_native_query(context, retained) == query
    failure = NativePlanGraphQueryFailedV1(event_id=uuid4(), sequence=7,
        started_event_id=start.event_id, reason='uncertain_owner_result')
    with pytest.raises(ValueError):
        invalid = execution(context.context_receipt_sha256, record.policy, [*events, failure])
        validate_context_binding(context, invalid)


def test_no_graph_closure_cannot_discard_explicit_authored_graph_reference(monkeypatch):
    from types import SimpleNamespace
    from uuid import uuid4
    from application_state.agent_conversation import authored_graph_references as refs
    from application_state.agent_conversation.native_plan_graph_need import NativePlanGraphQueryClosedV1, validate_pending_graph
    context, execution, observed = pending_execution('no_graph')
    authored = refs.AuthoredGraphReferenceV1.model_construct()
    monkeypatch.setattr(refs, 'native_references', lambda _execution: SimpleNamespace(references=(authored,)))
    execution.events.append(NativePlanGraphQueryClosedV1(event_id=uuid4(), sequence=4,
        need_event_id=observed.event_id, pending_query_sha256=observed.parent.pending_query_sha256))
    with pytest.raises(ValueError, match='authored Graph references'):
        validate_pending_graph(context, execution)


def test_graph_need_first_provider_is_still_bounded_by_frozen_allowance():
    from application_state.agent_conversation import types as t
    context, record, auth, _, _ = actual_need_execution()
    t.validate_provider_envelope_accounting(context.assembled_input, record, auth)
    with pytest.raises(ValueError, match='context window'):
        t.validate_provider_envelope_accounting(context.assembled_input, record,
            auth.model_copy(update={'input_tokens': context.assembled_input.context_window_limit + 1}))


def no_graph_writer_prefix():
    from uuid import uuid4
    from application_state.agent_conversation import types as t
    from application_state.agent_conversation.native_execution import NativePlanOpeningSelectedV1, validate_context_binding
    from application_state.agent_conversation.native_plan_graph_need import NativePlanGraphQueryStartedV1
    from application_state.agent_conversation.native_retrieval import NativePlanOpeningAuthorizedV1
    from application_state.agent_conversation.native_writer import model_frame
    from tests.test_surface_native_execution import controller, execution, native_writer, outcomes
    context, closed = actual_closed_execution()
    policy = closed.policy
    base = controller('plan', policy, sequence=5, semantic=True)
    opening = NativePlanOpeningAuthorizedV1.model_validate(base.model_dump(mode='json') | {
        'kind': 'native_plan_opening_authorized_v1'})
    selected = NativePlanOpeningSelectedV1(event_id=uuid4(), sequence=8,
        context_receipt_sha256=context.context_receipt_sha256, execution_policy_sha256=closed.execution_policy_sha256,
        decision_request_id=opening.decision_request_id, controller_attempt_id=opening.provider_attempt_id,
        controller_envelope_sha256=opening.envelope_sha256, controller_response_sha256='a'*64,
        parent_request_sha256=opening.parent_request_sha256, requested_work='discuss',
        target_capture_sha256=None, original_capture_sha256=None, placement_catalog_sha256=None,
        placement_selector=None, original_capture=None, placement_catalog=None,
        operation='finish_retrieval', selected_handles=[], post_read_plan='finish_if_selected_reads_succeed')
    before_writer = execution(context.context_receipt_sha256, policy,
        [*closed.events, opening, *outcomes(opening, 6), selected])
    return context, before_writer


def test_no_graph_writer_authorization_roundtrips_and_rejects_late_graph_events():
    from uuid import uuid4
    from application_state.agent_conversation import types as t
    from application_state.agent_conversation.native_execution import validate_context_binding
    from application_state.agent_conversation.native_plan_graph_need import NativePlanGraphQueryStartedV1
    from application_state.agent_conversation.native_writer import model_frame
    from tests.test_surface_native_execution import execution, native_writer
    context, before_writer = no_graph_writer_prefix()
    policy = before_writer.policy
    frame = model_frame(context, before_writer)
    writer = native_writer('plan', policy, sequence=9).model_copy(update={'frame_sha256': t.canonical_sha256(frame)})
    retained = execution(context.context_receipt_sha256, policy, [*before_writer.events, writer])
    assert validate_context_binding(context, retained) == retained
    reopened = type(retained).model_validate_json(retained.model_dump_json(by_alias=True))
    assert validate_context_binding(context, reopened) == retained
    late = NativePlanGraphQueryStartedV1(event_id=uuid4(), sequence=10, authorization_event_id=uuid4())
    with pytest.raises(ValueError):
        bad = execution(context.context_receipt_sha256, policy, [*retained.events, late])
        validate_context_binding(context, bad)


def _pending_graph_allows_exact_authored_reference_after_query_settlement(monkeypatch, support=None):
    from uuid import uuid4
    from application_state.agent_conversation import types as t
    from application_state.agent_conversation.authored_graph_references import AuthoredGraphReferenceV1, AuthoredReferencesV2
    from application_state.agent_conversation.native_context import SurfaceNativeContextReceiptV1
    from application_state.agent_conversation.native_execution import validate_context_binding
    from application_state.agent_conversation.native_plan_assertions import NativeGraphQueryV3
    from application_state.agent_conversation.native_plan_graph_need import (
        NativePlanGraphNeedInputV1, NativePlanGraphNeedObservedV1, NativePlanGraphQueryAuthorizedV1,
        NativePlanGraphQueryStartedV1, NativePlanGraphQuerySettledV1, canonical_wire,
    )
    from application_state.agent_conversation.native_plan_opening import request_manifest
    from application_state.agent_conversation.native_retrieval import NativePlanGraphNeedAuthorizedV1
    from tests.test_surface_native_context import WORK_MARKDOWN, seal, wire
    from tests.test_surface_native_execution import controller, execution, outcomes
    context, record = current_pending_context()
    authority = context.native_query.authority
    ref = AuthoredGraphReferenceV1(managed_world_id=authority.managed_world_id,
        native_world_id=authority.native_world_id, binding_version=authority.binding_version,
        graph_revision=authority.revision_id, node_id=support.assertion.subject_entity_id if support else 'ent:synthetic', label='Synthetic selected object')
    refs = AuthoredReferencesV2(references=(ref,))
    data = record.policy.action.intent.model_dump(mode='json', by_alias=True)
    data.update(schema='dmb_agent_submitted_turn_intent_v3', authored_references=refs.model_dump(mode='json', by_alias=True))
    intent = t.SubmittedTurnIntentV3.model_validate(data)
    action = record.policy.action.model_copy(update={'intent': intent})
    policy = record.policy.model_copy(update={'action': action})
    admission = context.assembled_input.model_copy(update={'submitted_intent_sha256': t.canonical_sha256(intent)})
    manifest = request_manifest(action=action, work_context=context.work_context,
        source_authority_sha256=policy.source_authority_sha256, native_query_sha256=policy.native_query_sha256,
        provenance_sha256=context.provenance_sha256, provider_roles=policy.provider_roles,
        provider_input_accounting=policy.provider_input_accounting, admission=admission)
    admission = admission.model_copy(update={'manifest_sha256': t.canonical_sha256(manifest)})
    raw_context = context.model_dump(mode='json', by_alias=True)
    raw_context['assembled_input'] = admission.model_dump(mode='json', by_alias=True)
    context = SurfaceNativeContextReceiptV1.model_validate(seal(raw_context))
    record = execution(context.context_receipt_sha256, policy)
    capture = t.BuildAuthoredReferencesCapturedV1(kind='build_authored_references_captured_v1', event_id=uuid4(),
        sequence=0, references=refs, read_graph_revision=authority.revision_id, turn_id=uuid4(),
        conversation_id=uuid4(), attempt=1, submitted_intent_fingerprint=t.submitted_turn_intent_fingerprint_v2(intent))
    value = NativePlanGraphNeedInputV1(pending_query_sha256=t.canonical_sha256(context.native_query),
        admission_sha256=t.canonical_sha256(admission), question=intent.message, dialogue=(), current_work=WORK_MARKDOWN)
    base = controller('plan', policy, sequence=1, semantic=True)
    auth = NativePlanGraphNeedAuthorizedV1.model_validate(base.model_dump(mode='json') | {
        'kind': 'native_plan_graph_need_authorized_v1', 'parent_request_sha256': value.digest,
        'parent_json': value.model_dump_json(by_alias=True),
        'envelope_sha256': sha256(canonical_wire(value, expected_model=base.model)).hexdigest()})
    typed = result(answers={'graph_need': ChoiceDecisionAnswer(selected='require_graph')})
    typed = typed.model_copy(update={'observation': typed.observation.model_copy(update={
        'resolved_model': auth.model, 'response_model': auth.model})})
    raw = typed.model_dump_json()
    observed = NativePlanGraphNeedObservedV1(event_id=uuid4(), sequence=4,
        controller_attempt_id=auth.provider_attempt_id, decision_request_id=auth.decision_request_id,
        context_receipt_sha256=context.context_receipt_sha256, execution_policy_sha256=record.execution_policy_sha256,
        parent=value, envelope_sha256=auth.envelope_sha256, result_json=raw,
        result_sha256=sha256(raw.encode()).hexdigest(), choice='require_graph')
    grant = NativePlanGraphQueryAuthorizedV1(event_id=uuid4(), sequence=5, need_event_id=observed.event_id,
        pending_query_sha256=value.pending_query_sha256)
    start = NativePlanGraphQueryStartedV1(event_id=uuid4(), sequence=6, authorization_event_id=grant.event_id)
    query_data = wire('plan')['native_query']; query_data['schema'] = 'dmb_native_graph_query_v3'
    query_data['authority']['scope_mode'] = 'world'; query_data['authority']['campaign_id'] = None
    matches = [] if support is None else [{'assertion_id': support.assertion.assertion_id,
        'subject_entity_id': ref.node_id, 'discovered_entity_ids': [ref.node_id],
        'assertion_sha256': t.canonical_sha256(support.assertion), 'label': 'Synthetic supported assertion'}]
    query_data['authored_targets'] = [{'node_id': ref.node_id, 'selection_revision_id': ref.graph_revision,
        'matches': [], 'assertion_matches': matches, 'status': 'complete', 'gap_codes': []}]
    query = NativeGraphQueryV3.model_validate(query_data)
    settlement = NativePlanGraphQuerySettledV1(event_id=uuid4(), sequence=7, started_event_id=start.event_id, query=query)
    retained = execution(context.context_receipt_sha256, policy, [capture, auth, *outcomes(auth, 2), observed, grant, start, settlement])
    assert validate_context_binding(context, retained) == retained
    assert validate_context_binding(context, type(retained).model_validate_json(retained.model_dump_json(by_alias=True))) == retained
    from application_state.agent_conversation.authored_graph_references import BuildAuthoredReferenceAuthorizedV2, BuildAuthoredReferenceReadV2
    authored_grant = BuildAuthoredReferenceAuthorizedV2(event_id=uuid4(), sequence=8, capture_event_id=capture.event_id,
        node_id=ref.node_id, context_receipt_sha256=context.context_receipt_sha256,
        execution_policy_sha256=retained.execution_policy_sha256, query_sha256=query.sha256)
    authored_read = BuildAuthoredReferenceReadV2(event_id=uuid4(), sequence=9, capture_event_id=capture.event_id,
        authorization_event_id=authored_grant.event_id, node_id=ref.node_id,
        statement_reads=(), assertion_reads=(support,) if support else (), unavailable_statement_ids=(), unavailable_assertion_ids=(), status='complete')
    with_read = execution(context.context_receipt_sha256, policy, [*retained.events, authored_grant, authored_read])
    assert validate_context_binding(context, with_read) == with_read
    assert validate_context_binding(context, type(with_read).model_validate_json(with_read.model_dump_json(by_alias=True))) == with_read
    if support is not None:
        altered = authored_read.model_copy(update={'assertion_reads': ()})
        bad_support = execution(context.context_receipt_sha256, policy, [*retained.events, authored_grant, altered])
        with pytest.raises(ValueError, match='support inventory'):
            validate_context_binding(context, bad_support)
        return
    from types import SimpleNamespace
    from apps.live_control_server.services import native_graph_reads
    from tests.test_native_corpus_source_access import GM
    binding = object()
    core = SimpleNamespace(query=query, repository=object(), pinned=(object(), SimpleNamespace(source_view=object()), None, None),
        binding=binding, resolve_binding=lambda _world: binding)
    monkeypatch.setattr(native_graph_reads, 'EvidenceReadService',
        lambda: SimpleNamespace(get_assertions_evidence=lambda _ctx, ids: () if not ids else pytest.fail('Unexpected evidence read')))
    captured = native_graph_reads.read_authored_reference(core, authored_grant, GM)
    assert captured.query_sha256 == query.sha256 and captured.node_id == ref.node_id
    assert not captured.statement_reads and not captured.assertion_reads
    bad_grant = authored_grant.model_copy(update={'query_sha256': policy.native_query_sha256})
    bad = execution(context.context_receipt_sha256, policy, [*retained.events, bad_grant, authored_read])
    with pytest.raises(ValueError, match='exact settled query digest'):
        validate_context_binding(context, bad)


def test_pending_graph_allows_exact_authored_reference_after_query_settlement(monkeypatch):
    _pending_graph_allows_exact_authored_reference_after_query_settlement(monkeypatch)


def test_pending_graph_roundtrip_preserves_nonempty_core_support(monkeypatch, core_read):
    # The Core fixture supplies real supported assertion bytes. The synthetic
    # target catalog then exercises the complete pending receipt and event join.
    _pending_graph_allows_exact_authored_reference_after_query_settlement(monkeypatch, core_read)


def test_no_graph_writer_reconstructs_actual_sdk_request_without_false_graph_evidence():
    import asyncio
    from application_state.agent_conversation.native_writer import model_frame, model_work_frame, verify_input_records
    from tests.test_surface_native_writer import actual_sdk_request, authorize, work_submission
    context, prefix = no_graph_writer_prefix()
    from application_state.agent_conversation.native_evidence_view import semantic_frame as evidence_view
    from application_state.agent_conversation.native_plan_work_view import semantic_frame as work_view
    frame = model_frame(context, prefix)
    work = work_submission(context, prefix)
    rendered_work = work_view(model_work_frame(context, prefix, **work), prefix)
    rendered_frame = evidence_view(frame)
    raw = asyncio.run(actual_sdk_request(rendered_frame, work_frame=rendered_work))
    retained, authorization = authorize(context, prefix, raw, rendered_frame)
    supports = verify_input_records(context, retained, authorization, raw, **work)
    assert supports.frame['native_statements']['status'] == 'not_requested'
    assert not supports.native_statements and not supports.native_assertions
    reopened = type(retained).model_validate_json(retained.model_dump_json(by_alias=True))
    assert verify_input_records(context, reopened, authorization, raw, **work) == supports


def test_no_graph_current_plan_prose_reconstructs_from_actual_sdk_request():
    import asyncio
    import httpx
    from openai import AsyncOpenAI
    from application_state.agent_conversation.native_evidence_view import render_plan_evidence, semantic_frame as evidence_view
    from application_state.agent_conversation.native_plan_work_view import semantic_frame as work_view
    from application_state.agent_conversation.native_writer import model_frame, model_work_frame, verify_input_records
    from tests.test_surface_native_writer import authorize, work_submission
    context, prefix = no_graph_writer_prefix()
    work = work_submission(context, prefix)
    rendered_frame = evidence_view(model_frame(context, prefix, passages_only=True))
    rendered_work = work_view(model_work_frame(context, prefix, **work), prefix)
    prose = render_plan_evidence(rendered_frame, rendered_work)
    assert 'Graph knowledge' not in prose
    sent = []
    def capture(request):
        sent.append(request.content.decode())
        return httpx.Response(200, request=request, json={'id': 'resp_synthetic', 'object': 'response',
            'created_at': 1, 'model': 'gpt-6-luna', 'status': 'completed', 'output': []})
    async def request():
        async with AsyncOpenAI(api_key='synthetic-not-secret', http_client=httpx.AsyncClient(
                transport=httpx.MockTransport(capture))) as client:
            await client.responses.create(model='gpt-6-luna', input=[{'role': 'user', 'content': prose}],
                tools=[], stream=False, max_output_tokens=4096)
    asyncio.run(request())
    assert len(sent) == 1
    retained, authorization = authorize(context, prefix, sent[0], rendered_frame)
    supports = verify_input_records(context, retained, authorization, sent[0], **work)
    assert supports.frame['native_statements']['status'] == 'not_requested'
    assert not supports.native_statements and not supports.native_assertions
    from application_state.agent_conversation.native_completion import normalize_candidate
    candidate = {'schema': supports.frame['answer_policy'], 'answer_segments': [
        {'kind': 'proposal', 'label': 'invented_idea', 'text': 'A quiet harbor.'}],
        'limitations': [], 'requested_detail_gaps': []}
    completion = normalize_candidate(candidate, context, retained, authorization, supports)
    assert not completion.native_body_citations and not completion.native_clause_citations
    assert not completion.native_assertion_citations
    assert all(getattr(segment, 'kind', None) != 'limitation' for segment in completion.answer_segments)
    from uuid import uuid4
    from application_state.agent_conversation import types as t
    from application_state.agent_conversation.native_completion import validate_retained_completion
    from tests.test_surface_native_execution import execution
    start = t.ProviderOutcomeEventV1(kind='provider_outcome', event_id=uuid4(), sequence=len(retained.events),
        provider_attempt_id=authorization.provider_attempt_id, outcome='sdk_entered')
    received = t.ProviderOutcomeEventV1(kind='provider_outcome', event_id=uuid4(), sequence=start.sequence + 1,
        provider_attempt_id=authorization.provider_attempt_id, outcome='response_received',
        request_id='synthetic-response', response_sha256='c'*64)
    binding = t.CompletionBindingEventV1(kind='completion_binding', event_id=uuid4(), sequence=received.sequence + 1,
        provider_attempt_id=authorization.provider_attempt_id, completion_sha256=t.canonical_sha256(completion),
        claim_graph_event_ids={})
    finished = execution(context.context_receipt_sha256, retained.policy, [*retained.events, start, received, binding])
    reopened = type(finished).model_validate_json(finished.model_dump_json(by_alias=True))
    validate_retained_completion(completion, context, reopened, authorization.provider_attempt_id, {})


@pytest.mark.parametrize('event_class', [
    'NativePlanGraphNeedAuthorizedV1', 'NativePlanGraphNeedObservedV1', 'NativePlanGraphQueryAuthorizedV1',
    'NativePlanGraphQueryStartedV1', 'NativePlanGraphQueryClosedV1', 'NativePlanGraphQueryFailedV1',
    'NativePlanGraphQuerySettledV1',
])
def test_reader_only_generic_append_refuses_new_graph_events_before_database(event_class):
    from uuid import uuid4
    from application_state.agent_conversation import AgentConversationService, native_plan_graph_need, native_retrieval
    from application_state.errors import ApplicationStateValidationError
    event_type = getattr(native_plan_graph_need, event_class, None) or getattr(native_retrieval, event_class)
    event = event_type.model_construct()
    service = AgentConversationService()
    with pytest.raises(ApplicationStateValidationError, match='producer is not active'):
        service._append_graph_execution_event('synthetic-world', uuid4(), uuid4(), expected_revision=1,
            expected_attempt=1, event=event, duplicate_key='event_id')


def test_forged_settlement_cannot_extend_legacy_receipt_authority():
    from uuid import uuid4
    from application_state.agent_conversation.native_execution import validate_context_binding
    from application_state.agent_conversation.native_plan_graph_need import NativePlanGraphQuerySettledV1
    from tests.test_surface_native_execution import component, execution
    context, record = component('plan')
    forged = NativePlanGraphQuerySettledV1(event_id=uuid4(), sequence=0,
        started_event_id=uuid4(), query=context.native_query)
    candidate = execution(context.context_receipt_sha256, record.policy, [forged])
    with pytest.raises(ValueError, match='require a pending Plan query'):
        validate_context_binding(context, candidate)


def test_forged_legacy_turn_is_rejected_before_authored_materialization():
    from types import SimpleNamespace
    from uuid import uuid4
    from application_state.agent_conversation.native_plan_graph_need import NativePlanGraphQuerySettledV1
    from tests.application_state.test_native_corpus_sources import source_turn
    from tests.test_surface_native_context import provenance_for
    from tests.test_surface_native_execution import component, execution
    context, record = component('plan')
    forged = NativePlanGraphQuerySettledV1(event_id=uuid4(), sequence=0,
        started_event_id=uuid4(), query=context.native_query)
    candidate = execution(context.context_receipt_sha256, record.policy, [forged])
    intent = record.policy.action.intent
    provenance = provenance_for(context.work_context).model_copy(update={'surface_instance_id': intent.surface_instance_id})
    submission = SimpleNamespace(conversation_id=uuid4(), world_id=intent.world_id, idempotency_key=uuid4(),
        user_text=intent.message, provenance=provenance, submitted_intent_v2=intent,
        graph_context_receipt=context, graph_context_execution=candidate)
    materializations = []
    def materialize(_grant):
        materializations.append(True)
    with pytest.raises(ValueError, match='require a pending Plan query'):
        turn = source_turn(submission)  # Same typed Turn reconstruction used by the locked APP read owner.
        from application_state.agent_conversation.authored_graph_references import observe_native_reference
        observe_native_reference(turn, event_id=uuid4(), authorization_event_id=uuid4(), materialize=materialize)
    assert not materializations


def test_settled_authored_core_read_keeps_nonempty_support_and_rejects_substitution(application_state_dsn, tmp_path, monkeypatch):
    from uuid import uuid4
    from application_state.agent_conversation import types as t
    from application_state.agent_conversation.authored_graph_references import (
        AuthoredGraphReferenceV1, AuthoredReferencesV2, BuildAuthoredReferenceAuthorizedV2,
        BuildAuthoredReferenceReadV2, validate_native_context, validate_native_execution,
    )
    from application_state.agent_conversation.native_execution import NativePlanActionV2
    from application_state.agent_conversation.native_plan_graph_need import NativePlanGraphQuerySettledV1
    from apps.live_control_server.services.native_graph_reads import prepare_query, read_authored_reference
    from tests.test_native_plan_assertions import publish
    from tests.test_native_plan_statements import bound
    from tests.test_source_statements import make_lane, GM
    from tests.test_surface_native_execution import component, execution
    lane = make_lane(tmp_path, monkeypatch, narrow=True)
    publish(lane)
    world = lane.world.world_id
    ref = AuthoredGraphReferenceV1(managed_world_id=world, native_world_id=world, binding_version=1,
        graph_revision=lane.repo.get_head(world).head_revision_id, node_id=lane.ids['B'], label='Synthetic object')
    refs = AuthoredReferencesV2(references=(ref,))
    core, query = prepare_query(world, 'What did B do?', GM, repository=lane.repo,
        resolve_binding=lambda _: bound(lane), authored_references=refs)
    target, = query.authored_targets
    assert target.assertion_matches
    _, old = component('plan')
    raw_intent = old.policy.action.intent.model_dump(mode='json', by_alias=True)
    raw_intent.update(schema='dmb_agent_submitted_turn_intent_v3', world_id=world,
        message=query.question, authored_references=refs.model_dump(mode='json', by_alias=True))
    intent = t.SubmittedTurnIntentV3.model_validate(raw_intent)
    action = NativePlanActionV2.model_validate(old.policy.action.model_dump(mode='json', by_alias=True) | {'action_version': 'plan_saved_authored_pages_v2', 'intent': intent.model_dump(mode='json', by_alias=True), 'related_page_catalog': []})
    policy = old.policy.model_copy(update={'action': action, 'native_query_sha256': 'a'*64})
    root = execution('b'*64, policy)
    capture = t.BuildAuthoredReferencesCapturedV1(kind='build_authored_references_captured_v1', event_id=uuid4(),
        sequence=0, references=refs, read_graph_revision=query.authority.revision_id, turn_id=uuid4(),
        conversation_id=uuid4(), attempt=1, submitted_intent_fingerprint=t.submitted_turn_intent_fingerprint_v2(intent))
    settlement = NativePlanGraphQuerySettledV1(event_id=uuid4(), sequence=1, started_event_id=uuid4(), query=query)
    grant = BuildAuthoredReferenceAuthorizedV2(event_id=uuid4(), sequence=2, capture_event_id=capture.event_id,
        node_id=ref.node_id, context_receipt_sha256=root.context_receipt_sha256,
        execution_policy_sha256=root.execution_policy_sha256, query_sha256=query.sha256)
    support = read_authored_reference(core, grant, GM)
    assert support.assertion_reads and not support.unavailable_assertion_ids
    read = BuildAuthoredReferenceReadV2(event_id=uuid4(), sequence=3, capture_event_id=capture.event_id,
        authorization_event_id=grant.event_id, node_id=ref.node_id, statement_reads=support.statement_reads,
        assertion_reads=support.assertion_reads, unavailable_statement_ids=support.unavailable_statement_ids,
        unavailable_assertion_ids=support.unavailable_assertion_ids, status=support.status)
    # This provisional execution is not read authority: the full pending-receipt
    # join is tested separately. Here Core and the record owner compare real supports.
    from types import SimpleNamespace
    provisional = SimpleNamespace(policy=policy, context_receipt_sha256=root.context_receipt_sha256,
        execution_policy_sha256=root.execution_policy_sha256, events=[capture, settlement, grant, read])
    validate_native_execution(provisional)
    validate_native_context(query, provisional)
    altered = read.model_copy(update={'assertion_reads': ()})
    provisional.events[-1] = altered
    with pytest.raises(ValueError, match='support inventory'):
        validate_native_context(query, provisional)


def test_sdk_observation_construction_requires_acknowledged_exact_result():
    from uuid import uuid4
    from generationengine.types import DecisionResult
    from application_state.agent_conversation.native_plan_graph_producer import observed_from_sdk_result
    from tests.test_surface_native_execution import execution
    context, record, auth, lifecycle, observed = actual_need_execution()
    prefix = execution(context.context_receipt_sha256, record.policy, [auth, *lifecycle])
    typed = DecisionResult.model_validate_json(observed.result_json)
    produced = observed_from_sdk_result(context, prefix, event_id=observed.event_id, result=typed)
    assert produced == observed
    with pytest.raises(ValueError, match='typed SDK result'):
        observed_from_sdk_result(context, prefix, event_id=uuid4(), result=typed.model_dump())
    incomplete = execution(context.context_receipt_sha256, record.policy, [auth, lifecycle[0]])
    with pytest.raises(ValueError, match='unique settled SDK response'):
        observed_from_sdk_result(context, incomplete, event_id=uuid4(), result=typed)
    complete = execution(context.context_receipt_sha256, record.policy, [auth, *lifecycle, observed])
    with pytest.raises(ValueError, match='unresolved authorization'):
        observed_from_sdk_result(context, complete, event_id=uuid4(), result=typed)


@pytest.mark.parametrize('source_adapter', [{'unique_world': True, 'sources': [('first', '# Synthetic\n')]}], indirect=True)
def test_sdk_result_owner_fences_and_reopens_actual_app_turn(source_adapter, monkeypatch, application_state_dsn):
    from uuid import uuid4
    from application_state.agent_conversation import types as t
    from application_state.agent_conversation.native_plan_graph_need import NativePlanGraphNeedInputV1, canonical_wire
    from application_state.agent_conversation.native_retrieval import NativePlanGraphNeedAuthorizedV1
    from application_state.errors import ApplicationStateConflictError, ApplicationStateValidationError
    from tests.test_surface_native_execution import controller, execution, outcomes
    service, created = _admitted_pending_turn(source_adapter, monkeypatch)
    turn = service.claim_turn(created.world_id, created.conversation_id, created.turn_id,
        expected_revision=created.revision).turn
    context, policy = turn.graph_context_receipt, turn.graph_context_execution.policy
    parent = NativePlanGraphNeedInputV1(pending_query_sha256=t.canonical_sha256(context.native_query),
        admission_sha256=t.canonical_sha256(context.assembled_input), question=policy.action.intent.message,
        dialogue=(), current_work=source_adapter.work.plan_markdown)
    base = controller('plan', policy, semantic=True)
    auth = NativePlanGraphNeedAuthorizedV1.model_validate(base.model_dump(mode='json') | {
        'kind': 'native_plan_graph_need_authorized_v1', 'parent_request_sha256': parent.digest,
        'parent_json': parent.model_dump_json(by_alias=True),
        'envelope_sha256': sha256(canonical_wire(parent, expected_model=base.model)).hexdigest(),
        'input_estimator': context.assembled_input.tokenizer_name,
        'output_token_reserve': context.assembled_input.output_token_reserve})
    from application_state.agent_conversation.native_writer import json_container_count
    from application_state.agent_conversation.plan_authoring import strict_json
    raw = canonical_wire(parent, expected_model=auth.model)
    auth = auth.model_copy(update={'input_tokens': len(raw) + 64 * (1 + json_container_count(strict_json(raw.decode())))})
    with pytest.raises(ApplicationStateValidationError, match='wire differs'):
        service._authorize_plan_graph_need(turn.world_id, turn.conversation_id, turn.turn_id,
            expected_revision=turn.revision, expected_attempt=turn.attempt, authorization=auth, prepared_request=raw + b' ')
    turn, fresh = service._authorize_plan_graph_need(turn.world_id, turn.conversation_id, turn.turn_id,
        expected_revision=turn.revision, expected_attempt=turn.attempt, authorization=auth, prepared_request=raw)
    assert fresh
    lifecycle = outcomes(auth, 1)
    with pytest.raises(ApplicationStateValidationError, match='exact admitted prepared authorization'):
        service.record_provider_outcome(turn.world_id, turn.conversation_id, turn.turn_id,
            expected_revision=turn.revision, expected_attempt=turn.attempt, outcome=lifecycle[0],
            opening_authorization=auth.model_copy(update={'event_id': uuid4()}))
    turn, fresh = service.record_provider_outcome(turn.world_id, turn.conversation_id, turn.turn_id,
        expected_revision=turn.revision, expected_attempt=turn.attempt, outcome=lifecycle[0], opening_authorization=auth)
    assert fresh
    typed = result(answers={'graph_need': ChoiceDecisionAnswer(selected='no_graph')})
    typed = typed.model_copy(update={'observation': typed.observation.model_copy(update={
        'resolved_model': auth.model, 'response_model': auth.model})})
    with pytest.raises(ApplicationStateValidationError, match='unique settled SDK response'):
        service._record_plan_graph_need_result(turn.world_id, turn.conversation_id, turn.turn_id,
            expected_revision=turn.revision, expected_attempt=turn.attempt, event_id=uuid4(), sdk_result=typed)
    assert service.inspect_turn(world_id=turn.world_id, turn_id=turn.turn_id).revision == turn.revision
    turn, fresh = service.record_provider_outcome(turn.world_id, turn.conversation_id, turn.turn_id,
        expected_revision=turn.revision, expected_attempt=turn.attempt, outcome=lifecycle[1])
    assert fresh
    with pytest.raises(ApplicationStateConflictError, match='stale claim'):
        service._record_plan_graph_need_result(turn.world_id, turn.conversation_id, turn.turn_id,
            expected_revision=turn.revision - 1, expected_attempt=turn.attempt, event_id=uuid4(), sdk_result=typed)
    with pytest.raises(ApplicationStateValidationError, match='typed SDK result'):
        service._record_plan_graph_need_result(turn.world_id, turn.conversation_id, turn.turn_id,
            expected_revision=turn.revision, expected_attempt=turn.attempt, event_id=uuid4(), sdk_result=typed.model_dump())
    updated, fresh = service._record_plan_graph_need_result(turn.world_id, turn.conversation_id, turn.turn_id,
        expected_revision=turn.revision, expected_attempt=turn.attempt, event_id=uuid4(), sdk_result=typed)
    assert fresh
    reopened = service.inspect_turn(world_id=turn.world_id, turn_id=turn.turn_id)
    assert reopened.graph_context_execution == updated.graph_context_execution
    assert reopened.graph_context_execution.events[-1].choice == 'no_graph'
    with pytest.raises(ApplicationStateValidationError, match='unresolved authorization'):
        service._record_plan_graph_need_result(turn.world_id, turn.conversation_id, turn.turn_id,
            expected_revision=reopened.revision, expected_attempt=reopened.attempt, event_id=uuid4(), sdk_result=typed)


def test_graph_need_sdk_entry_requires_its_exact_authorization():
    from uuid import uuid4
    from application_state.agent_conversation.native_plan_opening import validate_opening_sdk_entry
    from tests.test_surface_native_execution import execution
    context, record, auth, lifecycle, _ = actual_need_execution()
    prefix = execution(context.context_receipt_sha256, record.policy, [auth])
    validate_opening_sdk_entry(prefix, lifecycle[0], auth)
    with pytest.raises(ValueError, match='exact admitted prepared authorization'):
        validate_opening_sdk_entry(prefix, lifecycle[0], auth.model_copy(update={'event_id': uuid4()}))
    with pytest.raises(ValueError, match='exact admitted prepared authorization'):
        validate_opening_sdk_entry(prefix, lifecycle[0], None)


def test_prepared_graph_authorization_binds_exact_wire_and_accounting():
    from application_state.agent_conversation.native_plan_graph_producer import validate_prepared_authorization
    from application_state.agent_conversation.native_plan_graph_need import canonical_wire
    from application_state.agent_conversation.native_writer import json_container_count
    from application_state.agent_conversation.plan_authoring import strict_json
    from tests.test_surface_native_execution import execution
    context, record, auth, lifecycle, _ = actual_need_execution()
    parent = NativePlanGraphNeedInputV1.model_validate_json(auth.parent_json)
    raw = canonical_wire(parent, expected_model=auth.model)
    auth = auth.model_copy(update={'input_tokens': len(raw) + 64 * (1 + json_container_count(strict_json(raw.decode())))})
    empty = execution(context.context_receipt_sha256, record.policy)
    assert validate_prepared_authorization(context, empty, auth, raw).events == [auth]
    with pytest.raises(ValueError, match='wire differs'):
        validate_prepared_authorization(context, empty, auth, raw + b' ')
    with pytest.raises(ValueError, match='wire accounting'):
        validate_prepared_authorization(context, empty, auth.model_copy(update={'input_tokens': 1}), raw)
    active = execution(context.context_receipt_sha256, record.policy, [auth, *lifecycle])
    with pytest.raises(ValueError, match='first provider attempt'):
        validate_prepared_authorization(context, active, auth, raw)


@pytest.mark.parametrize('source_adapter', [{'unique_world': True, 'sources': [('first', '# Synthetic\n')]}], indirect=True)
def test_actual_sdk_callback_persists_graph_need_result(source_adapter, monkeypatch):
    import asyncio
    import httpx2
    from apps.live_control_server.services.agent_turn_service import _ClaimFence
    from apps.live_control_server.services.plan_graph_need_dispatch import PlanGraphNeedDispatch
    a = source_adapter
    service, created = _admitted_pending_turn(a, monkeypatch)
    turn = service.claim_turn(created.world_id, created.conversation_id, created.turn_id,
        expected_revision=created.revision).turn
    a.turn = turn
    a.fence = _ClaimFence(service, turn)
    a.context_capture = None
    monkeypatch.setattr(a, '_capture_prepared_prompt', lambda *_args, **_kwargs: None)
    dispatch = PlanGraphNeedDispatch(a, dialogue=())
    calls = []
    class Wire(httpx2.AsyncBaseTransport):
        async def handle_async_request(self, request):
            calls.append(request.content)
            return httpx2.Response(200, request=request, json={'model': 'typesafe-ai/jev-1.14.0',
                'answers': {'graph_need': {'type': 'choice', 'choice': 'no_graph', 'confidence': 1,
                    'probabilities': {'require_graph': 0, 'no_graph': 1, 'uncertain': 0}}},
                'usage': {'input_tokens': 10, 'output_tokens': 1}})
    observed = asyncio.run(dispatch.run(transport=Wire(), api_key='synthetic-not-secret'))
    assert len(calls) == 1 and calls[0] == dispatch.prepared.body
    assert observed.choice == 'no_graph'
    reopened = service.inspect_turn(world_id=turn.world_id, turn_id=turn.turn_id)
    assert reopened.graph_context_execution.events[-1] == observed
    assert [event.outcome for event in reopened.graph_context_execution.events if event.kind == 'provider_outcome'] == [
        'sdk_entered', 'response_received']
    with pytest.raises(ValueError, match='one actual authorized SDK dispatch'):
        dispatch.acknowledge(None)
