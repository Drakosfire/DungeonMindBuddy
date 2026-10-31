"""Admitted Build source crosses the real adapter/host IPC without inference."""
from tests.page_fixtures import create_page_fixture, save_page
from apps.live_control_server.services.workspace_document_registry import get_workspace_document
from dataclasses import replace
import hashlib
import json
import os
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from apps.live_control_server.routes import agent
from apps.live_control_server.services.agent_turn_service import execute_agent_turn
from apps.live_control_server.services.hermes_agent_runtime import HermesAgentRuntimeAdapter
from apps.live_control_server.services.hermes_graph_agent_contract import (
    HermesGraphAgentTurnResult, deserialize_hermes_graph_agent_turn_request,
    serialize_hermes_graph_agent_turn_request, serialize_hermes_graph_agent_turn_result,
    encode_json_wire, decode_json_wire,
)
from apps.live_control_server.services.hermes_graph_agent_host import HermesGraphAgentHost
from apps.live_control_server.services.hermes_session_store import HermesSessionPointerStore
from apps.live_control_server.services.workspace_document_registry import (get_workspace_document_snapshot)
from tests.test_agent_build_surface_context import request
from tests.test_hermes_graph_agent_contract import _request


@pytest.fixture
def source(tmp_path, monkeypatch, application_state_dsn):
    (tmp_path / 'corpus/elderwyld-markdown').mkdir(parents=True)
    record = create_page_fixture(tmp_path, title='Synthetic Guard — 羊', campaign_id='elderwyld', world_id='elderwyld',
        kind='worldbuilding_source', source_domain='worldbuilding', document_class='lore', authority_state='draft', visibility_state='internal')
    record = save_page(tmp_path, record.document_id, '# Guard\n' + 'Mirathorn — 羊 guards protect the city.\n' * 350)
    get_workspace_document(tmp_path, record.document_id)
    monkeypatch.setattr(agent, '_managed_world_root', lambda: tmp_path)
    return get_workspace_document_snapshot(tmp_path, record.document_id)


def saved_work_worker(request_queue, response_queue):
    """Actual process seam, no runtime/model import or network."""
    response_queue.put(encode_json_wire({'type': 'ready', 'pid': os.getpid()}))
    while True:
        message = decode_json_wire(request_queue.get())
        if message['type'] == 'shutdown':
            response_queue.put(encode_json_wire({'type': 'shutdown_ack', 'pid': os.getpid()}))
            return
        if message['type'] != 'execute':
            continue
        rid = message['requestId']
        response_queue.put(encode_json_wire({'type': 'accepted', 'requestId': rid, 'pid': os.getpid()}))
        proceed = decode_json_wire(request_queue.get())
        if proceed['type'] == 'shutdown':
            return
        assert proceed['type'] == 'proceed' and proceed['requestId'] == rid
        value = deserialize_hermes_graph_agent_turn_request(message['payload'])
        body = json.loads(value.question)
        saved = body['saved_source']
        witness = {key: saved[key] for key in ('document_id', 'registry_revision', 'content_sha256', 'world_id')}
        witness.update(content_sha256_observed=hashlib.sha256(saved['content'].encode()).hexdigest(),
            user_question=body['user_question'], input_kind=value.input_kind,
            plan_continuity_turn=value.plan_continuity_turn,
            capability_mode=value.capability_policy.mode, provider_calls=0)
        result = HermesGraphAgentTurnResult(status='ok', final_response=json.dumps(witness),
            messages=[], hermes_session_id='synthetic-build-worker', tool_events=[])
        response_queue.put(encode_json_wire({'type': 'result', 'requestId': rid,
            'payload': serialize_hermes_graph_agent_turn_result(result)}))


def test_admitted_large_unicode_source_reaches_real_adapter_and_worker(source, tmp_path):
    assert len(source.markdown) > 8000
    host = HermesGraphAgentHost(worker_target=saved_work_worker)
    runtime = HermesAgentRuntimeAdapter(host_factory=lambda: host)
    try:
        response = execute_agent_turn(request(source), root=tmp_path,
            pointer_store=HermesSessionPointerStore(tmp_path / 'pointers'),
            owner_resolver=lambda _: dict(kind='world', id='elderwyld', name='Elderwyld'),
            work_resolver=agent._work_resolver,
            graph_resolver=lambda *_: pytest.fail('implicit Graph read'), runtime=runtime)
        witness = json.loads(response.answer.text)
        assert witness == dict(document_id=source.record.document_id,
            registry_revision=source.loaded_revision, content_sha256=source.content_sha256,
            content_sha256_observed=source.content_sha256, world_id='elderwyld',
            user_question='Who operates the radio?', input_kind='server_assembled_saved_work',
            plan_continuity_turn=False, capability_mode='conversation_only', provider_calls=0)
        assert host.worker_pid is not None
    finally:
        assert host.shutdown()


