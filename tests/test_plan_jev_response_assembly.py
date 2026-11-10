"""Actual native work reconstruction and writer assembly, without APP/DB effects."""
import asyncio
import json
from types import SimpleNamespace as N

import httpx
from openai import AsyncOpenAI
import pytest

from application_state.agent_conversation import types as t
from application_state.agent_conversation.response_prompt import compose_response_prompt
from apps.live_control_server.services.plan_jev_writer import PlanJevWriter, _ordinary_response_selected
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
    assert sent[0]['tools'] == []
    assert 'instructions_sha256' not in json.dumps(sent[0])
    assert 'image_prompt' not in sent[0]['instructions']


def test_rules_guidance_requires_actual_supplied_lookup():
    from apps.live_control_server.services.plan_jev_writer import RULES_INSTRUCTIONS
    plain, _ = staged('plan')
    active, _ = staged('plan', rules=True)
    assert active.instructions == compose_response_prompt(rules_instructions=RULES_INSTRUCTIONS).instructions
    assert plain.instructions != active.instructions


def test_clarify_retains_its_capability_contract_instead_of_ordinary_response():
    writer, record = staged('plan', requested='clarify')
    assert not _ordinary_response_selected(record)
    assert writer.prompt_components is None
    assert 'Ask the specific clarifying question' in writer.instructions


@pytest.mark.parametrize('requested', ['discuss', 'clarify_request', 'plan', 'prepare_image', 'save_page'])
def test_build_dispatch_operation_alone_does_not_grant_ordinary_prompt(requested):
    context, record = component('build', unavailable=True)
    first = controller('build', record.policy)
    selection = build_resolution(record.policy, first, 3, requested=requested)
    # Use the actual closed event type; the work owner validates its resolution.
    record = record.model_copy(update={'events': (selection,)})
    assert _ordinary_response_selected(record) == (requested == 'discuss')


def test_frame_like_objects_cannot_select_a_product_response_contract():
    assert not _ordinary_response_selected(N(policy=N(action=N(surface_id='play')), events=()))


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
    assert _ordinary_response_selected(updated) == (requested == 'discuss')
    assert not _ordinary_response_selected(updated.model_copy(update={'events':(current,current)}))
