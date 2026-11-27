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
from tests.test_native_corpus_source_access import lane as native_lane


def staged(surface, *, requested='discuss', rules=False, current_plan=False, dialogue=(), anchored=False):
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
    if surface == 'build' and anchored:
        from application_state.agent_conversation.build_intentional_response import resolution_for
        events = [e.model_copy(update={'resolution': resolution_for(record.policy, 'discuss', source_scope='anchored')})
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
    return PlanJevWriter(adapter, work['work_proof'], rule_owner, dialogue=dialogue), record


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
    assert 'contract above' not in active.instructions
    assert 'BASE_OR_NULL' not in active.instructions
    assert '{"kind":"rules_answer"' not in active.instructions
    assert 'supplied Rules supports' in active.instructions
    assert 'applicability' in active.instructions
    assert 'reading order' in active.instructions
    assert active.output_format['type'] == 'json_schema'
    assert active.output_format['strict'] is True
    # The capability guidance must not leak into an ordinary no-lookup response.
    assert plain.instructions == compose_response_prompt().instructions


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


def test_variant_approval_uses_its_own_workflow_guidance():
    _, record = component('build', unavailable=True)
    first = controller('build', record.policy)
    selection = build_resolution(record.policy, first, 3, requested='review_variant_approval')
    record = record.model_copy(update={'events': (selection,)})

    task = _conversation_response_task(record)
    assert task == 'variant_approval'
    assert 'Open in Combat' in compose_response_prompt(task=task).instructions
    assert 'Open in Combat' not in compose_response_prompt().instructions


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

def test_build_writer_keeps_prior_gm_decisions_in_provider_messages():
    dialogue = (
        {"role": "user", "content": '{"ruleset":"x","lookups":[],"supports":[]}'},
        {"role": "assistant", "content": "We could negotiate a truce."},
        {"role": "user", "content": "Use the truce. Show them standing down first."},
    )
    writer, _ = staged("build", dialogue=dialogue)
    baseline, _ = staged("build")
    assert [
        {"role": message["role"], "content": json.loads(message["content"])["conversation"]}
        for message in writer.messages[:3]
    ] == list(dialogue)
    assert writer.messages[3:] == baseline.messages
    assert all(set(message) == {"role", "content"} for message in writer.messages[:3])
    assert dialogue[0]["content"] not in json.dumps(writer.output_format)
    from apps.live_control_server.services.plan_jev_writer import PlanWriterProvider

    call = N(model=writer.model, user_prompt=json.dumps(writer.messages),
             system_prompt=writer.instructions, temperature=None,
             max_output_tokens=None, reasoning_effort=None, json_object=False,
             json_schema=writer.output_format["schema"],
             schema_name=writer.output_format["name"])
    provider = object.__new__(PlanWriterProvider)
    assert provider._request_kwargs(call)["input"] == writer.messages


def test_build_status_guidance_reaches_the_actual_sdk_without_changing_plan_or_play():
    build, record = staged('build')
    assert _conversation_response_task(record) == 'build_discussion'
    expected = compose_response_prompt(task='build_discussion', build_source_status=True)
    assert build.instructions == expected.instructions
    assert build.prompt_components == expected.manifest()
    for surface in ('plan', 'play'):
        other, _ = staged(surface)
        assert 'next-session pickup or resume instruction' not in other.instructions
    sent = []

    async def run():
        def wire(request):
            sent.append(json.loads(request.content))
            return httpx.Response(200, request=request, json={'id': 'synthetic', 'object': 'response',
                'created_at': 1, 'model': build.model, 'status': 'completed', 'output': []})
        async with AsyncOpenAI(api_key='synthetic-not-secret', http_client=httpx.AsyncClient(
                transport=httpx.MockTransport(wire))) as client:
            await client.responses.create(model=build.model, input=build.messages,
                instructions=build.instructions, text={'format': build.output_format}, tools=[], stream=False)
    asyncio.run(run())
    assert len(sent) == 1
    assert sent[0]['instructions'] == expected.instructions
    assert 'next-session pickup or resume instruction' in sent[0]['instructions']
    assert sent[0]['input'] == build.messages


def test_different_source_guidance_reaches_actual_build_writer():
    writer, _ = staged('build')
    assert 'cite a source established as different' in writer.instructions
    assert 'does not establish a different source, say so' in writer.instructions
    assert 'comparison is requested' in writer.instructions
    evidence = next(c for c in writer.prompt_components['components'] if c['name'] == 'evidence')
    assert evidence['version'] == '2'
    assert evidence['text'] in writer.instructions
    from apps.live_control_server.services.plan_jev_writer import PlanWriterProvider
    call = N(model=writer.model, user_prompt=json.dumps(writer.messages),
             system_prompt=writer.instructions, temperature=None, max_output_tokens=None,
             reasoning_effort=None, json_object=False, json_schema=writer.output_format['schema'],
             schema_name=writer.output_format['name'])
    request = object.__new__(PlanWriterProvider)._request_kwargs(call)
    assert evidence['text'] in request['instructions']


def test_different_source_guidance_reaches_pending_build_writer(monkeypatch):
    from tests.test_build_source_free_protocol import pending_writer_runtime_case
    from application_state.agent_conversation.rules_authority_plan_packet import PlanRulesEvidenceFrameV1
    from application_state.agent_conversation.response_prompt import DIFFERENT_SOURCE_GUIDANCE
    from apps.live_control_server.services import build_jev_dispatch
    # This retained fixture was recorded under the historical controller name.
    monkeypatch.setattr(build_jev_dispatch, 'MODEL', 'jev-1.14.0')
    with pending_writer_runtime_case(monkeypatch) as (_, adapter, selector, _):
        selector.settle_empty()
        rules = N(frame=lambda: PlanRulesEvidenceFrameV1(schema='dmb_plan_rules_evidence_v1',
            ruleset='synthetic', lookups=(), supports=()), authoring=None)
        writer = PlanJevWriter(adapter, {}, rules)
        assert writer.shared and _conversation_response_task(adapter._broker_execution()) is None
        assert DIFFERENT_SOURCE_GUIDANCE in writer.instructions


@pytest.mark.parametrize(('surface', 'requested', 'expected'), [
    ('build', 'discuss', 'medium'),
    ('build', 'clarify_request', 'low'),
    ('plan', 'discuss', 'low'),
    ('play', 'discuss', 'low'),
])
def test_writer_passes_scoped_effort_to_generation_boundary(monkeypatch, surface, requested, expected):
    """Exercise actual writer assembly and TextRequest without a provider call."""
    import generationengine

    writer, _ = staged(surface, requested=requested)
    sent = []

    class StopBeforeProvider(Exception):
        pass

    class CaptureClient:
        def __init__(self, **kwargs):
            pass

        async def generate_structured(self, request):
            sent.append(request)
            raise StopBeforeProvider()

        async def aclose(self):
            pass

    writer.adapter.context_capture = N(observe=lambda event: None, provider_usage=lambda calls: None)
    monkeypatch.setattr(writer, 'observe', lambda *args, **kwargs: None)
    monkeypatch.setattr(writer, 'capture_draft', lambda *args, **kwargs: None)
    monkeypatch.setattr(generationengine, 'GenerationClient', CaptureClient)
    with pytest.raises(StopBeforeProvider):
        asyncio.run(writer.run(api_key='synthetic-not-secret'))
    assert len(sent) == 1
    assert sent[0].reasoning_effort == expected


@pytest.mark.parametrize(('default', 'shared', 'work', 'rules_active', 'authoring', 'expected'), [
    ('low', True, {'build_work': {'requested_work': {'requested_work': 'discuss',
        'operation': 'answer_from_sources', 'barrier': None}}}, False, False, 'medium'),
    ('none', True, {'build_work': {'requested_work': {'requested_work': 'discuss',
        'operation': 'answer_from_sources', 'barrier': None}}}, False, False, 'none'),
    ('medium', True, {'build_work': {'requested_work': {'requested_work': 'discuss',
        'operation': 'answer_from_sources', 'barrier': None}}}, False, False, 'medium'),
    ('low', False, {'build_work': {'requested_work': {'requested_work': 'discuss',
        'operation': 'answer_from_sources', 'barrier': None}}}, False, False, 'low'),
    ('low', True, {'build_work': {'requested_work': {'requested_work': 'discuss',
        'operation': 'answer_from_sources', 'barrier': None}}}, True, False, 'low'),
    ('low', True, {'build_work': {'requested_work': {'requested_work': 'discuss',
        'operation': 'answer_from_sources', 'barrier': None}}}, False, True, 'low'),
    ('low', True, {'build_work': {'requested_work': {'requested_work': 'discuss',
        'operation': 'answer_from_sources', 'barrier': 'unavailable'}}}, False, False, 'low'),
    ('low', True, {'build_work': {'requested_work': {'requested_work': 'discuss',
        'operation': 'answer_from_sources'}}}, False, False, 'low'),
    ('low', True, {'build_work': {'requested_work': {'requested_work': 'save_page',
        'operation': 'answer_from_sources', 'barrier': None}}}, False, False, 'low'),
    ('low', True, None, False, False, 'low'),
])
def test_discussion_effort_preserves_other_work(default, shared, work, rules_active, authoring, expected):
    from apps.live_control_server.services.plan_jev_writer import _discussion_reasoning_effort

    assert _discussion_reasoning_effort(default, shared=shared, provider_work=work,
        rules_active=rules_active, authoring=authoring) == expected


@pytest.mark.parametrize('family', ['body', 'statement', 'assertion'])
def test_supplied_native_evidence_disables_discussion_only_shortcut(family):
    from application_state.agent_conversation.plan_writer_output_schema import has_native_citable_evidence
    frame = {'native_body_evidence': {'excerpts': []}, 'native_statements': {'statements': []},
             'native_assertions': {'assertions': []}}
    assert not has_native_citable_evidence(frame)
    group, key = {'body': ('native_body_evidence', 'excerpts'),
                  'statement': ('native_statements', 'statements'),
                  'assertion': ('native_assertions', 'assertions')}[family]
    frame[group][key] = [{}]
    assert has_native_citable_evidence(frame)
    frame['native_assertions'] = None
    if family == 'assertion':
        assert not has_native_citable_evidence(frame)


def test_actual_anchored_writer_exposes_only_supplied_native_body_selector(monkeypatch):
    """Exercise the real schema and TextRequest assembly without a provider."""
    import generationengine
    from application_state.agent_conversation import native_writer
    from jsonschema import Draft202012Validator

    original = native_writer.model_frame
    def with_admitted_body(*args, **kwargs):
        frame = original(*args, **kwargs)
        frame['native_body_evidence']['excerpts'] = [{
            'excerpt_handle': 'host-only-original', 'source_name': 'Selected source',
            'section_title': 'A section', 'extent_kind': 'section', 'line_start': 1,
            'line_end': 1, 'campaign_scope': 'unestablished', 'session_scope': 'unestablished',
            'text': 'The supplied fixture supports this fact.',
        }]
        return frame
    monkeypatch.setattr(native_writer, 'model_frame', with_admitted_body)
    writer, _ = staged('build', anchored=True)
    sent = []
    class StopBeforeProvider(Exception): pass
    class CaptureClient:
        def __init__(self, **kwargs): pass
        async def generate_structured(self, request):
            sent.append(request); raise StopBeforeProvider()
        async def aclose(self): pass
    writer.adapter.context_capture = N(observe=lambda event: None, provider_usage=lambda calls: None)
    monkeypatch.setattr(writer, 'observe', lambda *args, **kwargs: None)
    monkeypatch.setattr(writer, 'capture_draft', lambda *args, **kwargs: None)
    monkeypatch.setattr(generationengine, 'GenerationClient', CaptureClient)
    with pytest.raises(StopBeforeProvider):
        asyncio.run(writer.run(api_key='synthetic-not-secret'))
    assert len(sent) == 1
    assert sent[0].schema_name != 'surface_native_evidence_selectors_v7'
    validator = Draft202012Validator(sent[0].json_schema['properties']['answer_segments']['items'])
    assert validator.is_valid({'kind': 'native_body_claim', 'text': 'Supported.', 'excerpt_handles': ['body0']})
    assert not validator.is_valid({'kind': 'native_body_claim', 'text': 'Fabricated.', 'excerpt_handles': ['body1']})


def test_actual_anchored_writer_keeps_discussion_only_without_native_evidence():
    from jsonschema import Draft202012Validator
    writer, _ = staged('build', anchored=True)
    assert writer.output_format['name'] == 'build_reply'
    items = writer.output_format['schema']['properties']['answer_segments']['items']
    validator = Draft202012Validator(items)
    assert validator.is_valid({'kind': 'discussion', 'text': 'A creative idea.'})
    assert not validator.is_valid({'kind': 'native_body_claim', 'text': 'Unsupported.', 'excerpt_handles': ['body0']})


@pytest.mark.parametrize(('group', 'field', 'handle', 'kind', 'selector'), [
    ('native_statements', 'statements', 'statement_handle', 'native_statement_report', 'statement_handles'),
    ('native_assertions', 'assertions', 'assertion_handle', 'native_assertion_claim', 'assertion_handles'),
])
def test_native_statement_and_assertion_formats_only_offer_supplied_handles(group, field, handle, kind, selector):
    from jsonschema import Draft202012Validator
    from application_state.agent_conversation.build_primary_context import NATIVE_WORK_SCHEMA
    from application_state.agent_conversation.native_writer import SCHEMA
    from application_state.agent_conversation.plan_writer_output_schema import native_output_format
    from application_state.agent_conversation.surface_evidence_answer import ASSERTION_POLICY
    from tests.test_plan_writer_output_schema import rules

    evidence = {'schema': SCHEMA, 'answer_policy': ASSERTION_POLICY,
                'native_body_evidence': {'excerpts': []}, 'native_statements': {'statements': []},
                'native_assertions': {'assertions': []}}
    evidence[group][field] = [{handle: 'offered0'}]
    work = {'schema': NATIVE_WORK_SCHEMA, 'artifact_under_edit': {'sections': []},
            'working_draft_context': {'record_id': '4c63e929-fcec-4d8a-b787-4f908b3ce857'}}
    fmt = native_output_format(evidence, rules(), work, build_local=True, format_version=2)
    validator = Draft202012Validator(fmt['schema']['properties']['answer_segments']['items'])
    assert validator.is_valid({'kind': kind, 'text': 'Supported.', selector: ['offered0']})
    assert not validator.is_valid({'kind': kind, 'text': 'Unsupported.', selector: ['unoffered']})
    historical = native_output_format(evidence, rules(), work, build_local=True, format_version=7)
    old = Draft202012Validator(historical['schema']['properties']['answer_segments']['items'])
    assert old.is_valid({'kind': 'discussion', 'text': 'Historical discussion.'})
    assert not old.is_valid({'kind': kind, 'text': 'Supported.', selector: ['offered0']})


def test_anchored_actual_native_read_can_bind_only_its_offered_citation(native_lane, monkeypatch):
    from jsonschema import Draft202012Validator
    from application_state.agent_conversation.build_intentional_response import resolution_for
    from application_state.agent_conversation.native_completion import normalize_output
    from application_state.agent_conversation.native_writer import model_input_frame
    from tests.test_surface_native_writer import body_case
    from tests import test_surface_native_completion as completion

    context, record, read = body_case('build', native_lane)
    events = [e.model_copy(update={'resolution': resolution_for(record.policy, 'discuss', source_scope='anchored')})
              if isinstance(e, t.BuildRequestedWorkResolutionV1) else e for e in record.events]
    record = execution(context.context_receipt_sha256, record.policy, events)
    work = work_submission(context, record)
    turn = N(graph_context_receipt=context, graph_context_execution=record,
             **{k: v for k, v in work.items() if k != 'work_proof'})
    adapter = N(fence=N(turn=turn), budget={'outputReserveTokens': 4096, 'contextLimitTokens': 128000},
                _broker_execution=lambda: record)
    rules = N(frame=lambda: N(ruleset='dnd_2024_srd_5_2_1', supports=(), lookups=()))
    writer = PlanJevWriter(adapter, work['work_proof'], rules)
    assert writer.output_format['name'] != 'surface_native_evidence_selectors_v7'
    items = writer.output_format['schema']['properties']['answer_segments']['items']
    candidate = {'kind': 'native_body_claim', 'text': 'The source supports this.', 'excerpt_handles': ['body0']}
    assert Draft202012Validator(items).is_valid(candidate)
    monkeypatch.setattr(completion, 'model_frame', model_input_frame)
    stored, auth, proof = completion.producing_case(context, record, completion.answer([candidate]))
    result = normalize_output(context, stored, auth, **proof)
    assert len(result.native_body_citations) == 1
    assert result.native_body_citations[0].read_event_id == read.event_id
    bad = candidate | {'excerpt_handles': ['body999']}
    assert not Draft202012Validator(items).is_valid(bad)
    stored, auth, proof = completion.producing_case(context, record, completion.answer([bad]))
    with pytest.raises(ValueError, match='excerpt selections'):
        normalize_output(context, stored, auth, **proof)