@pytest.mark.parametrize('bad', [None, True, 3, [], {}, 'plan', 'server_saved_work'])
def test_invalid_internal_discriminator_rejects_both_directions(bad):
    with pytest.raises(ValueError, match='inputKind'):
        serialize_hermes_graph_agent_turn_request(replace(_request(), input_kind=bad))
    wire = serialize_hermes_graph_agent_turn_request(_request())
    wire['inputKind'] = bad
    with pytest.raises(ValueError, match='inputKind'):
        deserialize_hermes_graph_agent_turn_request(wire)


def test_ordinary_and_plan_messages_round_trip_without_character_clipping():
    default = serialize_hermes_graph_agent_turn_request(_request())
    assert deserialize_hermes_graph_agent_turn_request(default).input_kind == 'ordinary_question'
    default.pop('inputKind')
    assert deserialize_hermes_graph_agent_turn_request(default).input_kind == 'ordinary_question'
    ordinary = replace(_request(), question='x' * 12000)
    assert deserialize_hermes_graph_agent_turn_request(
        serialize_hermes_graph_agent_turn_request(ordinary)).question == ordinary.question
    default['question'] = ordinary.question
    assert deserialize_hermes_graph_agent_turn_request(default).question == ordinary.question
    plan = replace(_request(), question='x' * 12000, plan_continuity_turn=True)
    restored = deserialize_hermes_graph_agent_turn_request(serialize_hermes_graph_agent_turn_request(plan))
    assert restored.question == plan.question and restored.plan_continuity_turn is True
    assert restored.input_kind == 'ordinary_question'


def test_public_input_preserves_message_but_cannot_inject_discriminator(source):
    message = 'x' * 12000
    assert request(source, message=message).message == message
    with pytest.raises(ValidationError):
        request(source, input_kind='server_assembled_saved_work')


def test_wrong_source_pin_rejects_before_actual_host(source, tmp_path):
    from apps.live_control_server.services.agent_turn_service import AgentTurnServiceError
    body = request(source)
    body = body.model_copy(update={'primary_work': body.primary_work.model_copy(
        update={'expected_content_sha256': '0' * 64})})
    class NoRuntime:
        def run(self, invocation):
            pytest.fail('source admission must reject before runtime')
    with pytest.raises(AgentTurnServiceError):
        execute_agent_turn(body, root=tmp_path, pointer_store=HermesSessionPointerStore(tmp_path / 'pointers'),
            owner_resolver=lambda _: dict(kind='world', id='elderwyld', name='Elderwyld'),
            work_resolver=agent._work_resolver, graph_resolver=lambda *_: pytest.fail('Graph read'), runtime=NoRuntime())


def test_encoded_unicode_wire_overflow_stops_before_request_dispatch():
    host = HermesGraphAgentHost(worker_target=saved_work_worker)
    try:
        value = replace(_request(), question='🐐' * 70000, input_kind='server_assembled_saved_work')
        phases = []
        result = host.execute(value, on_host_phase=phases.append)
        assert result.status == 'error' and result.error_code == 'hermes_worker_protocol_error'
        assert result.error_message == 'Hermes graph-agent request wire encoding failed.'
        assert any(phase['name'] == 'host_request_wire_encode' and phase['status'] == 'error' for phase in phases)
        assert not any(phase['name'] == 'host_request_queue_put' for phase in phases)
    finally:
        assert host.shutdown()


def test_final_provider_envelope_budget_still_rejects_large_saved_input_before_authorization():
    from apps.live_control_server.services.hermes_graph_agent import _request_budget_guard
    request_value = replace(_request(), question='羊' * 9000, input_kind='server_assembled_saved_work')
    restored = deserialize_hermes_graph_agent_turn_request(serialize_hermes_graph_agent_turn_request(request_value))
    payload = {'model': 'synthetic-model', 'messages': [{'role': 'user', 'content': restored.question}],
               'max_completion_tokens': 128}
    text = json.dumps(payload, ensure_ascii=False)
    calls = []
    guard = _request_budget_guard(dict(provider='openai-api', model='synthetic-model', apiMode='chat_completions',
        estimator='utf8_json_bytes_plus_64_per_node_v1', contextLimitTokens=10000, outputReserveTokens=128),
        on_provider_authorization=lambda view: calls.append(view) or True)
    assert guard(SimpleNamespace(provider='openai-api', model='synthetic-model', api_mode='chat_completions',
        payload_json=text, payload_utf8_bytes=len(text.encode()))) is False
    assert not calls
