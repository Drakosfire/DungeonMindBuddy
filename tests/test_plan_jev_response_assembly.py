"""Actual native work reconstruction and writer assembly, without APP/DB effects."""
import asyncio
import json
from types import SimpleNamespace as N
from uuid import uuid4

import httpx
from openai import AsyncOpenAI
import pytest

from application_state.agent_conversation import types as t
from application_state.agent_conversation.response_prompt import compose_response_prompt
from apps.live_control_server.services.plan_jev_writer import PlanJevWriter, _conversation_response_task
from tests.test_surface_native_context import seal
from tests.test_surface_native_execution import component, controller, decision_prefix, choice, execution, build_resolution
from tests.test_surface_native_writer import work_submission, with_work_selection


def staged(surface, *, requested='discuss', rules=False, current_plan=False):
    if surface == 'plan_current':
        surface, current_plan = 'plan', True
    context, record = component(surface, unavailable=True)
    data = context.model_dump(mode='json', by_alias=True)
    data['assembled_input']['tokenizer_name'] = controller(surface, record.policy).input_estimator
    context = type(context).model_validate_json(json.dumps(seal(data)))
    record = execution(context.context_receipt_sha256, record.policy)
    if current_plan:
        from application_state.agent_conversation.native_execution import NativePlanActionV2
        action = NativePlanActionV2(intent=record.policy.action.intent,
            authoring_capture=None, placement_catalog=None, related_page_catalog=())
        record = execution(context.context_receipt_sha256, record.policy.model_copy(update={'action': action}))
    events, active = decision_prefix(surface, context, record)
    if current_plan:
        from application_state.agent_conversation.native_execution import NativePlanRequestedWorkSelectedV3
        events = [NativePlanRequestedWorkSelectedV3.model_validate(e.model_dump() |
            {'kind': 'plan_requested_work_selected_v3'}) if isinstance(e,t.PlanRequestedWorkSelectedV2) else e
            for e in events]
    if surface == 'plan' and requested != 'discuss':
        events = [e.model_copy(update={'requested_work': requested})
                  if isinstance(e, t.PlanRequestedWorkSelectedV2) else e for e in events]
    if surface == 'build' and requested != 'discuss':
        events = [build_resolution(record.policy, events[0], e.sequence, requested=requested)
                  if isinstance(e, t.BuildRequestedWorkResolutionV1) else e for e in events]
    events.append(choice(context, record, active, len(events), 'finish_retrieval'))
    record = with_work_selection(execution(context.context_receipt_sha256, record.policy, events))
    work = work_submission(context, record)
    if surface == 'play':
        from application_state.agent_conversation.play_graph_authority import play_source_frame
        frame = play_source_frame((t.PlaySourcePayloadV1(source_kind='current_moment',
            locator=t.play_source_locator(context.work_context.play_basis), text='Exact saved Play moment.'),))
        work['work_proof'] = {'source_frame': frame.model_dump(mode='json', by_alias=True),
                              'session_evidence': [], 'dialogue': []}
    turn = N(graph_context_receipt=context, graph_context_execution=record,
             **{k: v for k, v in work.items() if k != 'work_proof'})
    if surface == 'play':
        turn.play_context_receipt = context.work_context.play_basis
    adapter = N(fence=N(turn=turn), budget={'outputReserveTokens': 4096, 'contextLimitTokens': 128000},
                _broker_execution=lambda: record)
    rule_owner = N(frame=lambda: N(ruleset='dnd_2024_srd_5_2_1', supports=(),
                                  lookups=(N(lookup=0, status='no_evidence'),) if rules else ()))
    return PlanJevWriter(adapter, work['work_proof'], rule_owner), record


