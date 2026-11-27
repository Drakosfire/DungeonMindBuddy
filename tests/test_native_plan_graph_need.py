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
