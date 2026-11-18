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

    async def get(*, query=None, authorized=True, turn=None, identities=False):
        q = urlencode({key: ref[key] for key in ['conversation_id', 'attempt', 'source_read_id', 'content_sha256']}) if query is None else query
        path = f"/api/live/agent/worlds/{ref['world_id']}/conversation/turns/{turn or ref['turn_id']}/context-trace/{ref['trace_id']}/source-passages/{ref['source_read_event_id']}"
        if identities:
            path = path.rsplit('/source-passages/', 1)[0] + '/identities'
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


@pytest.mark.parametrize(('authorized', 'query', 'status'), [
    (False, '', 401),
    (True, 'subject_id=foreign-object', 422),
    (True, '', 200),
])
def test_replay_identity_route_only_accepts_the_trace_pin(passage_api, monkeypatch, authorized, query, status):
    from apps.live_control_server.services import agent_replay_identities

    calls = []

    def read(**kwargs):
        calls.append(kwargs)
        return {'identities': []}

    monkeypatch.setattr(agent_replay_identities, 'replay_identities', read)
    response = asyncio.run(passage_api.get(query=query, authorized=authorized, identities=True))
    assert response.status_code == status
    if status == 200:
        assert response.headers['cache-control'] == 'no-store'
        assert len(calls) == 1
        assert calls[0]['world_id'] == passage_api.ref['world_id']
        assert calls[0]['offset'] == 0
        assert str(calls[0]['turn_id']) == passage_api.ref['turn_id']
        assert str(calls[0]['trace_id']) == passage_api.ref['trace_id']
    else:
        assert not calls


def test_replay_names_include_discovery_only_nodes_at_the_saved_pin(monkeypatch):
    from contextlib import contextmanager
    from types import SimpleNamespace
    from apps.live_control_server.services import agent_replay_identities as identities

    discovery = SimpleNamespace(
        revision_id="saved-revision", seed_ids=["seed"],
        labels={"seed": "Caelynn", "discovered": "Unnamed object 26"},
        hops=[SimpleNamespace(from_node_id="seed", to_node_id="discovered")],
    )
    trace = SimpleNamespace(
        trace_id="trace", world_id="elderwyld", turn_id="turn",
        conversation_id="conversation", native_assertion_steps=[], native_discovery_replay=discovery,
    )
    authority = dict(managed_world_id="elderwyld", native_world_id="native", binding_version=1,
                     revision_id="saved-revision", scope_mode="world", campaign_id=None)

    @contextmanager
    def uow(_):
        yield SimpleNamespace(execute=lambda *args: SimpleNamespace(fetchone=lambda: (authority,)))

    pins, reads = [], []
    monkeypatch.setattr(identities, "unit_of_work", uow)
    monkeypatch.setattr(identities, "_ready_dsn", lambda: "mock-dsn")
    monkeypatch.setattr(identities, "_pinned",
                        lambda pin, principal, **kwargs: (pins.append(pin) or pin, "saved-read", None, None, None))
    monkeypatch.setattr(identities, "_response", lambda *args: None)
    monkeypatch.setattr(identities, "EntityReadService", lambda: SimpleNamespace(
        get_entity=lambda read, identity: reads.append((read, identity)) or SimpleNamespace(found=True)))
    monkeypatch.setattr(identities, "map_entity_result",
                        lambda *args, **kwargs: SimpleNamespace(label="Stormspire Academy", kind="location"))
    result = identities.replay_identities(
        service=SimpleNamespace(list_context_trace_attempts=lambda **kwargs: [trace]),
        principal="owner", world_id="elderwyld", turn_id="turn", trace_id="trace",
    )
    assert reads == [("saved-read", "discovered")]
    assert pins[0].revision_id == "saved-revision"
    assert result["identities"] == [{"node_id": "discovered", "label": "Stormspire Academy", "kind": "location"}]
    discovery.hops = [
        SimpleNamespace(from_node_id="seed", to_node_id=f"discovered-{index}")
        for index in range(130)
    ]
    first = identities.replay_identities(
        service=SimpleNamespace(list_context_trace_attempts=lambda **kwargs: [trace]),
        principal="owner", world_id="elderwyld", turn_id="turn", trace_id="trace",
    )
    assert len(first["identities"]) == 128
    assert first["next_offset"] == 128
    last = identities.replay_identities(
        service=SimpleNamespace(list_context_trace_attempts=lambda **kwargs: [trace]),
        principal="owner", world_id="elderwyld", turn_id="turn", trace_id="trace", offset=128,
    )
    assert [item["node_id"] for item in last["identities"]] == ["discovered-128", "discovered-129"]
    assert last["next_offset"] is None
    read_count = len(reads)
    discovery.revision_id = "later-revision"
    with pytest.raises(identities.InspectionUnavailable):
        identities.replay_identities(
            service=SimpleNamespace(list_context_trace_attempts=lambda **kwargs: [trace]),
            principal="owner", world_id="elderwyld", turn_id="turn", trace_id="trace",
        )
    assert len(reads) == read_count
