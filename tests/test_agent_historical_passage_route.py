import asyncio
from hashlib import sha256
from types import SimpleNamespace
from uuid import uuid4
from urllib.parse import urlencode

import httpx
import pytest
from fastapi import FastAPI

from application_state.agent_conversation.context_trace import TraceSourcePassage
from application_state.errors import ApplicationStateNotFoundError
from apps.live_control_server.routes import agent


@pytest.fixture
def passage_api(monkeypatch):
    token = 'historical-passage-test-token-' * 2
    monkeypatch.setenv('DMB_AGENT_GRAPH_AUTH_MODE', 'local_operator')
    monkeypatch.setenv('DMB_AGENT_GRAPH_AUTH_ENVIRONMENT', 'local')
    monkeypatch.setenv('DMB_AGENT_GRAPH_LOCAL_OPERATOR_TOKEN', token)
    text = 'Captured 🦉 story.'
    ref = dict(world_id='world-one', conversation_id=str(uuid4()), turn_id=str(uuid4()),
               trace_id=str(uuid4()), source_read_event_id=str(uuid4()), attempt=1,
               source_read_id='read/a ?&=🦉', content_sha256=sha256(text.encode()).hexdigest())
    passage = TraceSourcePassage(sequence=0, elapsed_ms=1, source_read_event_id=ref['source_read_event_id'],
        read_call_id=uuid4(), world_id=ref['world_id'], graph_revision='revision', source_read_id=ref['source_read_id'],
        anchor_id='anchor', evidence_ref_id='evidence', source_artifact_id='source', source_revision_id='revision',
        outcome='enough', returned_chars=len(text), content_sha256=ref['content_sha256'], text=text)
    calls = []
    state = SimpleNamespace(passage=passage, error=None)

    def read(reference):
        calls.append(reference)
        if state.error:
            raise state.error
        return state.passage

    monkeypatch.setattr(agent, '_verified_world_id', lambda value: value)
    monkeypatch.setattr(agent, '_conversation_service', lambda request: SimpleNamespace(read_historical_source_passage=read))
    app = FastAPI()
    app.include_router(agent.router, prefix='/api/live')

    async def get(*, query=None, authorized=True, turn=None):
        q = urlencode({key: ref[key] for key in ['conversation_id', 'attempt', 'source_read_id', 'content_sha256']}) if query is None else query
        path = f"/api/live/agent/worlds/{ref['world_id']}/conversation/turns/{turn or ref['turn_id']}/context-trace/{ref['trace_id']}/source-passages/{ref['source_read_event_id']}"
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=('127.0.0.1', 1234)), base_url='http://test') as client:
            return await client.get(path + '?' + q, headers={'Authorization': f'Bearer {token}'} if authorized else {})

    return SimpleNamespace(ref=ref, state=state, calls=calls, get=get)


def test_exact_unicode_capture_only_and_no_store(passage_api):
    response = asyncio.run(passage_api.get())
    assert response.status_code == 200
    assert set(response.json()) == {'schema', 'reference', 'passage'}
    assert response.json()['passage'] == passage_api.state.passage.model_dump(mode='json')
    assert passage_api.calls[0].source_read_id == 'read/a ?&=🦉'
    assert response.headers['cache-control'] == 'no-store'
    assert len(response.content) <= 65536


def test_authentication_precedes_invalid_selector_and_storage(passage_api):
    response = asyncio.run(passage_api.get(authorized=False, query='unknown=x', turn='invalid'))
    assert response.status_code == 401
    assert not passage_api.calls


@pytest.mark.parametrize('kind', ['duplicate', 'unknown', 'missing', 'attempt', 'digest', 'read', 'uuid', 'path'])
def test_invalid_selectors_never_touch_store(passage_api, kind):
    q = {key: str(passage_api.ref[key]) for key in ['conversation_id', 'attempt', 'source_read_id', 'content_sha256']}
    if kind == 'unknown': q['unknown'] = 'x'
    if kind == 'missing': q.pop('source_read_id')
    if kind == 'attempt': q['attempt'] = '01'
    if kind == 'digest': q['content_sha256'] = 'A' * 64
    if kind == 'read': q['source_read_id'] = 'x' * 129
    if kind == 'uuid': q['conversation_id'] = q['conversation_id'].replace('-', '')
    query = urlencode(q) + ('&attempt=1' if kind == 'duplicate' else '')
    response = asyncio.run(passage_api.get(query=query, turn='not-a-uuid' if kind == 'path' else None))
    assert response.status_code == 422
    assert not passage_api.calls


def test_missing_or_foreign_capture_is_not_replaced(passage_api):
    passage_api.state.error = ApplicationStateNotFoundError('secret foreign scope')
    response = asyncio.run(passage_api.get())
    assert response.status_code == 404
    assert 'secret' not in response.text
    assert 'passage' not in response.json()


def test_returned_binding_is_validated_again(passage_api):
    passage_api.state.passage = passage_api.state.passage.model_copy(update={'world_id': 'foreign'})
    response = asyncio.run(passage_api.get())
    assert response.status_code == 409
    assert 'foreign' not in response.text


def test_serialized_control_character_payload_is_bounded_without_truncation(passage_api):
    text = '\x01' * 12000
    digest = sha256(text.encode()).hexdigest()
    passage_api.ref['content_sha256'] = digest
    passage_api.state.passage = TraceSourcePassage.model_validate({**passage_api.state.passage.model_dump(),
        'text': text, 'returned_chars': len(text), 'content_sha256': digest})
    response = asyncio.run(passage_api.get())
    assert response.status_code == 409
    assert len(response.content) < 256