@pytest.mark.parametrize('surface', ['plan', 'plan_current', 'build', 'play'])
def test_actual_ordinary_writer_uses_compiler_in_actual_sdk_bytes(surface):
    writer, _ = staged(surface)
    assert writer.instructions == compose_response_prompt().instructions
    assert writer.prompt_components == compose_response_prompt().manifest()
    sent = []

    async def run():
        def wire(request):
            sent.append(json.loads(request.content))
            return httpx.Response(200, request=request, json={'id': 'synthetic', 'object': 'response',
                'created_at': 1, 'model': writer.model, 'status': 'completed', 'output': []})
        async with AsyncOpenAI(api_key='synthetic-not-secret', http_client=httpx.AsyncClient(
                transport=httpx.MockTransport(wire))) as client:
            await client.responses.create(model=writer.model, input=writer.messages,
                instructions=writer.instructions, text={'format': writer.output_format}, tools=[], stream=False)
    asyncio.run(run())
    assert len(sent) == 1
    assert sent[0]['instructions'] == compose_response_prompt().instructions
    assert sent[0]['input'] == writer.messages
    assert sent[0]['text']['format'] == writer.output_format
    assert writer.output_format['type'] == 'json_schema'
    assert writer.output_format['strict'] is True
    assert len(sent[0]['input']) == 3
    assert all(message['content'] != 'Return JSON.' for message in sent[0]['input'])
    # Every remaining message is one intact owned frame, with no format-only tail.
    assert all(isinstance(json.loads(message['content']), dict) for message in sent[0]['input'])
    assert sent[0]['tools'] == []
    assert 'instructions_sha256' not in json.dumps(sent[0])
    assert 'image_prompt' not in sent[0]['instructions']


def test_rules_guidance_requires_actual_supplied_lookup():
    from apps.live_control_server.services.plan_jev_writer import RULES_INSTRUCTIONS
    plain, _ = staged('plan')
    active, _ = staged('plan', rules=True)
    assert active.instructions == compose_response_prompt(rules_instructions=RULES_INSTRUCTIONS).instructions
    assert plain.instructions != active.instructions


def test_clarify_uses_only_its_active_task_component():
    writer, record = staged('plan', requested='clarify')
    assert _conversation_response_task(record) == 'clarify'
    assert writer.instructions == compose_response_prompt(task='clarify').instructions
    assert 'image_prompt' not in writer.instructions


@pytest.mark.parametrize('requested', ['discuss', 'clarify_request', 'plan', 'prepare_image', 'save_page'])
def test_build_dispatch_operation_alone_does_not_grant_ordinary_prompt(requested):
    context, record = component('build', unavailable=True)
    first = controller('build', record.policy)
    selection = build_resolution(record.policy, first, 3, requested=requested)
    # Use the actual closed event type; the work owner validates its resolution.
    record = record.model_copy(update={'events': (selection,)})
    assert _conversation_response_task(record) == ('answer' if requested == 'discuss' else 'explain_capability')


def test_frame_like_objects_cannot_select_a_product_response_contract():
    assert not _conversation_response_task(N(policy=N(action=N(surface_id='play')), events=()))


def test_current_plan_constructor_uses_its_reconstructed_native_work():
    writer, _ = staged('plan', current_plan=True)
    assert writer.instructions == compose_response_prompt().instructions
    assert writer.provider_work['requested_work'] == 'discuss'


@pytest.mark.parametrize('surface', ['plan', 'build', 'play'])
def test_ordinary_assembly_does_not_construct_legacy_instructions_first(surface, monkeypatch):
    from apps.live_control_server.services import plan_jev_writer
    monkeypatch.setattr(plan_jev_writer, 'INSTRUCTIONS', None)
    writer, _ = staged(surface)
    assert writer.instructions == compose_response_prompt().instructions


@pytest.mark.parametrize('requested', ['discuss', 'clarify', 'review_connected_page'])
def test_current_native_plan_owner_requires_its_actual_work_selection(requested):
    from application_state.agent_conversation.native_execution import NativePlanActionV2, NativePlanRequestedWorkSelectedV3
    _, record = staged('plan')
    action = NativePlanActionV2(intent=record.policy.action.intent,
        authoring_capture=None, placement_catalog=None, related_page_catalog=())
    selection = next(e for e in record.events if isinstance(e, t.PlanRequestedWorkSelectedV2))
    data = selection.model_dump(); data.update(kind='plan_requested_work_selected_v3', requested_work=requested)
    current = NativePlanRequestedWorkSelectedV3.model_validate(data)
    updated = record.model_copy(update={'policy':record.policy.model_copy(update={'action':action}), 'events':(current,)})
    assert _conversation_response_task(updated) == {'discuss': 'answer', 'clarify': 'clarify'}.get(requested)
    assert not _conversation_response_task(updated.model_copy(update={'events':(current,current)}))


@pytest.mark.parametrize('requested', ['clarify_request', 'plan', 'prepare_image', 'save_page'])
def test_actual_build_limit_explanations_do_not_receive_image_or_authoring_instructions(requested, monkeypatch):
    from apps.live_control_server.services import plan_jev_writer
    monkeypatch.setattr(plan_jev_writer, 'INSTRUCTIONS', None)
    writer, record = staged('build', requested=requested)
    assert _conversation_response_task(record) == 'explain_capability'
    assert writer.instructions == compose_response_prompt(task='explain_capability').instructions
    assert 'image_prompt' not in writer.instructions and 'authoring' not in writer.instructions


def test_actual_plan_clarification_skips_legacy_assembly(monkeypatch):
    from apps.live_control_server.services import plan_jev_writer
    monkeypatch.setattr(plan_jev_writer, 'INSTRUCTIONS', None)
    writer, _ = staged('plan', requested='clarify', current_plan=True)
    assert writer.instructions == compose_response_prompt(task='clarify').instructions


def test_reviewed_task_requires_actual_scoped_action_instead_of_frame_words():
    from application_state.agent_conversation.reviewed_action import ReviewedStepBindingV3
    _, record = staged('build')
    step = uuid4()
    binding = ReviewedStepBindingV3(reference={'conversation_id':uuid4(), 'source_turn_id':uuid4(), 'command_id':uuid4()},
        step_id=step, kind='discuss', source_answer_sha256='a'*64, dispatch_sha256='b'*64,
        authored_references=None, scope={'task': {'step_id':step, 'kind':'discuss', 'text':'Discuss the lamp location.'},
            'objective_context':'Choose a location, then draft later.', 'sibling_context': ()})
    intent = record.policy.action.intent.model_copy(update={'reviewed_step':binding, 'build_draft_context_sha256':'c'*64})
    selected = t.BuildReviewedActionSelectionV1(kind='build_reviewed_action_selected_v1',event_id=uuid4(),sequence=0,
        intent=intent,operation='answer_from_sources',broker_operation_id='selected-discussion',
        capability_sha256=None,arguments_sha256='d'*64)
    record = record.model_copy(update={'policy':record.policy.model_copy(update={
        'action':record.policy.action.model_copy(update={'intent':intent})}), 'events':(selected,)})
    # Selector-only proof; actual scoped APP admission is separately exercised by
    # the existing reviewed-step boundary tests, not granted by this fixture.
    assert _conversation_response_task(record) == 'scoped_discussion'
    assert not _conversation_response_task(N(reviewed_task=binding.scope))


@pytest.mark.parametrize('surface', ['plan', 'plan_current', 'build', 'play'])
def test_native_response_schema_does_not_advertise_image_preparation(surface):
    from jsonschema import Draft202012Validator, ValidationError
    writer, _ = staged(surface)
    schema = writer.output_format['schema']
    assert writer.output_format['name'] == 'surface_native_evidence_selectors_v2'
    assert 'image_prompt' not in json.dumps(schema)
    candidate = {'schema': schema['properties']['schema']['const'],
        'answer_segments': [{'kind': 'proposal', 'label': 'invented_idea', 'text': 'A requested idea.'}],
        'limitations': [], 'requested_detail_gaps': []}
    Draft202012Validator(schema).validate(candidate)
    candidate['answer_segments'][0]['label'] = 'image_prompt'
    with pytest.raises(ValidationError):
        Draft202012Validator(schema).validate(candidate)
