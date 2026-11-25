from __future__ import annotations

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from apps.live_control_server.native_graph_demo import NativeGraphDemoService
from apps.live_control_server.routes import index_graph, live, workspace_documents, play_runs, media_images
from apps.live_control_server.services import index_graph as graph_service
from apps.live_control_server.services.hosted_auth import install_hosted_request_boundary
from dungeonmind.infrastructure.memory.vnext_sources import InMemoryNativeSourceEvidenceRepository
from tests.test_native_plan_assertions import lane as native_build_lane


def test_guest_build_decision_guard_rejects_effects():
    from types import SimpleNamespace
    from apps.live_control_server.services.build_jev_driver import _require_guest_build_discussion
    from apps.live_control_server.services.agent_turn_service import AgentTurnServiceError
    from apps.live_control_server.services.hosted_native_graph_access import HostedGuestGraphPrincipal
    principal = HostedGuestGraphPrincipal(subject='hosted_guest', role='gm', auth_method='hosted_guest',
        managed_world_id='guest-world', session_id='session', request=SimpleNamespace())
    adapter = SimpleNamespace(native_principal=principal)
    _require_guest_build_discussion(adapter, label='discuss', graph_reference='other_work', image_move='other')
    _require_guest_build_discussion(adapter, label='clarify_request', graph_reference=None, image_move=None)
    from apps.live_control_server.services.agent_graph_auth import NativeGraphPrincipal
    signed_in = SimpleNamespace(native_principal=NativeGraphPrincipal(subject='owner', role='gm', auth_method='hosted_owner'))
    _require_guest_build_discussion(signed_in, label='write_current_page', graph_reference='place_existing_reference', image_move='move_existing')
    for label, graph, image in [('write_current_page', None, None), ('prepare_image', None, None),
                                ('discuss', 'place_existing_reference', None), ('discuss', None, 'move_existing'),
                                (None, None, None)]:
        with pytest.raises(AgentTurnServiceError, match='discussion'):
            _require_guest_build_discussion(adapter, label=label, graph_reference=graph, image_move=image)


def test_guest_build_guard_runs_in_real_decision_driver(native_build_lane, tmp_path, monkeypatch):
    from copy import deepcopy
    from types import SimpleNamespace
    from uuid import uuid4
    from apps.live_control_server.services import build_jev_driver
    from apps.live_control_server.services.hosted_native_graph_access import HostedGuestGraphPrincipal
    from tests.test_surface_native_build_ordinary import _fresh_case
    principal = HostedGuestGraphPrincipal(subject='hosted_guest', role='gm', auth_method='hosted_guest',
        managed_world_id='guest-world', session_id='session', request=SimpleNamespace())
    original = build_jev_driver._require_guest_build_discussion
    seen = []
    def exercise(adapter, **decision):
        seen.append(decision['label'])
        return original(SimpleNamespace(native_principal=principal), **decision)
    monkeypatch.setattr(build_jev_driver, '_require_guest_build_discussion', exercise)
    work = ['discuss']
    case = _fresh_case(native_build_lane, tmp_path, monkeypatch, None, False, False, False,
        message='Discuss the selected object.', requested_work=lambda _message: work[0])
    assert 'discuss' in seen
    before = len(case.writer.calls)
    work[0] = 'write_current_page'
    payload = deepcopy(case.request)
    payload['turn_id'] = str(uuid4())
    payload['message'] = 'Write this to the page.'
    rejected = case.client.post('/api/live/agent/turn', json=payload)
    assert rejected.status_code != 200, rejected.text
    assert seen[-1] == 'write_current_page'
    assert len(case.writer.calls) == before



def test_guest_build_discussion_admission_is_page_and_session_bound(guests, monkeypatch):
    from hashlib import sha256
    from uuid import uuid4
    (first, token, world), (second, other_token, other_world) = guests[0]
    monkeypatch.setenv('DMB_HOSTED_GUEST_CONVERSATION_ENABLED', '1')
    monkeypatch.setenv('DMB_HOSTED_GUEST_TURN_ENABLED', '1')
    monkeypatch.setenv('DMB_HOSTED_GUEST_BUILD_BUDDY_ENABLED', '1')
    headers = {'X-DMB-Index-Graph-CSRF': token}
    created = first.post('/api/live/workspace-documents', headers=headers, json={
        'title': 'Notes', 'world_id': world, 'campaign_id': world, 'kind': 'worldbuilding_source',
        'source_domain': 'worldbuilding', 'document_class': 'lore', 'authority_state': 'draft', 'visibility_state': 'internal'})
    assert created.status_code == 200, created.text
    document = created.json()['document_id']
    digest = sha256(b'').hexdigest()
    body = {'schema': 'dmb_agent_turn_request_v1', 'client_thread_id': str(uuid4()), 'turn_id': str(uuid4()),
        'surface': {'surface_id': 'build', 'instance_id': 'build-main'}, 'owner_scope': {'kind': 'world', 'world_id': world},
        'primary_work': {'kind': 'build', 'object_id': document, 'expected_revision': 1, 'expected_content_sha256': digest},
        'client_work_state': 'saved_clean', 'graph_request': {'mode': 'world', 'world_id': world, 'campaign_id': None,
            'revision_pin': None, 'focus': {'kind': 'none', 'session_id': None, 'campaign_id': None}},
        'graph_selection': None, 'message': 'Discuss this page.', 'build_draft_context': {
            'snapshot': {'schema': 'dmb_build_draft_snapshot_v1', 'world_id': world, 'document_id': document,
                'registry_revision': 1, 'content_sha256': digest, 'visibility': 'internal', 'draft_markdown': '',
                'draft_sha256': digest, 'editor_sha256': digest, 'draft_generation': 0},
            'conversation_id': str(uuid4()), 'expected_pointer_revision': 0}}
    app = FastAPI()
    @app.post('/api/live/agent/turn')
    def admitted():
        return {'admitted': True}
    install_hosted_request_boundary(app)
    async def signed_out(_request): return None
    app.state.dms_principal_resolver = signed_out
    client = TestClient(app, base_url='https://buddy.example', headers={'Origin': 'https://buddy.example', 'Sec-Fetch-Site': 'same-origin'})
    client.cookies.update(first.cookies)
    accepted = client.post('/api/live/agent/turn', headers=headers, json=body)
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()['admitted'] is True
    # Exercise the real turn route after the hosted boundary, stopping at the
    # service boundary so no model or mutation runs in this wiring check.
    from apps.live_control_server.routes import agent
    from apps.live_control_server.services.agent_turn_service import AgentTurnServiceError
    from apps.live_control_server.services.hosted_native_graph_access import HostedGuestGraphPrincipal
    seen = []
    def inspect_principal(_body, **kwargs):
        seen.append(kwargs['native_principal'])
        raise AgentTurnServiceError('wiring verified', code='test_stop', status_code=409)
    monkeypatch.setattr(agent, 'execute_agent_turn', inspect_principal)
    routed_app = FastAPI()
    routed_app.include_router(live.router)
    install_hosted_request_boundary(routed_app)
    routed_app.state.dms_principal_resolver = signed_out
    routed = TestClient(routed_app, base_url='https://buddy.example', headers={
        'Origin': 'https://buddy.example', 'Sec-Fetch-Site': 'same-origin'})
    routed.cookies.update(first.cookies)
    response = routed.post('/api/live/agent/turn', headers=headers, json=body)
    assert response.status_code == 409, response.text
    assert len(seen) == 1 and isinstance(seen[0], HostedGuestGraphPrincipal)
    assert seen[0].managed_world_id == world
    from apps.live_control_server.models.agent_turn import AgentTurnRequest
    from application_state.build_proposal.types import BuildWriteCapability
    from application_state.build_proposal.image_move_capture import BuildImageMoveCapture
    editor = '{"type":"doc","content":[]}'
    basis = {'world_id': world, 'document_id': document, 'registry_revision': 1,
        'content_sha256': digest, 'visibility': 'internal', 'draft_sha256': digest,
        'editor_sha256': sha256(editor.encode()).hexdigest(), 'caret': 0,
        'draft_generation': 0, 'selection_generation': 0}
    capability = BuildWriteCapability(idempotency_key=uuid4(), conversation_id=uuid4(),
        expected_pointer_revision=1, basis=basis, draft_markdown='').model_dump(mode='json')
    capture = BuildImageMoveCapture(basis=basis, conversation_id=uuid4(),
        expected_pointer_revision=1, editor_json=editor).model_dump(mode='json')
    for field, value in [('build_write_capability', capability), ('build_image_move_capture', capture)]:
        draft = {**body['build_draft_context'], 'conversation_id': value['conversation_id'],
            'expected_pointer_revision': value['expected_pointer_revision'],
            'snapshot': {**body['build_draft_context']['snapshot'], 'editor_sha256': basis['editor_sha256']}}
        forged = {**body, 'build_draft_context': draft, field: value}
        AgentTurnRequest.model_validate(forged)
        refused = routed.post('/api/live/agent/turn', headers=headers, json=forged)
        assert refused.status_code == 403, refused.text
        assert len(seen) == 1  # Admission refused it before the service ran.
    monkeypatch.delenv('DMB_HOSTED_GUEST_BUILD_BUDDY_ENABLED')
    assert client.post('/api/live/agent/turn', headers=headers, json=body).status_code == 403
    monkeypatch.setenv('DMB_HOSTED_GUEST_BUILD_BUDDY_ENABLED', '1')
    assert client.post('/api/live/agent/turn', json=body).status_code == 403
    assert client.post('/api/live/agent/turn', headers=headers, json={**body, 'client_work_state': 'saved_dirty'}).status_code == 403
    assert client.post('/api/live/agent/turn', headers={**headers, 'Origin': 'https://bad.example'}, json=body).status_code == 403
    changed_draft = {**body['build_draft_context'], 'snapshot': {**body['build_draft_context']['snapshot'],
        'draft_markdown': 'unsaved', 'draft_sha256': sha256(b'unsaved').hexdigest()}}
    assert client.post('/api/live/agent/turn', headers=headers, json={**body, 'build_draft_context': changed_draft}).status_code == 403
    assert client.post('/api/live/agent/turn', headers=headers, json={**body, 'primary_work': {**body['primary_work'], 'object_id': str(uuid4())}}).status_code != 200
    other_page = second.post('/api/live/workspace-documents', headers={'X-DMB-Index-Graph-CSRF': other_token}, json={
        'title': 'Other notes', 'world_id': other_world, 'campaign_id': other_world, 'kind': 'worldbuilding_source',
        'source_domain': 'worldbuilding', 'document_class': 'lore', 'authority_state': 'draft', 'visibility_state': 'internal'})
    assert other_page.status_code == 200, other_page.text
    other_document = other_page.json()['document_id']
    foreign_page = {**body, 'primary_work': {**body['primary_work'], 'object_id': other_document},
        'build_draft_context': {**body['build_draft_context'], 'snapshot': {**body['build_draft_context']['snapshot'], 'document_id': other_document}}}
    assert client.post('/api/live/agent/turn', headers=headers, json=foreign_page).status_code == 403
    foreign = TestClient(app, base_url='https://buddy.example', headers={'Origin': 'https://buddy.example', 'Sec-Fetch-Site': 'same-origin'})
    foreign.cookies.update(second.cookies)
    assert foreign.post('/api/live/agent/turn', headers={'X-DMB-Index-Graph-CSRF': other_token}, json=body).status_code == 403


def test_guest_play_discussion_admission_is_session_bound(guests, monkeypatch):
    from uuid import uuid4
    from tests.test_agent_turn_route import _play_turn_payload
    (first, token, world), (second, other_token, _other_world) = guests[0]
    monkeypatch.setenv('DMB_HOSTED_GUEST_CONVERSATION_ENABLED', '1')
    monkeypatch.setenv('DMB_HOSTED_GUEST_TURN_ENABLED', '1')
    monkeypatch.setenv('DMB_HOSTED_GUEST_PLAY_ENABLED', '1')
    monkeypatch.setenv('DMB_HOSTED_GUEST_PLAY_BUDDY_ENABLED', '1')
    body = {**_play_turn_payload(), 'client_thread_id': str(uuid4()), 'turn_id': str(uuid4()),
        'owner_scope': {'kind': 'world', 'world_id': world},
        'graph_request': {'mode': 'world', 'world_id': world, 'campaign_id': None,
                          'revision_pin': None, 'focus': {'kind': 'none', 'session_id': None, 'campaign_id': None}}}
    app = FastAPI()
    @app.post('/api/live/agent/turn')
    def admitted(): return {'admitted': True}
    install_hosted_request_boundary(app)
    async def signed_out(_request): return None
    app.state.dms_principal_resolver = signed_out
    client = TestClient(app, base_url='https://buddy.example', headers={'Origin': 'https://buddy.example', 'Sec-Fetch-Site': 'same-origin'})
    client.cookies.update(first.cookies)
    headers = {'X-DMB-Index-Graph-CSRF': token}
    assert client.post('/api/live/agent/turn', headers=headers, json=body).status_code == 200
    assert client.post('/api/live/agent/turn', json=body).status_code == 403
    assert client.post('/api/live/agent/turn', headers={**headers, 'Origin': 'https://bad.example'}, json=body).status_code == 403
    foreign = TestClient(app, base_url='https://buddy.example', headers={'Origin': 'https://buddy.example', 'Sec-Fetch-Site': 'same-origin'})
    foreign.cookies.update(second.cookies)
    assert foreign.post('/api/live/agent/turn', headers={'X-DMB-Index-Graph-CSRF': other_token}, json=body).status_code == 403
    monkeypatch.delenv('DMB_HOSTED_GUEST_PLAY_BUDDY_ENABLED')
    assert client.post('/api/live/agent/turn', headers=headers, json=body).status_code == 403


def test_guest_plan_routes_are_default_off(monkeypatch):
    from apps.live_control_server.services.guest_build_access import matches_guest_build_route
    monkeypatch.delenv("DMB_HOSTED_GUEST_PLAN_ENABLED", raising=False)
    assert not matches_guest_build_route("GET", "/api/live/workspace-documents/world-plans")
    assert not matches_guest_build_route("POST", "/api/live/workspace-documents/world-plans")
    monkeypatch.setenv("DMB_HOSTED_GUEST_PLAN_ENABLED", "1")
    assert matches_guest_build_route("GET", "/api/live/workspace-documents/world-plans")
    assert matches_guest_build_route("POST", "/api/live/workspace-documents/world-plans")
    assert not matches_guest_build_route("DELETE", "/api/live/workspace-documents/world-plans")


def test_guest_play_routes_require_both_flags(monkeypatch):
    from apps.live_control_server.services.guest_build_access import matches_guest_build_route
    monkeypatch.delenv("DMB_HOSTED_GUEST_PLAN_ENABLED", raising=False)
    monkeypatch.setenv("DMB_HOSTED_GUEST_PLAY_ENABLED", "1")
    assert not matches_guest_build_route("GET", "/api/live/world-play-runs/v2")
    monkeypatch.setenv("DMB_HOSTED_GUEST_PLAN_ENABLED", "1")
    assert matches_guest_build_route("GET", "/api/live/world-play-runs/v2")
    assert not matches_guest_build_route("DELETE", "/api/live/world-play-runs/v2")


def test_guest_conversation_plan_revision_requires_both_flags(monkeypatch):
    from apps.live_control_server.services.guest_build_access import matches_guest_build_route
    path = "/api/live/workspace-documents/11111111-1111-4111-8111-111111111111/committed-revision"
    monkeypatch.delenv("DMB_HOSTED_GUEST_PLAY_ENABLED", raising=False)
    monkeypatch.setenv("DMB_HOSTED_GUEST_PLAN_ENABLED", "1")
    monkeypatch.delenv("DMB_HOSTED_GUEST_CONVERSATION_ENABLED", raising=False)
    assert not matches_guest_build_route("GET", path)
    monkeypatch.setenv("DMB_HOSTED_GUEST_CONVERSATION_ENABLED", "1")
    assert matches_guest_build_route("GET", path)
    assert not matches_guest_build_route("POST", path)
    monkeypatch.delenv("DMB_HOSTED_GUEST_PLAN_ENABLED", raising=False)
    assert not matches_guest_build_route("GET", path)


def test_guest_media_routes_are_default_off(monkeypatch):
    from apps.live_control_server.services.guest_build_access import matches_guest_build_route
    monkeypatch.delenv("DMB_HOSTED_GUEST_MEDIA_ENABLED", raising=False)
    assert not matches_guest_build_route("POST", "/api/live/media/images/generate")
    monkeypatch.setenv("DMB_HOSTED_GUEST_MEDIA_ENABLED", "1")
    assert matches_guest_build_route("POST", "/api/live/media/images/generate")
    assert not matches_guest_build_route("POST", "/api/live/media/images/11111111-1111-4111-8111-111111111111/save")


@pytest.fixture
def guests(application_state_dsn, monkeypatch, tmp_path):
    repo = InMemoryNativeSourceEvidenceRepository()
    seed = NativeGraphDemoService(repo, tmp_path / "seed", storage_label="memory")
    try:
        source = seed.graph()
    finally:
        seed.close()
    monkeypatch.setattr(graph_service, "repository", lambda: repo)
    monkeypatch.setenv("DMB_DEPLOYMENT_ENVIRONMENT", "production")
    monkeypatch.setenv("DMB_AUTH_MODE", "hosted_dms")
    monkeypatch.setenv("DMB_HOSTED_GUEST_GRAPH_ENABLED", "1")
    monkeypatch.setenv("DMB_HOSTED_GUEST_BUILD_ENABLED", "1")
    monkeypatch.setenv("DMB_GUEST_GRAPH_SOURCE_SPACE", source["world_id"])
    monkeypatch.setenv("DMB_GUEST_GRAPH_SOURCE_REVISION", source["revision_id"])
    monkeypatch.setenv("AUTH_TRUSTED_FRONTEND_ORIGINS", "https://buddy.example")
    monkeypatch.setattr(workspace_documents, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(live, "repo_root", lambda: tmp_path)
    app = FastAPI()
    app.include_router(index_graph.router)
    app.include_router(workspace_documents.router)
    app.include_router(live.router)
    app.include_router(play_runs.router)
    app.include_router(media_images.router)
    from apps.live_control_server.routes import conversation_library
    app.include_router(conversation_library.router)
    install_hosted_request_boundary(app)
    async def signed_out(_request):
        return None
    app.state.dms_principal_resolver = signed_out
    headers = {"Origin": "https://buddy.example", "Sec-Fetch-Site": "same-origin"}
    clients = [TestClient(app, base_url="https://buddy.example", headers=headers) for _ in range(2)]
    contexts = []
    for client in clients:
        start = client.post("/api/live/index-graph/session")
        assert start.status_code == 200
        csrf = start.json()["csrf_token"]
        world = client.post("/api/live/index-graph/world", headers={"X-DMB-Index-Graph-CSRF": csrf})
        assert world.status_code == 200
        contexts.append((client, csrf, world.json()["world_id"]))
    return contexts, repo, source


def test_guest_conversation_history_and_new_are_session_bound(guests, monkeypatch):
    from uuid import uuid4
    from apps.live_control_server.services import guest_build_access

    (client, csrf, world), (other, _, other_world) = guests[0]
    path = f"/api/live/agent/worlds/{world}/conversation"
    assert client.get(path).status_code == 401
    monkeypatch.setenv("DMB_HOSTED_GUEST_CONVERSATION_ENABLED", "1")
    assert client.get(path).status_code == 200
    assert other.get(path).status_code == 403
    assert client.get(f"/api/live/agent/worlds/{other_world}/conversation").status_code == 403
    assert client.get(path + "?limit=1&limit=2").status_code == 400
    citation = path + f"/turns/{uuid4()}/source-passages/0"
    assert client.get(citation).status_code in (404, 409)
    assert other.get(citation).status_code == 403
    assert client.get(citation + "?world_id=other").status_code == 400
    body = {"command_id": str(uuid4()), "expected_pointer_revision": 0,
            "expected_active_conversation_id": None}
    assert client.post(path + "/new", json=body).status_code == 403
    monkeypatch.setattr(guest_build_access, 'MAX_GUEST_CONVERSATION_BYTES', 1)
    assert client.post(path + "/new", json=body, headers={"X-DMB-Index-Graph-CSRF": csrf}).status_code == 409
    assert client.get(path).json()['conversation_state'] == 'absent'
    monkeypatch.setattr(guest_build_access, 'MAX_GUEST_CONVERSATION_BYTES', 32 * 1024 * 1024)
    response = client.post(path + "/new", json=body, headers={"X-DMB-Index-Graph-CSRF": csrf})
    assert response.status_code == 200, response.text
    from types import SimpleNamespace
    from uuid import UUID
    from application_state.unit_of_work import unit_of_work
    session_id = str(UUID(world.removeprefix('guest-')))
    bound_request = SimpleNamespace(state=SimpleNamespace(guest_build_world=world, guest_build_session=session_id))
    with unit_of_work() as conn:
        guest_build_access._lock_guest_session(bound_request, conn, world)
        exact_bytes = guest_build_access.guest_conversation_bytes(bound_request, conn, world)
    monkeypatch.setattr(guest_build_access, 'MAX_GUEST_CONVERSATION_BYTES', exact_bytes)
    monkeypatch.setattr(guest_build_access, "MAX_GUEST_CONVERSATIONS", 1)
    assert client.post(path + "/new", json=body, headers={"X-DMB-Index-Graph-CSRF": csrf}).json() == response.json()
    monkeypatch.setattr(guest_build_access, 'MAX_GUEST_CONVERSATION_BYTES', 32 * 1024 * 1024)
    second = {"command_id": str(uuid4()), "expected_pointer_revision": 1,
              "expected_active_conversation_id": response.json()["active_conversation_id"]}
    assert client.post(path + "/new", json=second, headers={"X-DMB-Index-Graph-CSRF": csrf}).status_code == 409
    assert client.post("/api/live/index-graph/reset", headers={"X-DMB-Index-Graph-CSRF": csrf}).status_code == 200
    assert client.get(path).status_code in (401, 403)


def test_guest_cleanup_sweep_advances_past_failed_session(guests, monkeypatch):
    from uuid import uuid4
    from application_state.index_graph import guest_conversation_cleanup as cleanup

    monkeypatch.setenv('DMB_HOSTED_GUEST_CONVERSATION_ENABLED', '1')
    for client, csrf, world in guests[0]:
        response = client.post(f'/api/live/agent/worlds/{world}/conversation/new',
            headers={'X-DMB-Index-Graph-CSRF': csrf}, json={'command_id': str(uuid4()),
                'expected_pointer_revision': 0, 'expected_active_conversation_id': None})
        assert response.status_code == 200, response.text
    monkeypatch.setenv('DMB_HOSTED_GUEST_CONVERSATION_ENABLED', '0')
    for client, csrf, _ in guests[0]:
        assert client.post('/api/live/index-graph/reset', headers={'X-DMB-Index-Graph-CSRF': csrf}).status_code == 200
    attempted = []
    def fail(session_id):
        attempted.append(session_id)
        raise RuntimeError('synthetic unexpected dependency')
    monkeypatch.setattr(cleanup, '_cursor', None)
    monkeypatch.setattr(cleanup, 'cleanup_expired_guest_conversation', fail)
    cleanup.cleanup_expired_guest_conversations(limit=1)
    cleanup.cleanup_expired_guest_conversations(limit=1)
    assert len(attempted) == 2 and attempted[0] != attempted[1]


def test_guest_cleanup_skips_a_locked_session(guests, monkeypatch, application_state_dsn):
    from time import monotonic
    from uuid import UUID
    from application_state.engine import connect
    from application_state.errors import ApplicationStateConflictError
    from application_state.index_graph.guest_conversation_cleanup import cleanup_expired_guest_conversation

    (client, csrf, world), _ = guests[0]
    monkeypatch.setenv('DMB_HOSTED_GUEST_CONVERSATION_ENABLED', '0')
    assert client.post('/api/live/index-graph/reset', headers={'X-DMB-Index-Graph-CSRF': csrf}).status_code == 200
    session_id = str(UUID(world.removeprefix('guest-')))
    with connect(application_state_dsn) as conn:
        conn.execute('SELECT 1 FROM application_state.index_graph_sessions WHERE session_id=%s FOR UPDATE', (session_id,))
        started = monotonic()
        with pytest.raises(ApplicationStateConflictError):
            cleanup_expired_guest_conversation(session_id)
        assert monotonic() - started < 2


def test_guest_cleanup_rolls_back_on_unexpected_dependency(guests, monkeypatch, application_state_dsn):
    from uuid import UUID, uuid4
    from application_state.engine import connect
    from application_state.index_graph.guest_conversation_cleanup import cleanup_expired_guest_conversation
    import psycopg

    (client, csrf, world), _ = guests[0]
    monkeypatch.setenv('DMB_HOSTED_GUEST_CONVERSATION_ENABLED', '1')
    response = client.post(f'/api/live/agent/worlds/{world}/conversation/new',
        headers={'X-DMB-Index-Graph-CSRF': csrf}, json={'command_id': str(uuid4()),
            'expected_pointer_revision': 0, 'expected_active_conversation_id': None})
    assert response.status_code == 200, response.text
    monkeypatch.setenv('DMB_HOSTED_GUEST_CONVERSATION_ENABLED', '0')
    assert client.post('/api/live/index-graph/reset', headers={'X-DMB-Index-Graph-CSRF': csrf}).status_code == 200
    session_id = str(UUID(world.removeprefix('guest-')))
    with connect(application_state_dsn) as conn:
        conn.execute('CREATE TABLE agent.test_guest_cleanup_dependency (conversation_id uuid REFERENCES agent.conversation(conversation_id))')
        conn.execute('INSERT INTO agent.test_guest_cleanup_dependency VALUES (%s)', (response.json()['conversation_id'],))
        conn.commit()
        try:
            with pytest.raises(psycopg.errors.ForeignKeyViolation):
                cleanup_expired_guest_conversation(session_id)
            assert conn.execute('SELECT count(*) FROM agent.command_receipt WHERE world_id=%s', (world,)).fetchone()[0] == 1
            assert conn.execute('SELECT count(*) FROM agent.world_state WHERE world_id=%s', (world,)).fetchone()[0] == 1
            assert conn.execute('SELECT count(*) FROM agent.conversation WHERE world_id=%s', (world,)).fetchone()[0] == 1
        finally:
            conn.rollback()
            conn.execute('DROP TABLE agent.test_guest_cleanup_dependency')
            conn.commit()


def test_guest_turn_admission_is_default_off_and_rejects_streams(guests, monkeypatch):
    from tests.test_agent_turn_route import _payload

    (client, csrf, world), (_, _, other_world) = guests[0]
    path = "/api/live/agent/turn"
    headers = {"X-DMB-Index-Graph-CSRF": csrf}
    monkeypatch.setenv("DMB_HOSTED_GUEST_CONVERSATION_ENABLED", "1")
    assert client.post(path, json={}, headers=headers).status_code == 401
    monkeypatch.setenv("DMB_HOSTED_GUEST_TURN_ENABLED", "1")
    assert client.post(path, json={}, headers={**headers, "Accept": "text/event-stream"}).status_code == 403
    assert client.post(path, json={}).status_code == 403
    assert client.post(path, json={}, headers=headers).status_code == 400
    forged = {**_payload(), "owner_scope": {"kind": "world", "world_id": other_world}}
    assert client.post(path, json=forged, headers=headers).status_code == 403
    unsupported = {**_payload(), "owner_scope": {"kind": "world", "world_id": world},
                   "surface": {"surface_id": "plan", "instance_id": "plan-main"}}
    rejected = client.post(path, json=unsupported, headers=headers)
    assert rejected.status_code == 403, rejected.text
    assert rejected.json()["detail"]["code"] == "guest_turn_capability_unavailable"
    conflicting = {**_payload(), "owner_scope": {"kind": "world", "world_id": world},
                   "graph_request": {"mode": "world", "world_id": other_world, "campaign_id": None,
                                     "revision_pin": None, "focus": {"kind": "none", "session_id": None, "campaign_id": None}}}
    assert client.post(path, json=conflicting, headers=headers).status_code == 403


def test_guest_plan_discussion_uses_normal_native_request_shape(guests, monkeypatch):
    from tests.test_plan_jev_authoring import request_payload
    from apps.live_control_server.routes import agent

    (client, csrf, world), _ = guests[0]
    monkeypatch.setenv("DMB_HOSTED_GUEST_CONVERSATION_ENABLED", "1")
    monkeypatch.setenv("DMB_HOSTED_GUEST_TURN_ENABLED", "1")
    observed = []
    monkeypatch.setattr(agent, "_execute_agent_turn", lambda body, _request: observed.append(body) or {"ok": True})
    payload = request_payload()
    payload.pop("plan_authoring_capture")
    payload["owner_scope"]["world_id"] = world
    payload["plan_context_policy"] = {"schema": "dmb_plan_context_policy_v2", "policy": "auto_plan_world", "graph_source": "reviewed_native_graph"}
    headers = {"X-DMB-Index-Graph-CSRF": csrf}
    response = client.post("/api/live/agent/turn", json=payload, headers=headers)
    assert response.status_code == 200, response.text
    assert len(observed) == 1
    payload["plan_requested_operation"] = "write_current_page"
    rejected = client.post("/api/live/agent/turn", json=payload, headers=headers)
    assert rejected.status_code == 403, rejected.text
    assert len(observed) == 1


def test_guest_read_revalidation_does_not_block_own_session_lock(guests, application_state_dsn):
    from types import SimpleNamespace
    from uuid import UUID
    from dataclasses import replace
    from fastapi import HTTPException
    from application_state.engine import connect
    from application_state.errors import ApplicationStateConflictError
    from apps.live_control_server.services.hosted_native_graph_access import HostedGuestGraphPrincipal, require_guest_read_access

    (client, csrf, world), _ = guests[0]
    session_id = str(UUID(world.removeprefix('guest-')))
    request = SimpleNamespace(state=SimpleNamespace(guest_build_world=world, guest_build_session=session_id))
    principal = HostedGuestGraphPrincipal(subject='hosted_guest', role='gm', auth_method='hosted_guest',
        managed_world_id=world, session_id=session_id, request=request)
    with connect(application_state_dsn) as conn:
        conn.execute('SELECT 1 FROM application_state.index_graph_sessions WHERE session_id=%s FOR UPDATE', (session_id,))
        require_guest_read_access(principal, world)
    with pytest.raises(HTTPException):
        require_guest_read_access(replace(principal, auth_method='local_operator'), world)
    with connect(application_state_dsn) as conn:
        original = conn.execute("SELECT value FROM application_state.index_graph_bindings WHERE session_id=%s AND key='space_id'", (session_id,)).fetchone()[0]
        conn.execute("UPDATE application_state.index_graph_bindings SET value='foreign-space' WHERE session_id=%s AND key='space_id'", (session_id,))
    with pytest.raises(HTTPException):
        require_guest_read_access(principal, world)
    with connect(application_state_dsn) as conn:
        conn.execute("UPDATE application_state.index_graph_bindings SET value=%s WHERE session_id=%s AND key='space_id'", (original, session_id))
    assert client.post('/api/live/index-graph/reset', headers={'X-DMB-Index-Graph-CSRF': csrf}).status_code == 200
    with pytest.raises(ApplicationStateConflictError):
        require_guest_read_access(principal, world)


@pytest.mark.parametrize('reset_during_read', [False, True])
def test_guest_reset_revokes_prepared_native_graph_read(guests, tmp_path, monkeypatch, reset_during_read):
    from types import SimpleNamespace
    from uuid import UUID
    from application_state.errors import ApplicationStateConflictError
    from apps.live_control_server.services.hosted_native_graph_access import HostedGuestGraphPrincipal
    from apps.live_control_server.services.native_graph_reads import prepare_query, read_selected
    from tests.test_source_statements import make_lane
    from tests.test_native_plan_assertions import publish, grant

    (client, csrf, world), _ = guests[0]
    lane = make_lane(tmp_path, monkeypatch, narrow=True)
    publish(lane)
    session_id = str(UUID(world.removeprefix('guest-')))
    request = SimpleNamespace(state=SimpleNamespace(guest_build_world=world, guest_build_session=session_id))
    principal = HostedGuestGraphPrincipal(subject='hosted_guest', role='gm', auth_method='hosted_guest',
        managed_world_id=world, session_id=session_id, request=request)
    binding = SimpleNamespace(managed_world_id=world, native_world_id=lane.world.world_id,
                              binding_version=1, provisioning_id=None)
    context, _ = prepare_query(world, 'What did B do?', principal, repository=lane.repo,
                               resolve_binding=lambda _: binding)
    authorization = grant(context)
    reads, _ = read_selected(context, authorization, principal)
    assert reads
    def reset():
        assert client.post('/api/live/index-graph/reset', headers={'X-DMB-Index-Graph-CSRF': csrf}).status_code == 200

    if reset_during_read:
        from apps.live_control_server.services import native_graph_reads
        original = native_graph_reads._read_assertions

        def reset_after_read(*args, **kwargs):
            result = original(*args, **kwargs)
            reset()
            return result

        monkeypatch.setattr(native_graph_reads, '_read_assertions', reset_after_read)
    else:
        reset()
    with pytest.raises(ApplicationStateConflictError):
        read_selected(context, authorization, principal)


def test_guest_reset_during_authored_reference_read_discards_result(guests, tmp_path, monkeypatch):
    from types import SimpleNamespace
    from uuid import UUID
    from application_state.errors import ApplicationStateConflictError
    from application_state.agent_conversation.authored_graph_references import AuthoredGraphReferenceV1, AuthoredReferencesV2
    from apps.live_control_server.services.hosted_native_graph_access import HostedGuestGraphPrincipal
    from apps.live_control_server.services import native_graph_reads
    from tests.test_source_statements import make_lane
    from tests.test_native_plan_assertions import publish
    from tests.test_surface_native_authored_references import human_grant

    (client, csrf, world), _ = guests[0]
    lane = make_lane(tmp_path, monkeypatch, narrow=True)
    publish(lane)
    session_id = str(UUID(world.removeprefix('guest-')))
    request = SimpleNamespace(state=SimpleNamespace(guest_build_world=world, guest_build_session=session_id))
    principal = HostedGuestGraphPrincipal(subject='hosted_guest', role='gm', auth_method='hosted_guest',
        managed_world_id=world, session_id=session_id, request=request)
    binding = SimpleNamespace(managed_world_id=world, native_world_id=lane.world.world_id,
                              binding_version=1, provisioning_id=None)
    selected = AuthoredReferencesV2(references=(AuthoredGraphReferenceV1(managed_world_id=world,
        native_world_id=lane.world.world_id, binding_version=1,
        graph_revision=lane.repo.get_head(lane.world.world_id).head_revision_id,
        node_id=lane.ids['B'], label='B'),))
    context, _ = native_graph_reads.prepare_query(world, 'What did B do?', principal,
        repository=lane.repo, resolve_binding=lambda _: binding, authored_references=selected)
    authorization = human_grant(context, selected)
    original = native_graph_reads._read_assertions
    def reset_after_read(*args, **kwargs):
        result = original(*args, **kwargs)
        assert client.post('/api/live/index-graph/reset', headers={'X-DMB-Index-Graph-CSRF': csrf}).status_code == 200
        return result
    monkeypatch.setattr(native_graph_reads, '_read_assertions', reset_after_read)
    with pytest.raises(ApplicationStateConflictError):
        native_graph_reads.read_authored_reference(context, authorization, principal)


@pytest.mark.parametrize('reset_during_direct_read', [False, True])
def test_guest_reset_revokes_prepared_native_source_body(guests, tmp_path, monkeypatch, reset_during_direct_read):
    from types import SimpleNamespace
    from uuid import UUID
    from application_state.errors import ApplicationStateConflictError
    from apps.live_control_server.integrations.dungeonmind.native_corpus_source import prepare_native_source_context, open_native_corpus_member, read_direct_native_source
    from apps.live_control_server.services.hosted_native_graph_access import HostedGuestGraphPrincipal
    from tests.test_source_statements import make_lane
    from tests.test_native_plan_assertions import publish

    (client, csrf, world), _ = guests[0]
    lane = make_lane(tmp_path, monkeypatch, narrow=True)
    publish(lane)
    session_id = str(UUID(world.removeprefix('guest-')))
    request = SimpleNamespace(state=SimpleNamespace(guest_build_world=world, guest_build_session=session_id))
    principal = HostedGuestGraphPrincipal(subject='hosted_guest', role='gm', auth_method='hosted_guest',
        managed_world_id=world, session_id=session_id, request=request)
    binding = SimpleNamespace(managed_world_id=world, native_world_id=lane.world.world_id,
                              binding_version=1, provisioning_id=None)
    context = prepare_native_source_context(managed_world_id=world, principal=principal,
        repository=lane.repo, resolve_identity=lambda _: binding)
    member, _ = open_native_corpus_member(context, lane.meta.evidence_ref_ids[0])
    def reset():
        assert client.post('/api/live/index-graph/reset', headers={'X-DMB-Index-Graph-CSRF': csrf}).status_code == 200

    if reset_during_direct_read:
        from application_state.agent_conversation import native_corpus
        original = native_corpus.build_native_body_catalog
        def reset_after_open(*args, **kwargs):
            result = original(*args, **kwargs)
            reset()
            return result
        monkeypatch.setattr(native_corpus, 'build_native_body_catalog', reset_after_open)
        with pytest.raises(ApplicationStateConflictError):
            read_direct_native_source(context, authority=context.authority,
                source_artifact_id=member.artifact.source_artifact_id,
                source_revision_id=member.revision.source_revision_id,
                content_sha256=member.revision.content_sha256)
    else:
        reset()
        with pytest.raises(ApplicationStateConflictError):
            open_native_corpus_member(context, lane.meta.evidence_ref_ids[0])


@pytest.mark.parametrize(('reset_during_writer', 'reset_during_build', 'reset_during_play', 'retained_reset'), [(False, False, False, None), (True, False, False, None), (False, True, False, None), (False, False, True, None), (False, False, False, 'admission'), (False, False, False, 'writer'), (False, False, False, 'quota-admission'), (False, False, False, 'quota-writer')])
def test_native_source_world_bootstraps_real_guest_copy(application_state_dsn, tmp_path, monkeypatch, reset_during_writer, reset_during_build, reset_during_play, retained_reset):
    import json
    import re
    import httpx2
    from threading import Event
    from concurrent.futures import ThreadPoolExecutor
    from uuid import uuid4
    from tests.test_source_statements import make_lane
    from tests.test_native_plan_assertions import publish, grant
    from application_state.world_catalog.service import get_world
    from apps.live_control_server.services.hosted_native_graph_access import HostedGuestGraphPrincipal
    from apps.live_control_server.services.native_graph_reads import prepare_query, read_selected
    from types import SimpleNamespace
    from uuid import UUID
    from apps.live_control_server.routes import agent
    from apps.live_control_server.services import plan_jev_harness
    from apps.live_control_server.services.plan_jev_harness import PlanJevHarness
    from apps.live_control_server.integrations.dungeonmind import native_registry_source
    from apps.live_control_server.routes import native_graph_inspection
    from apps.live_control_server.routes import native_source_inspection
    from apps.live_control_server.services import native_source_inspection as source_inspection_service
    from tests.test_plan_jev_writer import WriterWire
    from application_state.agent_conversation.native_plan_assertions import POLICY

    lane = make_lane(tmp_path, monkeypatch, narrow=True)
    publish(lane)
    monkeypatch.setattr(graph_service, 'repository', lambda: lane.repo)
    monkeypatch.setenv('DMB_DEPLOYMENT_ENVIRONMENT', 'production')
    monkeypatch.setenv('DMB_AUTH_MODE', 'hosted_dms')
    monkeypatch.setenv('DMB_HOSTED_GUEST_GRAPH_ENABLED', '1')
    monkeypatch.setenv('DMB_HOSTED_GUEST_BUILD_ENABLED', '1')
    monkeypatch.setenv('DMB_HOSTED_GUEST_PLAN_ENABLED', '1')
    monkeypatch.setenv('DMB_HOSTED_GUEST_CONVERSATION_ENABLED', '1')
    monkeypatch.delenv('DMB_HOSTED_GUEST_PLAY_ENABLED', raising=False)
    monkeypatch.setenv('DMB_HOSTED_GUEST_TURN_ENABLED', '1')
    monkeypatch.setenv('DMB_GUEST_GRAPH_SOURCE_SPACE', lane.world.world_id)
    monkeypatch.setenv('DMB_GUEST_GRAPH_SOURCE_REVISION', lane.repo.get_head(lane.world.world_id).head_revision_id)
    monkeypatch.setenv('AUTH_TRUSTED_FRONTEND_ORIGINS', 'https://buddy.example')
    app = FastAPI()
    app.include_router(index_graph.router)
    app.include_router(workspace_documents.router)
    app.include_router(live.router)
    app.include_router(play_runs.router)
    app.include_router(native_graph_inspection.router)
    app.include_router(native_source_inspection.router)
    monkeypatch.setattr(workspace_documents, 'repo_root', lambda: tmp_path)
    monkeypatch.setattr(live, 'repo_root', lambda: tmp_path)
    monkeypatch.setattr(agent, 'repo_root', lambda: tmp_path)
    monkeypatch.setattr(agent, '_managed_world_root', lambda: tmp_path)
    monkeypatch.setattr(agent, 'session_dir', lambda: tmp_path / 'sessions')
    monkeypatch.setattr(native_registry_source, 'repository', lambda **_kw: lane.repo)
    monkeypatch.setattr(native_registry_source, 'read_repository', lambda **_kw: lane.repo)
    monkeypatch.setattr(source_inspection_service, 'turn_source_repository', lambda **_kw: lane.repo)
    from dataclasses import asdict
    monkeypatch.setattr(native_registry_source, 'binding', lambda world_id: asdict(native_registry_source.resolve_managed_world_binding(world_id)))
    monkeypatch.setattr('apps.live_control_server.services.agent_graph_policy.resolve_agent_graph_openai_inference',
        lambda **_: ('openai-api', 'gpt-6-luna', 'https://api.openai.com/v1'))
    install_hosted_request_boundary(app)
    async def signed_out(_request):
        return None
    app.state.dms_principal_resolver = signed_out
    client = TestClient(app, base_url='https://buddy.example', headers={'Origin': 'https://buddy.example', 'Sec-Fetch-Site': 'same-origin'})
    session = client.post('/api/live/index-graph/session')
    assert session.status_code == 200, session.text
    headers = {'X-DMB-Index-Graph-CSRF': session.json()['csrf_token']}
    guest = client.post('/api/live/index-graph/world', headers=headers)
    assert guest.status_code == 200, guest.text
    world = get_world(guest.json()['world_id']).record
    assert world.native_graph_binding.native_world_id != lane.world.world_id
    assert lane.repo.get_head(world.native_graph_binding.native_world_id) is not None
    inspection_scope = {'managed_world_id': world.world_id, 'scope_mode': 'world', 'campaign_id': None}
    assert client.post('/api/live/native-graph-inspection/catalog', json=inspection_scope).status_code == 403
    catalog = client.post('/api/live/native-graph-inspection/catalog', headers=headers, json=inspection_scope)
    assert catalog.status_code == 200, catalog.text
    inspection = {'scope': catalog.json()['scope'], 'selection': {'kind': 'entity', 'entity_id': lane.ids['B']}}
    selected = client.post('/api/live/native-graph-inspection/read', headers=headers, json=inspection)
    assert selected.status_code == 200, selected.text
    forbidden = {**inspection, 'scope': {**inspection['scope'], 'managed_world_id': 'foreign-world'}}
    assert client.post('/api/live/native-graph-inspection/read', headers=headers, json=forbidden).status_code == 403
    forged = {**inspection, 'scope': {**inspection['scope'], 'native_world_id': lane.world.world_id}}
    assert client.post('/api/live/native-graph-inspection/read', headers=headers, json=forged).status_code != 200
    assert client.post('/api/live/native-graph-inspection/read', headers=headers,
        json={**inspection, 'selection': {'kind': 'chronology'}}).status_code == 403
    assert client.post('/api/live/native-source-inspection/catalog', json=inspection_scope).status_code == 403
    sources = client.post('/api/live/native-source-inspection/catalog', headers=headers, json=inspection_scope)
    assert sources.status_code == 200, sources.text
    item = sources.json()['catalogue']['sources'][0]
    source_read = {'scope': sources.json()['scope'], 'source_artifact_id': item['source_artifact']['source_artifact_id'],
                   'source_revision_id': item['source_revision']['source_revision_id'], 'evidence_ref_id': item['evidence_ref_ids'][0]}
    opened_source = client.post('/api/live/native-source-inspection/read', headers=headers, json=source_read)
    assert opened_source.status_code == 200, opened_source.text
    assert 'A reports that B fled' in opened_source.text
    foreign_source = {**source_read, 'scope': {**source_read['scope'], 'managed_world_id': 'foreign-world'}}
    assert client.post('/api/live/native-source-inspection/read', headers=headers, json=foreign_source).status_code == 403
    forged_source = {**source_read, 'scope': {**source_read['scope'], 'native_world_id': lane.world.world_id}}
    assert client.post('/api/live/native-source-inspection/read', headers=headers, json=forged_source).status_code != 200
    session_id = str(UUID(world.world_id.removeprefix('guest-')))
    request = SimpleNamespace(state=SimpleNamespace(guest_build_world=world.world_id, guest_build_session=session_id))
    principal = HostedGuestGraphPrincipal(subject='hosted_guest', role='gm', auth_method='hosted_guest',
        managed_world_id=world.world_id, session_id=session_id, request=request)
    context, _ = prepare_query(world.world_id, 'What did B do?', principal, repository=lane.repo)
    reads, _ = read_selected(context, grant(context), principal)
    assert reads
    # Exercise the real guest Build turn with synthetic decision and writer transports.
    from apps.live_control_server.services.build_jev_harness import BuildJevHarness
    from tests.test_build_jev_estimated_continuations import counter
    from hashlib import sha256
    monkeypatch.setenv('DMB_HOSTED_GUEST_BUILD_BUDDY_ENABLED', '1')
    page_response = client.post('/api/live/workspace-documents', headers=headers, json={
        'title': 'Guest Build context', 'world_id': world.world_id, 'campaign_id': world.world_id,
        'kind': 'worldbuilding_source', 'source_domain': 'worldbuilding', 'document_class': 'lore',
        'authority_state': 'draft', 'visibility_state': 'internal'})
    assert page_response.status_code == 200, page_response.text
    page = page_response.json()['document_id']
    page_draft = {'document_id': page, 'markdown': '# Guest notes\n\nA saved detail.'}
    page_prepare = client.post('/api/live/tiptap/markdown-write/prepare', headers=headers, json=page_draft)
    assert page_prepare.status_code == 200, page_prepare.text
    page_commit = client.post('/api/live/tiptap/markdown-write/commit', headers=headers, json={
        **page_draft, 'writer_confirm_token': page_prepare.json()['writer_confirm_token'],
        'expected_revision': page_prepare.json()['registry_revision']})
    assert page_commit.status_code == 200, page_commit.text
    from apps.live_control_server.services.workspace_document_registry import get_committed_page_snapshot
    saved_page = get_committed_page_snapshot(tmp_path, page)
    pointer_response = client.post(f'/api/live/agent/worlds/{world.world_id}/conversation/new',
        headers=headers, json={'command_id': str(uuid4()), 'expected_pointer_revision': 0,
                               'expected_active_conversation_id': None})
    assert pointer_response.status_code == 200, pointer_response.text
    pointer = pointer_response.json()
    empty_digest = sha256(saved_page.markdown.encode()).hexdigest()
    build_payload = {'schema': 'dmb_agent_turn_request_v1', 'client_thread_id': str(uuid4()), 'turn_id': str(uuid4()),
        'surface': {'surface_id': 'build', 'instance_id': page},
        'owner_scope': {'kind': 'world', 'world_id': world.world_id},
        'primary_work': {'kind': 'build', 'object_id': page, 'expected_revision': saved_page.loaded_revision,
                         'expected_content_sha256': empty_digest},
        'client_work_state': 'saved_clean', 'graph_request': {'mode': 'world', 'world_id': world.world_id,
            'campaign_id': None, 'revision_pin': None, 'focus': {'kind': 'none', 'session_id': None, 'campaign_id': None}},
        'graph_selection': None, 'message': 'Discuss the page.', 'build_draft_context': {
            'snapshot': {'schema': 'dmb_build_draft_snapshot_v1', 'world_id': world.world_id,
                'document_id': page, 'registry_revision': saved_page.loaded_revision, 'content_sha256': empty_digest,
                'visibility': 'internal', 'draft_markdown': saved_page.markdown, 'draft_sha256': empty_digest,
                'editor_sha256': empty_digest, 'draft_generation': 0},
            'conversation_id': pointer['conversation_id'], 'expected_pointer_revision': pointer['pointer_revision']}}
    monkeypatch.setenv('TYPESAFE_JEV_API_KEY', 'synthetic-only')
    monkeypatch.setenv('OPENAI_API_KEY', 'synthetic-only')
    from application_state.agent_conversation.native_plan_assertions import POLICY as BUILD_POLICY
    import httpx
    from application_state.agent_conversation.rules_authority_policy import rules_capability
    seen_build = []
    class BuildDecisions(httpx2.AsyncBaseTransport):
        async def handle_async_request(self, req):
            body = json.loads(req.content)
            answers = {}
            for name, question in body['questions'].items():
                choice = ('discuss' if name == 'requested_work' else 'anchored' if name == 'source_need'
                          else 'finish_retrieval' if name == 'operation' else 'exclude' if name.startswith('candidate_')
                          else 'skip')
                assert choice in question['criteria'], (name, question['criteria'])
                answers[name] = {'type': 'choice', 'choice': choice, 'confidence': 1,
                    'probabilities': {key: float(key == choice) for key in question['criteria']}}
            return httpx2.Response(200, request=req, json={'model': 'jev-1.14.0', 'answers': answers,
                'usage': {'input_tokens': 37, 'output_tokens': 9}})
    build_entered, build_release = Event(), Event()
    class BuildWriter(httpx.AsyncBaseTransport):
        async def handle_async_request(self, req):
            if reset_during_build:
                build_entered.set()
                assert build_release.wait(15)
            body = json.loads(req.content)
            candidate = {'schema': BUILD_POLICY, 'answer_segments': [
                {'kind': 'discussion', 'text': 'We can discuss this saved page.'}],
                'limitations': [], 'requested_detail_gaps': [], 'collaboration': None}
            properties = body['text']['format']['schema']['properties']
            candidate = {key: value for key, value in candidate.items() if key in properties}
            return httpx.Response(200, request=req, json={'id': 'resp_build', 'object': 'response',
                'created_at': 1, 'status': 'completed', 'model': body['model'], 'output': [
                    {'type': 'message', 'id': 'msg_build', 'role': 'assistant', 'status': 'completed',
                     'content': [{'type': 'output_text', 'text': json.dumps(candidate), 'annotations': []}]}],
                'usage': {'input_tokens': 100, 'output_tokens': 40, 'total_tokens': 140}})
    class InspectBuild(BuildJevHarness):
        def execute(self, adapter):
            seen_build.append(adapter)
            return super().execute(adapter)
    app.state.build_jev_runtime_factory = SimpleNamespace(create=lambda: InspectBuild(
        decision_transport=BuildDecisions(), writer_transport=BuildWriter(), accounting=counter(),
        world_context=True, named_citations=True, related_pages=True, rules_capability=rules_capability(graph=True)))
    stale_revision = build_payload['primary_work']['expected_revision'] + 1
    stale = {**build_payload, 'turn_id': str(uuid4()),
        'primary_work': {**build_payload['primary_work'], 'expected_revision': stale_revision},
        'build_draft_context': {**build_payload['build_draft_context'], 'snapshot': {
            **build_payload['build_draft_context']['snapshot'], 'registry_revision': stale_revision}}}
    stale_response = client.post('/api/live/agent/turn', headers=headers, json=stale)
    assert stale_response.status_code == 409, stale_response.text
    assert stale_response.json()['detail']['code'] == 'build_source_unavailable'
    assert not seen_build
    if reset_during_build:
        with ThreadPoolExecutor(max_workers=1) as pool:
            pending_build = pool.submit(client.post, '/api/live/agent/turn', headers=headers, json=build_payload)
            try:
                assert build_entered.wait(15)
                assert client.post('/api/live/index-graph/reset', headers=headers).status_code == 200
            finally:
                build_release.set()
            build_response = pending_build.result(timeout=15)
        assert build_response.status_code != 200, build_response.text
        assert 'discuss this saved page' not in build_response.text
        from application_state.engine import connect
        with connect(application_state_dsn) as conn:
            assert conn.execute("SELECT count(*) FROM agent.turn WHERE turn_id=%s AND status='completed'",
                                (build_payload['turn_id'],)).fetchone()[0] == 0
        return
    build_response = client.post('/api/live/agent/turn', headers=headers, json=build_payload)
    assert build_response.status_code == 200, build_response.text
    assert 'discuss this saved page' in build_response.json()['answer']['text']
    assert len(seen_build) == 1 and isinstance(seen_build[0].native_principal, HostedGuestGraphPrincipal)
    assert seen_build[0].native_principal.managed_world_id == world.world_id
    if retained_reset and retained_reset.startswith('quota-'):
        from application_state.agent_conversation import AgentConversationService
        from application_state.errors import ApplicationStateConflictError
        boundary = retained_reset.removeprefix('quota-')
        method = 'admit_pending_build_prior_body_evidence' if boundary == 'admission' else 'authorize_pending_build_writer'
        original = getattr(AgentConversationService, method)
        rejected = []
        def reject_transaction(owner, world_id, conversation_id, turn_id, **kwargs):
            before = owner.inspect_turn(world_id=world_id, turn_id=turn_id)
            previous = owner._validate_transaction
            def reject(_conn):
                rejected.append(True)
                raise ApplicationStateConflictError('guest quota exceeded')
            owner._validate_transaction = reject
            try:
                with pytest.raises(ApplicationStateConflictError, match='guest quota exceeded'):
                    original(owner, world_id, conversation_id, turn_id, **kwargs)
            finally:
                owner._validate_transaction = previous
            assert owner.inspect_turn(world_id=world_id, turn_id=turn_id) == before
            raise ApplicationStateConflictError('guest quota exceeded')
        monkeypatch.setattr(AgentConversationService, method, reject_transaction)
        followup = {**build_payload, 'turn_id': str(uuid4()), 'message': 'Recap our conversation without another search.'}
        result = client.post('/api/live/agent/turn', headers=headers, json=followup)
        assert result.status_code != 200 and rejected
        return
    if retained_reset:
        from application_state.agent_conversation import AgentConversationService
        method = 'admit_pending_build_prior_body_evidence' if retained_reset == 'admission' else 'authorize_pending_build_writer'
        original = getattr(AgentConversationService, method)
        locked, release = Event(), Event()
        def pause_after_guest_lock(owner, *args, **kwargs):
            previous = owner._authorize_transaction
            def hold(conn, *, read_only):
                previous(conn, read_only=read_only)
                if not read_only and not locked.is_set():
                    locked.set()
                    assert release.wait(15)
            owner._authorize_transaction = hold
            try:
                return original(owner, *args, **kwargs)
            finally:
                owner._authorize_transaction = previous
        monkeypatch.setattr(AgentConversationService, method, pause_after_guest_lock)
        followup = {**build_payload, 'turn_id': str(uuid4()), 'message': 'Recap our conversation without another search.'}
        with ThreadPoolExecutor(max_workers=2) as pool:
            pending = pool.submit(client.post, '/api/live/agent/turn', headers=headers, json=followup)
            try:
                assert locked.wait(15)
                reset = pool.submit(client.post, '/api/live/index-graph/reset', headers=headers)
                import time
                from application_state.engine import connect
                deadline = time.monotonic() + 5
                with connect(application_state_dsn) as observer:
                    while time.monotonic() < deadline:
                        observer.execute('SELECT pg_stat_clear_snapshot()')
                        waiters = observer.execute("SELECT count(*) FROM pg_stat_activity WHERE datname = current_database() AND wait_event_type = 'Lock'").fetchone()[0]
                        if waiters:
                            break
                        time.sleep(0.05)
                assert waiters and not reset.done(), 'reset did not wait for the active guest transaction'
            finally:
                release.set()
            assert reset.result(timeout=15).status_code == 200
            pending.result(timeout=15)
        assert client.get(f'/api/live/agent/worlds/{world.world_id}/conversation').status_code in (401, 403)
        return
    del app.state.build_jev_runtime_factory
    plan = client.post('/api/live/workspace-documents/world-plans', headers=headers,
        json={'schema_version': 'dmb_workspace_document_create_v2', 'scope_mode': 'world',
              'world_id': world.world_id, 'title': 'Guest source question'})
    assert plan.status_code == 200, plan.text
    document = plan.json()['document_id']
    draft = {'document_id': document, 'markdown': '# Session\n\nInvestigate the report.',
             'world_id': world.world_id, 'scope_mode': 'world',
             'schema_version': 'dmb_tiptap_markdown_write_prepare_v2'}
    prepared = client.post('/api/live/tiptap/markdown-write/prepare', headers=headers, json=draft)
    assert prepared.status_code == 200, prepared.text
    commit = {**draft, 'schema_version': 'dmb_tiptap_markdown_write_commit_v2',
              'writer_confirm_token': prepared.json()['writer_confirm_token'],
              'expected_revision': prepared.json()['registry_revision']}
    saved = client.post('/api/live/tiptap/markdown-write/commit', headers=headers, json=commit)
    assert saved.status_code == 200, saved.text
    snapshot = client.get(f'/api/live/workspace-documents/{document}/snapshot')
    assert snapshot.status_code == 200, snapshot.text
    assert 'Investigate the report.' in snapshot.json()['markdown']
    revision = client.get(f'/api/live/workspace-documents/{document}/committed-revision')
    assert revision.status_code == 200, revision.text

    class Decisions(httpx2.AsyncBaseTransport):
        async def handle_async_request(self, req):
            body = json.loads(req.content)
            candidates = body.get('state', {}).get('candidates', [])
            answers = {}
            for name, entry in body['questions'].items():
                choice = ('review_after_reads' if name == 'post_read_plan' else
                          'discuss' if name == 'requested_work' else
                          'finish_retrieval' if name == 'operation' else
                          'include' if name.startswith('candidate_') and
                          candidates[int(name.split('_')[-1])]['kind'].startswith('Native Graph object') else 'exclude')
                answers[name] = {'type': 'choice', 'choice': choice, 'confidence': 1,
                                 'probabilities': {key: float(key == choice) for key in entry['criteria']}}
            return httpx2.Response(200, request=req, json={'model': 'jev-1.14.0', 'answers': answers,
                'usage': {'input_tokens': 37, 'output_tokens': 9}})

    writer_entered, writer_release = Event(), Event()
    class Writer(WriterWire):
        async def handle_async_request(self, req):
            if reset_during_writer:
                writer_entered.set()
                assert writer_release.wait(15)
            body = json.loads(req.content)
            messages = [item['content'] for item in body['input'] if item['content'] != 'Return JSON.']
            prose = messages[-1] if messages[-1].startswith('# Plan evidence\n\n') else None
            if prose is not None:
                match = re.search(r'^\[(assertion\d+)\] .+ · summary · .+$', prose, re.MULTILINE)
                assert match, prose
                handle = match[1]
            else:
                frames = [json.loads(message) for message in messages]
                frame = next(item for item in frames if 'native_assertions' in item and 'native_body_evidence' in item)
                handle = next(row['assertion_handle'] for row in frame['native_assertions']['records']
                              if row['assertion']['predicate'] == 'dnd5e:summary')
            output = {'schema': POLICY, 'limitations': [],
                'answer_segments': [{'kind': 'native_assertion_claim', 'text': 'A reports that B fled; uncertain.',
                                     'assertion_handles': [handle]}]}
            if 'requested_detail_gaps' in body['text']['format']['schema']['properties']:
                output['requested_detail_gaps'] = []
            self.text = json.dumps(output)
            return await super().handle_async_request(req)

    wire = Writer(None, '')
    class Harness(PlanJevHarness):
        def execute(self, adapter, **kwargs):
            wire.adapter = adapter
            return super().execute(adapter, **kwargs)
    monkeypatch.setattr(plan_jev_harness, 'default_plan_jev_runtime', lambda: Harness(
        decision_transport=Decisions(), writer_transport=wire,
        decision_api_key='synthetic', writer_api_key='synthetic'))
    from apps.live_control_server.services.workspace_document_registry import get_committed_playable_revision
    committed = get_committed_playable_revision(document)
    payload = {'schema': 'dmb_agent_turn_request_v1', 'client_thread_id': str(uuid4()), 'turn_id': str(uuid4()),
        'surface': {'surface_id': 'plan', 'instance_id': 'plan-main'},
        'owner_scope': {'kind': 'world', 'world_id': world.world_id},
        'primary_work': {'kind': 'plan', 'object_id': document, 'expected_revision': committed.object_revision,
                         'expected_revision_n': committed.revision_n, 'expected_content_sha256': committed.content_sha256},
        'client_work_state': 'saved_clean', 'graph_request': {'mode': 'none'}, 'graph_selection': None,
        'plan_context_policy': {'schema': 'dmb_plan_context_policy_v2', 'policy': 'auto_plan_world',
                                'graph_source': 'reviewed_native_graph'}, 'message': 'What did B do?'}
    binding = world.native_graph_binding
    reference = {'schema': 'dmb_authored_graph_reference_v1', 'managed_world_id': world.world_id,
                 'native_world_id': binding.native_world_id, 'binding_version': binding.binding_version,
                 'graph_revision': lane.repo.get_head(binding.native_world_id).head_revision_id,
                 'node_id': lane.ids['B'], 'label': 'B'}
    source_reference = {'schema': 'dmb_authored_source_reference_v1', 'managed_world_id': world.world_id,
        'native_world_id': binding.native_world_id, 'binding_version': binding.binding_version,
        'knowledge_revision': sources.json()['scope']['revision_id'], 'source_artifact_id': source_read['source_artifact_id'],
        'source_revision_id': source_read['source_revision_id'], 'evidence_ref_id': source_read['evidence_ref_id'],
        'content_sha256': item['source_revision']['content_sha256'], 'selection_kind': 'full_document',
        'section_id': None, 'label': 'Report'}
    payload['authored_references'] = {'schema': 'dmb_authored_references_v2', 'references': [reference, source_reference]}
    foreign = {**payload, 'authored_references': {'schema': 'dmb_authored_references_v2',
               'references': [{**reference, 'managed_world_id': 'foreign-world'}]}}
    assert client.post('/api/live/agent/turn', headers=headers, json=foreign).status_code in (400, 403, 422)
    for invalid in ({**reference, 'native_world_id': lane.world.world_id},
                    {**reference, 'binding_version': binding.binding_version + 1},
                    {**reference, 'graph_revision': 'rev:missing'}):
        invalid_payload = {**payload, 'turn_id': str(uuid4()),
                           'authored_references': {'schema': 'dmb_authored_references_v2', 'references': [invalid]}}
        invalid_response = client.post('/api/live/agent/turn', headers=headers, json=invalid_payload)
        assert invalid_response.status_code != 200, invalid_response.text
    for invalid in ({**source_reference, 'native_world_id': lane.world.world_id},
                    {**source_reference, 'content_sha256': '0' * 64},
                    {**source_reference, 'selection_kind': 'section', 'section_id': '0' * 64}):
        invalid_payload = {**payload, 'turn_id': str(uuid4()),
                           'authored_references': {'schema': 'dmb_authored_references_v2', 'references': [invalid]}}
        invalid_response = client.post('/api/live/agent/turn', headers=headers, json=invalid_payload)
        assert invalid_response.status_code != 200, invalid_response.text
    assert not wire.calls
    if reset_during_writer:
        with ThreadPoolExecutor(max_workers=1) as pool:
            pending = pool.submit(client.post, '/api/live/agent/turn', headers=headers, json=payload)
            try:
                assert writer_entered.wait(15)
                assert client.post('/api/live/index-graph/reset', headers=headers).status_code == 200
            finally:
                writer_release.set()
            answer = pending.result(timeout=15)
        assert answer.status_code != 200, answer.text
        assert 'A reports that B fled' not in answer.text
        from application_state.engine import connect
        with connect(application_state_dsn) as conn:
            assert conn.execute("SELECT count(*) FROM agent.turn WHERE world_id=%s AND status='completed' AND turn_id <> %s", (world.world_id, build_payload['turn_id'])).fetchone()[0] == 0
        return
    answer = client.post('/api/live/agent/turn', headers=headers, json=payload)
    assert answer.status_code == 200, answer.text
    assert 'B fled' in answer.json()['answer']['text']
    # Normal Play conversation with the same real guest session and synthetic providers.
    from application_state.content.service import create_world_plan, commit_plan
    from tests.application_state.play_runtime_helpers import V2_SOURCE_MARKDOWN
    from apps.live_control_server.services import play_jev_harness
    from apps.live_control_server.services.play_jev_harness import PlayJevHarness
    monkeypatch.setenv('DMB_HOSTED_GUEST_PLAY_ENABLED', '1')
    monkeypatch.setenv('DMB_HOSTED_GUEST_PLAY_BUDDY_ENABLED', '1')
    play_plan = create_world_plan(title='Guest Play', world_id=world.world_id)
    play_plan, play_revision = commit_plan(str(play_plan.work_object_id), V2_SOURCE_MARKDOWN,
        expected_world_id=world.world_id, expected_revision=play_plan.object_revision)
    run_id = str(uuid4())
    run_body = {'schema_version': 'dmb_world_session_create_v1', 'playable_artifact_id': str(play_plan.work_object_id),
        'expected_playable_revision': play_revision.revision_n, 'expected_playable_work_revision_id': str(play_revision.work_revision_id),
        'expected_playable_content_sha256': play_revision.content_sha256, 'entry_scene_id': 'scene:gate',
        'encounters': [{'scene_id': 'scene:gate', 'template': None}]}
    run_response = client.put(f'/api/live/world-play-runs/v2/{run_id}', params={'world_id': world.world_id}, headers=headers, json=run_body)
    assert run_response.status_code == 200, run_response.text
    play_entered, play_release = Event(), Event()
    class PlayWriter(WriterWire):
        async def handle_async_request(self, req):
            if reset_during_play:
                play_entered.set()
                assert play_release.wait(15)
            output = {'schema': POLICY, 'limitations': [], 'requested_detail_gaps': [],
                'answer_segments': [{'kind': 'native_assertion_claim', 'text': 'A reports that B fled; uncertain.', 'assertion_handles': ['assertion0']}]}
            properties = json.loads(req.content)['text']['format']['schema']['properties']
            self.text = json.dumps({key: value for key, value in output.items() if key in properties})
            return await super().handle_async_request(req)
    play_wire = PlayWriter(None, '')
    class PlayHarness(PlayJevHarness):
        def execute(self, adapter, **kwargs):
            play_wire.adapter = adapter
            return super().execute(adapter, **kwargs)
    monkeypatch.setattr(play_jev_harness, 'default_play_jev_runtime', lambda: PlayHarness(
        decision_transport=Decisions(), writer_transport=play_wire,
        decision_api_key='synthetic', writer_api_key='synthetic'))
    play_payload = {'schema': 'dmb_agent_turn_request_v1', 'client_thread_id': str(uuid4()), 'turn_id': str(uuid4()),
        'surface': {'surface_id': 'play', 'instance_id': run_id}, 'owner_scope': {'kind': 'world', 'world_id': world.world_id},
        'primary_work': {'kind': 'run', 'object_id': run_id, 'expected_revision': 1,
            'play_content_basis': {'edition_revision': 0, 'edition_revision_id': None, 'content_sha256': play_revision.content_sha256}},
        'play_target': {'beat_id': 'beat:arrival', 'scene_id': 'scene:gate', 'marker_grammar_version': 'v2'},
        'client_work_state': 'saved_clean', 'graph_request': {'mode': 'world', 'world_id': world.world_id,
            'campaign_id': None, 'revision_pin': None, 'focus': {'kind': 'none', 'session_id': None, 'campaign_id': None}},
        'graph_selection': None, 'message': 'What did B do?'}
    if reset_during_play:
        with ThreadPoolExecutor(max_workers=1) as pool:
            pending_play = pool.submit(client.post, '/api/live/agent/turn', headers=headers, json=play_payload)
            try:
                assert play_entered.wait(15)
                assert client.post('/api/live/index-graph/reset', headers=headers).status_code == 200
            finally:
                play_release.set()
            play_response = pending_play.result(timeout=15)
        assert play_response.status_code != 200, play_response.text
        assert 'A reports that B fled' not in play_response.text
        from application_state.engine import connect
        with connect(application_state_dsn) as conn:
            assert conn.execute("SELECT count(*) FROM agent.turn WHERE turn_id=%s AND status='completed'", (play_payload['turn_id'],)).fetchone()[0] == 0
        return
    play_response = client.post('/api/live/agent/turn', headers=headers, json=play_payload)
    assert play_response.status_code == 200, play_response.text
    assert 'B fled' in play_response.json()['answer']['text']
    from apps.live_control_server.services import guest_build_access
    from application_state.engine import connect
    from application_state.errors import ApplicationStateConflictError
    with connect(application_state_dsn) as conn:
        guest_build_access._lock_guest_session(request, conn, world.world_id)
        before = guest_build_access.guest_conversation_bytes(request, conn, world.world_id)
        updated = conn.execute("UPDATE agent.turn_context_trace SET payload=payload || jsonb_build_object('quota_probe', repeat('x', 4096)) WHERE turn_id=%s", (wire.adapter.turn.turn_id,))
        assert updated.rowcount == 1
        monkeypatch.setattr(guest_build_access, 'MAX_GUEST_CONVERSATION_BYTES', before + 1024)
        with pytest.raises(ApplicationStateConflictError):
            guest_build_access.guest_conversation_bytes(request, conn, world.world_id)
        conn.rollback()
    monkeypatch.setattr(guest_build_access, 'MAX_GUEST_CONVERSATION_BYTES', 32 * 1024 * 1024)
    from time import monotonic
    with connect(application_state_dsn) as conn:
        guest_build_access._lock_guest_session(request, conn, world.world_id)
        conn.execute("UPDATE agent.turn SET assistant_text=repeat('x', 30 * 1024 * 1024) WHERE turn_id=%s", (wire.adapter.turn.turn_id,))
        started = monotonic()
        measured = guest_build_access.guest_conversation_bytes(request, conn, world.world_id)
        elapsed = monotonic() - started
        assert 30 * 1024 * 1024 < measured < 32 * 1024 * 1024
        assert elapsed < 5
        conn.rollback()
    citation = f'/api/live/agent/worlds/{world.world_id}/conversation/turns/{wire.adapter.turn.turn_id}/native-assertion-sources/0'
    opened = client.get(citation)
    assert opened.status_code == 200, opened.text
    assert opened.json()['content'] == 'A reports that B fled; uncertain.\n'
    from application_state.unit_of_work import unit_of_work
    with unit_of_work() as conn:
        guest_build_access._lock_guest_session(request, conn, world.world_id)
        current_bytes = guest_build_access.guest_conversation_bytes(request, conn, world.world_id)
    monkeypatch.setattr(guest_build_access, 'MAX_GUEST_CONVERSATION_BYTES', current_bytes + 6000)
    def append_under_budget():
        try:
            with unit_of_work() as conn:
                guest_build_access._lock_guest_session(request, conn, world.world_id)
                conn.execute("UPDATE agent.turn SET assistant_text=assistant_text || repeat('x', 4000) WHERE turn_id=%s", (wire.adapter.turn.turn_id,))
                guest_build_access.guest_conversation_bytes(request, conn, world.world_id)
            return 'committed'
        except ApplicationStateConflictError:
            return 'rejected'
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(lambda _: append_under_budget(), range(2)))
    assert sorted(outcomes) == ['committed', 'rejected']
    monkeypatch.setattr(guest_build_access, 'MAX_GUEST_CONVERSATION_BYTES', 32 * 1024 * 1024)
    other = TestClient(app, base_url='https://buddy.example', headers={'Origin': 'https://buddy.example', 'Sec-Fetch-Site': 'same-origin'})
    other_session = other.post('/api/live/index-graph/session')
    assert other_session.status_code == 200
    other_world = other.post('/api/live/index-graph/world', headers={'X-DMB-Index-Graph-CSRF': other_session.json()['csrf_token']})
    assert other_world.status_code == 200
    assert other.get(f'/api/live/workspace-documents/{document}/committed-revision').status_code == 403
    other_headers = {'X-DMB-Index-Graph-CSRF': other_session.json()['csrf_token']}
    assert other.post('/api/live/native-graph-inspection/catalog', headers=other_headers, json=inspection_scope).status_code == 403
    assert other.post('/api/live/native-source-inspection/read', headers=other_headers, json=source_read).status_code == 403
    other_conversation = other.post(f"/api/live/agent/worlds/{other_world.json()['world_id']}/conversation/new",
        headers=other_headers, json={'command_id': str(uuid4()), 'expected_pointer_revision': 0,
                                    'expected_active_conversation_id': None})
    assert other_conversation.status_code == 200, other_conversation.text
    assert other.get(citation).status_code == 403
    from apps.live_control_server.services import native_graph_inspection as inspection_service
    inspection_entered, inspection_release = Event(), Event()
    original_catalog = inspection_service.catalog
    def paused_catalog(*args, **kwargs):
        result = original_catalog(*args, **kwargs)
        inspection_entered.set()
        assert inspection_release.wait(15)
        return result
    monkeypatch.setattr(inspection_service, 'catalog', paused_catalog)
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending_inspection = pool.submit(client.post, '/api/live/native-graph-inspection/catalog', headers=headers, json=inspection_scope)
        try:
            assert inspection_entered.wait(15)
            assert client.post('/api/live/index-graph/reset', headers=headers).status_code == 200
        finally:
            inspection_release.set()
        rejected = pending_inspection.result(timeout=15)
    assert rejected.status_code != 200
    assert 'catalogue' not in rejected.text
    assert client.post('/api/live/native-graph-inspection/catalog', headers=headers, json=inspection_scope).status_code in (401, 403, 409)
    assert client.post('/api/live/native-source-inspection/read', headers=headers, json=source_read).status_code in (401, 403, 409)
    assert client.get(citation).status_code in (401, 403)
    from application_state.index_graph.guest_conversation_cleanup import cleanup_expired_guest_conversation
    from application_state.errors import ApplicationStateConflictError
    from application_state.engine import connect
    with connect(application_state_dsn) as conn:
        assert conn.execute('SELECT count(*) FROM agent.conversation WHERE world_id=%s', (world.world_id,)).fetchone()[0] == 0
    other_id = str(UUID(other_world.json()['world_id'].removeprefix('guest-')))
    with pytest.raises(ApplicationStateConflictError):
        cleanup_expired_guest_conversation(other_id)
    other_scope = {'managed_world_id': other_world.json()['world_id'], 'scope_mode': 'world', 'campaign_id': None}
    other_catalog = other.post('/api/live/native-source-inspection/catalog', headers=other_headers, json=other_scope)
    assert other_catalog.status_code == 200
    other_item = other_catalog.json()['catalogue']['sources'][0]
    other_read = {'scope': other_catalog.json()['scope'], 'source_artifact_id': other_item['source_artifact']['source_artifact_id'],
                  'source_revision_id': other_item['source_revision']['source_revision_id'], 'evidence_ref_id': other_item['evidence_ref_ids'][0]}
    source_entered, source_release = Event(), Event()
    original_inspect = source_inspection_service.inspect
    def paused_source(*args, **kwargs):
        result = original_inspect(*args, **kwargs)
        source_entered.set()
        assert source_release.wait(15)
        return result
    monkeypatch.setattr(source_inspection_service, 'inspect', paused_source)
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending_source = pool.submit(other.post, '/api/live/native-source-inspection/read', headers=other_headers, json=other_read)
        try:
            assert source_entered.wait(15)
            assert other.post('/api/live/index-graph/reset', headers=other_headers).status_code == 200
        finally:
            source_release.set()
        rejected_source = pending_source.result(timeout=15)
    assert rejected_source.status_code != 200
    assert 'A reports that B fled' not in rejected_source.text
    cleanup_expired_guest_conversation(session_id)
    with connect(application_state_dsn) as conn:
        assert conn.execute('SELECT count(*) FROM agent.conversation WHERE world_id=%s', (world.world_id,)).fetchone()[0] == 0
        assert conn.execute('SELECT count(*) FROM agent.turn WHERE world_id=%s', (world.world_id,)).fetchone()[0] == 0
        assert conn.execute('SELECT count(*) FROM agent.conversation WHERE world_id=%s', (other_world.json()['world_id'],)).fetchone()[0] == 0


def test_guest_normal_turn_uses_guest_conversation(guests, monkeypatch, tmp_path):
    from tests.test_agent_turn_route import FakeRuntime, _payload
    from apps.live_control_server.routes import agent

    (client, csrf, world), (other, _, _) = guests[0]
    monkeypatch.setenv("DMB_HOSTED_GUEST_CONVERSATION_ENABLED", "1")
    monkeypatch.setenv("DMB_HOSTED_GUEST_TURN_ENABLED", "1")
    monkeypatch.setattr(agent, "_managed_world_root", lambda: tmp_path)
    monkeypatch.setattr(agent, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(agent, "session_dir", lambda: tmp_path / "sessions")
    runtime = FakeRuntime()
    client.app.state.agent_turn_runtime = runtime
    payload = {**_payload(), "owner_scope": {"kind": "world", "world_id": world}}
    headers = {"X-DMB-Index-Graph-CSRF": csrf}
    response = client.post("/api/live/agent/turn", json=payload, headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["answer"]["text"] == "A simple answer."
    assert len(runtime.invocations) == 1
    assert other.get(f"/api/live/agent/worlds/{world}/conversation").status_code == 403
    assert client.get(f"/api/live/agent/worlds/{world}/conversation").status_code == 200
    messages = f"/api/live/agent/worlds/{world}/conversations/active/messages?limit=50"
    page = client.get(messages)
    assert page.status_code == 200, page.text
    assert page.json()['messages'][0]['assistant_text'] == 'A simple answer.'
    assert other.get(messages).status_code == 403


def test_guest_storage_limit_rejects_provider_answer_without_replaying(guests, monkeypatch, tmp_path):
    from tests.test_agent_turn_route import FakeRuntime, _payload
    from apps.live_control_server.routes import agent
    from apps.live_control_server.services import guest_build_access
    from application_state.agent_conversation import AgentConversationService

    (client, csrf, world), _ = guests[0]
    monkeypatch.setenv('DMB_HOSTED_GUEST_CONVERSATION_ENABLED', '1')
    monkeypatch.setenv('DMB_HOSTED_GUEST_TURN_ENABLED', '1')
    monkeypatch.setattr(agent, '_managed_world_root', lambda: tmp_path)
    monkeypatch.setattr(agent, 'repo_root', lambda: tmp_path)
    monkeypatch.setattr(agent, 'session_dir', lambda: tmp_path / 'sessions')
    class LimitAfterProvider(FakeRuntime):
        def run(self, invocation):
            result = super().run(invocation)
            monkeypatch.setattr(guest_build_access, 'MAX_GUEST_CONVERSATION_BYTES', 1)
            return result
    runtime = LimitAfterProvider()
    client.app.state.agent_turn_runtime = runtime
    payload = {**_payload(), 'owner_scope': {'kind': 'world', 'world_id': world}}
    headers = {'X-DMB-Index-Graph-CSRF': csrf}
    response = client.post('/api/live/agent/turn', json=payload, headers=headers)
    assert response.status_code != 200, response.text
    assert 'A simple answer.' not in response.text
    assert len(runtime.invocations) == 1
    monkeypatch.setattr(guest_build_access, 'MAX_GUEST_CONVERSATION_BYTES', 32 * 1024 * 1024)
    service = AgentConversationService()
    conversation = service.get_active_conversation(world)
    turns = service.list_turns(world, conversation.conversation_id)
    assert len(turns) == 1 and turns[0].status != 'completed'
    client.post('/api/live/agent/turn', json=payload, headers=headers)
    assert len(runtime.invocations) == 1


def test_guest_reset_during_turn_does_not_return_or_complete_answer(guests, monkeypatch, tmp_path, application_state_dsn):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    from application_state.engine import connect
    from tests.test_agent_turn_route import FakeRuntime, _payload
    from apps.live_control_server.routes import agent

    (client, csrf, world), _ = guests[0]
    monkeypatch.setenv("DMB_HOSTED_GUEST_CONVERSATION_ENABLED", "1")
    monkeypatch.setenv("DMB_HOSTED_GUEST_TURN_ENABLED", "1")
    monkeypatch.setattr(agent, "_managed_world_root", lambda: tmp_path)
    monkeypatch.setattr(agent, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(agent, "session_dir", lambda: tmp_path / "sessions")
    entered, release = Event(), Event()

    class WaitingRuntime(FakeRuntime):
        def run(self, invocation):
            entered.set()
            assert release.wait(15)
            return super().run(invocation)

    client.app.state.agent_turn_runtime = WaitingRuntime()
    payload = {**_payload(), "owner_scope": {"kind": "world", "world_id": world}}
    headers = {"X-DMB-Index-Graph-CSRF": csrf}
    with ThreadPoolExecutor(max_workers=1) as pool:
        turn = pool.submit(client.post, "/api/live/agent/turn", json=payload, headers=headers)
        try:
            assert entered.wait(15)
            reset = client.post("/api/live/index-graph/reset", headers=headers)
            assert reset.status_code == 200, reset.text
        finally:
            release.set()
        response = turn.result(timeout=15)
    assert response.status_code != 200, response.text
    assert "A simple answer." not in response.text
    with connect(application_state_dsn) as conn:
        completed = conn.execute("SELECT count(*) FROM agent.turn WHERE world_id = %s AND status = 'completed'", (world,)).fetchone()[0]
    assert completed == 0


def test_guest_image_generation_and_document_reopen(guests, monkeypatch):
    from io import BytesIO
    from types import SimpleNamespace
    from unittest.mock import AsyncMock
    from PIL import Image
    from generationengine import GeneratedImage
    from apps.live_control_server.services import guest_media_access
    monkeypatch.setenv("DMB_HOSTED_GUEST_MEDIA_ENABLED", "1")
    monkeypatch.setenv("FAL_KEY", "synthetic")
    image = BytesIO()
    Image.new("RGB", (4, 4), "blue").save(image, format="PNG")
    provider = SimpleNamespace(generate_image=AsyncMock(return_value=SimpleNamespace(
        images=[GeneratedImage(content=image.getvalue(), media_type="image/png")],
        observation=SimpleNamespace(model_dump=lambda **_: {"provider": "fake"}))), aclose=AsyncMock())
    monkeypatch.setattr(media_images, "_image_client", lambda: provider)
    (first, token, world), (second, other_token, other_world) = guests[0]
    headers = {"X-DMB-Index-Graph-CSRF": token}
    body = {"prompt": "A blue lantern", "model": "gpt-image-2.5-flare"}
    path = "/api/live/media/images/generate"
    assert first.post(path, params={"world_id": world}, json=body).status_code == 403
    assert first.post(path, params={"world_id": world}, headers={**headers, "Origin": "https://bad.example"}, json=body).status_code == 403
    assert second.post(path, params={"world_id": world}, headers={"X-DMB-Index-Graph-CSRF": other_token}, json=body).status_code == 403
    generated = first.post(path, params={"world_id": world}, headers=headers, json=body)
    assert generated.status_code == 200, generated.text
    asset = generated.json()["images"][0]["asset_id"]
    monkeypatch.setattr(guest_media_access, "MAX_GUEST_ASSET_BYTES", len(image.getvalue()))
    assert first.post(path, params={"world_id": world}, headers=headers, json=body).status_code == 409
    monkeypatch.setattr(guest_media_access, "MAX_GUEST_ASSET_BYTES", 20 * 1024 * 1024)
    monkeypatch.setattr(guest_media_access, "MAX_GUEST_ASSETS", 1)
    assert first.post(path, params={"world_id": world}, headers=headers, json=body).status_code == 409
    provider.generate_image.assert_awaited_once()
    assert first.get(f"/api/live/media/images/{asset}/metadata").status_code == 200
    assert second.get(f"/api/live/media/images/{asset}/original").status_code == 403
    page = first.post("/api/live/workspace-documents", headers=headers, json={"title": "Guest page", "world_id": world, "campaign_id": world,
        "kind": "worldbuilding_source", "source_domain": "worldbuilding", "document_class": "lore", "authority_state": "draft", "visibility_state": "internal"})
    assert page.status_code == 200, page.text
    doc = page.json()["document_id"]
    markdown = f"# A clue\n\n![Lantern](dmb-media:{asset})\n"
    prepared = first.post("/api/live/tiptap/markdown-write/prepare", headers=headers, json={"document_id": doc, "markdown": markdown})
    assert prepared.status_code == 200, prepared.text
    saved = first.post("/api/live/tiptap/markdown-write/commit", headers=headers, json={"document_id": doc, "markdown": markdown,
        "writer_confirm_token": prepared.json()["writer_confirm_token"], "expected_revision": prepared.json()["registry_revision"]})
    assert saved.status_code == 200, saved.text
    assert asset in first.get(f"/api/live/workspace-documents/{doc}/snapshot").json()["markdown"]
    assert first.post("/api/live/index-graph/reset", headers=headers).status_code == 200
    assert first.get(f"/api/live/media/images/{asset}/original").status_code in (401, 403)


def test_guest_image_reset_during_generation_does_not_retain(guests, application_state_dsn, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from io import BytesIO
    from threading import Event
    from types import SimpleNamespace
    from unittest.mock import AsyncMock
    from PIL import Image
    from generationengine import GeneratedImage
    from application_state.engine import connect
    from apps.live_control_server.services.hosted_native_graph_access import hosted_world_media_owner
    monkeypatch.setenv("DMB_HOSTED_GUEST_MEDIA_ENABLED", "1")
    monkeypatch.setenv("FAL_KEY", "synthetic")
    entered, release = Event(), Event()
    data = BytesIO()
    Image.new("RGB", (4, 4), "blue").save(data, format="PNG")
    async def generate(_request):
        entered.set()
        if not release.wait(10): raise RuntimeError("image reset test timed out")
        return SimpleNamespace(images=[GeneratedImage(content=data.getvalue(), media_type="image/png")],
                               observation=SimpleNamespace(model_dump=lambda **_: {"provider": "fake"}))
    provider = SimpleNamespace(generate_image=generate, aclose=AsyncMock())
    monkeypatch.setattr(media_images, "_image_client", lambda: provider)
    (client, token, world), _ = guests[0]
    headers = {"X-DMB-Index-Graph-CSRF": token}
    with ThreadPoolExecutor(max_workers=2) as pool:
        pending = pool.submit(client.post, "/api/live/media/images/generate", params={"world_id": world}, headers=headers,
                              json={"prompt": "A blue lantern", "model": "gpt-image-2.5-flare"})
        try:
            assert entered.wait(10)
            duplicate = client.post("/api/live/media/images/generate", params={"world_id": world}, headers=headers,
                                    json={"prompt": "Another lantern", "model": "gpt-image-2.5-flare"})
            assert duplicate.status_code == 409
            assert client.post("/api/live/index-graph/reset", headers=headers).status_code == 200
        finally:
            release.set()
        assert pending.result(timeout=10).status_code in (401, 403, 409)
    with connect(application_state_dsn) as conn:
        assert conn.execute("SELECT count(*) FROM media.asset WHERE owner_id = %s", (hosted_world_media_owner(world),)).fetchone()[0] == 0


def test_guest_image_retention_serializes_with_reset(guests, application_state_dsn, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from io import BytesIO
    from threading import Event
    from types import SimpleNamespace
    from unittest.mock import AsyncMock
    import time
    from PIL import Image
    from generationengine import GeneratedImage
    from application_state.engine import connect
    from apps.live_control_server.services import guest_media_access
    monkeypatch.setenv("DMB_HOSTED_GUEST_MEDIA_ENABLED", "1")
    monkeypatch.setenv("FAL_KEY", "synthetic")
    data = BytesIO()
    Image.new("RGB", (4, 4), "blue").save(data, format="PNG")
    provider = SimpleNamespace(generate_image=AsyncMock(return_value=SimpleNamespace(
        images=[GeneratedImage(content=data.getvalue(), media_type="image/png")],
        observation=SimpleNamespace(model_dump=lambda **_: {"provider": "fake"}))), aclose=AsyncMock())
    monkeypatch.setattr(media_images, "_image_client", lambda: provider)
    entered, release = Event(), Event()
    original = guest_media_access.authorize_guest_image_stage
    def hold(*args):
        original(*args)
        entered.set()
        if not release.wait(10): raise RuntimeError("image retention test timed out")
    monkeypatch.setattr(guest_media_access, "authorize_guest_image_stage", hold)
    (client, token, world), _ = guests[0]
    headers = {"X-DMB-Index-Graph-CSRF": token}
    with ThreadPoolExecutor(max_workers=2) as pool:
        pending = pool.submit(client.post, "/api/live/media/images/generate", params={"world_id": world}, headers=headers,
                              json={"prompt": "A lantern", "model": "gpt-image-2.5-flare"})
        try:
            assert entered.wait(10)
            reset = pool.submit(client.post, "/api/live/index-graph/reset", headers=headers)
            deadline = time.monotonic() + 5
            with connect(application_state_dsn) as conn:
                while time.monotonic() < deadline:
                    conn.execute('SELECT pg_stat_clear_snapshot()')
                    waiting = conn.execute("SELECT count(*) FROM pg_stat_activity WHERE datname = current_database() AND wait_event_type = 'Lock'").fetchone()[0]
                    if waiting: break
                    time.sleep(0.05)
            assert waiting > 0
        finally:
            release.set()
        assert pending.result(timeout=10).status_code in (200, 401, 403)
        assert reset.result(timeout=10).status_code == 200


def test_guest_play_run_is_bound_to_session(guests, monkeypatch, tmp_path):
    from application_state.content.service import create_world_plan, commit_plan
    from tests.application_state.play_runtime_helpers import V2_SOURCE_MARKDOWN, gate_progress
    from apps.live_control_server.services import guest_build_access
    from apps.live_control_server.services.play_run_edition_structure import structure_signature
    from uuid import uuid4
    monkeypatch.setenv("DMB_HOSTED_GUEST_PLAN_ENABLED", "1")
    monkeypatch.setenv("DMB_HOSTED_GUEST_PLAY_ENABLED", "1")
    contexts, _, _ = guests
    (first, token, world), (second, other_token, other_world) = contexts
    plan = create_world_plan(title="Guest play", world_id=world)
    plan, revision = commit_plan(str(plan.work_object_id), V2_SOURCE_MARKDOWN,
                                 expected_world_id=world, expected_revision=plan.object_revision)
    run = str(uuid4())
    path = f"/api/live/world-play-runs/v2/{run}"
    scenes = structure_signature(V2_SOURCE_MARKDOWN)["membership"]["scenes"]
    body = {"schema_version": "dmb_world_session_create_v1", "playable_artifact_id": str(plan.work_object_id),
            "expected_playable_revision": revision.revision_n, "expected_playable_work_revision_id": str(revision.work_revision_id),
            "expected_playable_content_sha256": revision.content_sha256, "entry_scene_id": scenes[0]["scene_id"],
            "encounters": [{"scene_id": scene["scene_id"], "template": None} for scene in scenes]}
    headers = {"X-DMB-Index-Graph-CSRF": token}
    source = {key: body[key] for key in ("playable_artifact_id", "expected_playable_revision", "expected_playable_work_revision_id", "expected_playable_content_sha256")}
    revision_read = first.get(f"/api/live/workspace-documents/{plan.work_object_id}/committed-revision")
    assert revision_read.status_code == 200, revision_read.text
    preview = first.post("/api/live/world-play-runs/v2/preparation", params={"world_id": world}, headers=headers, json=source)
    assert preview.status_code == 200, preview.text
    assert first.put(path, params={"world_id": world}, json=body).status_code == 403
    assert first.put(path, params={"world_id": world}, headers={**headers, "Origin": "https://bad.example"}, json=body).status_code == 403
    assert first.get(path, params=[("world_id", world), ("world_id", world)]).status_code in (400, 403)
    assert second.put(path, params={"world_id": world}, headers={"X-DMB-Index-Graph-CSRF": other_token}, json=body).status_code == 403
    created = first.put(path, params={"world_id": world}, headers=headers, json=body)
    assert created.status_code == 200, created.text
    monkeypatch.setattr(guest_build_access, "MAX_GUEST_RUNS", 1)
    assert first.put(path, params={"world_id": world}, headers=headers, json=body).status_code == 200
    assert first.put(f"/api/live/world-play-runs/v2/{uuid4()}", params={"world_id": world}, headers=headers, json=body).status_code == 409
    progress = first.put(f"{path}/progress", params={"world_id": world}, headers=headers,
                         json={"expected_run_revision": 1, "progress": gate_progress().model_dump(mode="json")})
    assert progress.status_code == 200, progress.text
    assert progress.json()["progress"]["selections"]["choice:route"] == "option:fire"
    assert first.put("/api/live/world-play-runs/v2/active", params={"world_id": world}, headers=headers,
                     json={"run_id": run}).status_code == 200
    reopened = first.get(path, params={"world_id": world})
    assert reopened.status_code == 200
    assert reopened.json()["progress"]["selections"]["choice:route"] == "option:fire"
    assert first.get(f"{path}/reference-manifest", params={"world_id": world}).status_code == 200
    assert first.get(f"{path}/content", params={"world_id": world}).status_code == 200
    assert second.get(path, params={"world_id": other_world}).status_code in (403, 404)
    # The actual Play turn work resolver must bind the exact Run and edition
    # to the session World, not just trust guest admission.
    from tests.test_agent_turn_route import _play_turn_payload
    from apps.live_control_server.models.agent_turn import AgentTurnRequest
    from apps.live_control_server.routes import agent
    from apps.live_control_server.services.agent_turn_service import AgentTurnServiceError
    monkeypatch.setattr(agent, '_managed_world_root', lambda: tmp_path)
    payload = _play_turn_payload(revision=progress.json()['run_revision'])
    payload['owner_scope'] = {'kind': 'world', 'world_id': world}
    payload['primary_work']['object_id'] = run
    payload['primary_work']['play_content_basis']['content_sha256'] = revision.content_sha256
    payload['graph_request'] = {'mode': 'world', 'world_id': world, 'campaign_id': None,
        'revision_pin': None, 'focus': {'kind': 'none', 'session_id': None, 'campaign_id': None}}
    turn = AgentTurnRequest.model_validate(payload)
    resolved = agent._work_resolver(turn, {'kind': 'world', 'id': world})
    assert resolved.object_id == run and resolved.world_id == world
    with pytest.raises(AgentTurnServiceError, match='unavailable|stale'):
        agent._work_resolver(turn, {'kind': 'world', 'id': other_world})
    stale = turn.model_copy(update={'primary_work': turn.primary_work.model_copy(
        update={'expected_revision': progress.json()['run_revision'] + 1})})
    with pytest.raises(AgentTurnServiceError, match='stale'):
        agent._work_resolver(stale, {'kind': 'world', 'id': world})
    assert first.post("/api/live/index-graph/reset", headers=headers).status_code == 200
    assert first.get(path, params={"world_id": world}).status_code in (401, 403)


@pytest.mark.parametrize("operation", ["create", "progress", "active"])
def test_guest_play_write_serializes_with_reset(guests, application_state_dsn, monkeypatch, operation):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    from uuid import uuid4
    import time
    from application_state.content.service import create_world_plan, commit_plan
    from application_state.engine import connect
    from apps.live_control_server.services import guest_build_access
    from apps.live_control_server.services.play_run_edition_structure import structure_signature
    from tests.application_state.play_runtime_helpers import V2_SOURCE_MARKDOWN, gate_progress
    monkeypatch.setenv("DMB_HOSTED_GUEST_PLAN_ENABLED", "1")
    monkeypatch.setenv("DMB_HOSTED_GUEST_PLAY_ENABLED", "1")
    (client, token, world), _ = guests[0]
    plan = create_world_plan(title="Guest play", world_id=world)
    plan, revision = commit_plan(str(plan.work_object_id), V2_SOURCE_MARKDOWN, expected_world_id=world, expected_revision=plan.object_revision)
    scenes = structure_signature(V2_SOURCE_MARKDOWN)["membership"]["scenes"]
    body = {"schema_version": "dmb_world_session_create_v1", "playable_artifact_id": str(plan.work_object_id),
            "expected_playable_revision": revision.revision_n, "expected_playable_work_revision_id": str(revision.work_revision_id),
            "expected_playable_content_sha256": revision.content_sha256, "entry_scene_id": scenes[0]["scene_id"],
            "encounters": [{"scene_id": scene["scene_id"], "template": None} for scene in scenes]}
    headers = {"X-DMB-Index-Graph-CSRF": token}
    run_id = str(uuid4())
    path = f"/api/live/world-play-runs/v2/{run_id}"
    if operation != "create":
        created = client.put(path, params={"world_id": world}, headers=headers, json=body)
        assert created.status_code == 200, created.text
    entered, release = Event(), Event()
    original = guest_build_access._lock_guest_session
    def hold(*args, **kwargs):
        original(*args, **kwargs)
        entered.set()
        if not release.wait(10): raise RuntimeError("guest Play race test timed out")
    monkeypatch.setattr(guest_build_access, "_lock_guest_session", hold)
    with ThreadPoolExecutor(max_workers=2) as pool:
        target = path if operation == "create" else f"{path}/progress" if operation == "progress" else "/api/live/world-play-runs/v2/active"
        payload = body if operation == "create" else {"expected_run_revision": 1, "progress": gate_progress().model_dump(mode="json")} if operation == "progress" else {"run_id": run_id}
        create = pool.submit(client.put, target, params={"world_id": world}, headers=headers, json=payload)
        try:
            assert entered.wait(10)
            reset = pool.submit(client.post, "/api/live/index-graph/reset", headers=headers)
            deadline = time.monotonic() + 5
            with connect(application_state_dsn) as connection:
                while time.monotonic() < deadline:
                    connection.execute('SELECT pg_stat_clear_snapshot()')
                    waiting = connection.execute("SELECT count(*) FROM pg_stat_activity WHERE datname = current_database() AND wait_event_type = 'Lock'").fetchone()[0]
                    if waiting: break
                    time.sleep(0.05)
            assert waiting > 0
        finally:
            release.set()
        assert create.result(timeout=10).status_code in (200, 401, 403)
        assert reset.result(timeout=10).status_code == 200


def test_guest_create_save_and_reopen_isolated_document(guests):
    contexts, repo, source = guests
    (first, token, world), (second, other_token, other_world) = contexts
    headers = {"X-DMB-Index-Graph-CSRF": token}
    body = {"title": "Guest notes", "world_id": world, "campaign_id": world, "kind": "worldbuilding_source", "source_domain": "worldbuilding", "document_class": "lore", "authority_state": "draft", "visibility_state": "internal"}
    created = first.post("/api/live/workspace-documents", headers=headers, json=body)
    assert created.status_code == 200, created.text
    doc = created.json()["document_id"]
    assert second.get(f"/api/live/workspace-documents/{doc}").status_code == 403
    assert second.get("/api/live/workspace-documents/pages/inventory", params={"world_id": world}).status_code == 403
    prepared = first.post("/api/live/tiptap/markdown-write/prepare", headers=headers,
                          json={"document_id": doc, "markdown": "# Guest note\n\nA fresh clue."})
    assert prepared.status_code == 200, prepared.text
    receipt = prepared.json()
    committed = first.post("/api/live/tiptap/markdown-write/commit", headers=headers,
                           json={"document_id": doc, "markdown": "# Guest note\n\nA fresh clue.",
                                 "writer_confirm_token": receipt["writer_confirm_token"],
                                 "expected_revision": receipt["registry_revision"]})
    assert committed.status_code == 200, committed.text
    opened = first.get(f"/api/live/workspace-documents/{doc}/snapshot")
    assert opened.status_code == 200, opened.text
    assert "A fresh clue." in opened.json()["markdown"]
    assert second.get(f"/api/live/workspace-documents/{doc}/snapshot").status_code == 403
    assert second.post("/api/live/tiptap/markdown-write/prepare", headers={"X-DMB-Index-Graph-CSRF": other_token},
                       json={"document_id": doc, "markdown": "Cross-session attempt"}).status_code == 403
    assert second.post("/api/live/tiptap/markdown-write/commit", headers={"X-DMB-Index-Graph-CSRF": other_token},
                       json={"document_id": doc, "markdown": "# Guest note\n\nA fresh clue.",
                             "writer_confirm_token": receipt["writer_confirm_token"], "expected_revision": receipt["registry_revision"]}).status_code == 403
    assert repo.get_head(source["world_id"]).head_revision_id == source["revision_id"]
    reset = first.post("/api/live/index-graph/reset", headers=headers)
    assert reset.status_code == 200
    assert first.get(f"/api/live/workspace-documents/{doc}").status_code in (401, 403)
    assert other_world != world


def test_guest_plan_create_and_isolation(guests, monkeypatch):
    from apps.live_control_server.services import guest_build_access
    monkeypatch.setenv("DMB_HOSTED_GUEST_PLAN_ENABLED", "1")
    contexts, _, _ = guests
    (first, token, world), (second, _, other_world) = contexts
    headers = {"X-DMB-Index-Graph-CSRF": token}
    path = "/api/live/workspace-documents/world-plans"
    body = {"schema_version": "dmb_workspace_document_create_v2", "scope_mode": "world", "world_id": world, "title": "Guest plan"}
    assert first.post(path, json=body).status_code == 403
    assert first.post(path, headers=headers, json={**body, "world_id": other_world}).status_code == 403
    assert first.post(path, headers={**headers, "Origin": "https://bad.example"}, json=body).status_code == 403
    assert first.get(path, params=[("world_id", world), ("world_id", world)]).status_code in (400, 403)
    created = first.post(path, headers=headers, json=body)
    assert created.status_code == 200, created.text
    doc = created.json()["document_id"]
    inventory = first.get(path, params={"world_id": world})
    assert inventory.status_code == 200, inventory.text
    assert any(record["document_id"] == doc for record in inventory.json()["records"])
    draft = {"document_id": doc, "markdown": "# Guest plan\n\nA new clue.", "scope_mode": "world", "world_id": world,
             "schema_version": "dmb_tiptap_markdown_write_prepare_v2"}
    prepared = first.post("/api/live/tiptap/markdown-write/prepare", headers=headers, json=draft)
    assert prepared.status_code == 200, prepared.text
    assert second.post("/api/live/tiptap/markdown-write/prepare", headers={"X-DMB-Index-Graph-CSRF": contexts[1][1]}, json=draft).status_code == 403
    receipt = prepared.json()
    commit = {**draft, "schema_version": "dmb_tiptap_markdown_write_commit_v2",
              "writer_confirm_token": receipt["writer_confirm_token"], "expected_revision": receipt["registry_revision"]}
    monkeypatch.setattr(guest_build_access, "MAX_GUEST_SAVED_BYTES", 1)
    assert first.post("/api/live/tiptap/markdown-write/commit", headers=headers, json=commit).status_code == 409
    monkeypatch.setattr(guest_build_access, "MAX_GUEST_SAVED_BYTES", 16 * 1024 * 1024)
    saved = first.post("/api/live/tiptap/markdown-write/commit", headers=headers, json=commit)
    assert saved.status_code == 200, saved.text
    monkeypatch.setattr(guest_build_access, "MAX_GUEST_SAVED_BYTES", 1)
    assert first.post("/api/live/tiptap/markdown-write/commit", headers=headers, json=commit).status_code == 200
    snapshot = first.get(f"/api/live/workspace-documents/{doc}/snapshot")
    assert snapshot.status_code == 200, snapshot.text
    assert "A new clue." in snapshot.json()["markdown"]
    assert second.get(f"/api/live/workspace-documents/{doc}/snapshot").status_code == 403
    assert second.get(path, params={"world_id": world}).status_code == 403
    assert first.post("/api/live/index-graph/reset", headers=headers).status_code == 200
    assert first.get(f"/api/live/workspace-documents/{doc}/snapshot").status_code in (401, 403)


def test_released_pages_open_through_ordinary_guest_build(guests, monkeypatch, tmp_path, application_state_dsn):
    import hashlib
    import json

    contexts, _, source = guests
    (first, token, world), (second, _, other_world) = contexts
    bundle = tmp_path / 'released-documents.json'
    bundle.write_text(json.dumps({'version': 1, 'graph_space': source['world_id'],
                                  'graph_revision': source['revision_id'],
                                  'documents': [{'title': 'Apprentice', 'markdown': 'A source.'}]}))
    monkeypatch.setenv('DMB_GUEST_DOCUMENT_BUNDLE', str(bundle))
    monkeypatch.setenv('DMB_GUEST_DOCUMENT_BUNDLE_SHA256', hashlib.sha256(bundle.read_bytes()).hexdigest())
    inventory = first.get('/api/live/workspace-documents/pages/inventory', params={'world_id': world})
    assert inventory.status_code == 200, inventory.text
    record, = inventory.json()['records']
    assert record['title'] == 'Apprentice'
    doc = record['document_id']
    snapshot = first.get(f'/api/live/workspace-documents/{doc}/snapshot')
    assert snapshot.status_code == 200, snapshot.text
    assert 'A source.' in snapshot.json()['markdown']
    assert snapshot.json()['record']['document_class'] == 'lore'
    # Simulate a session seeded before the metadata fix. Reopening the same
    # World repairs the seeded page without changing its revision or content.
    from application_state.engine import connect
    with connect(application_state_dsn) as conn:
        conn.execute('UPDATE content.page_metadata SET document_class = NULL WHERE work_object_id = %s::uuid', (doc,))
        conn.commit()
    reopened = first.post('/api/live/index-graph/world', headers={'X-DMB-Index-Graph-CSRF': token})
    assert reopened.status_code == 200, reopened.text
    repaired = first.get(f'/api/live/workspace-documents/{doc}/snapshot').json()
    assert repaired['record']['document_class'] == 'lore'
    assert repaired['loaded_revision'] == snapshot.json()['loaded_revision']
    assert repaired['markdown'] == snapshot.json()['markdown']
    # Exercise the boundary that rejected the live guest Buddy question.
    from types import SimpleNamespace
    from apps.live_control_server.routes import agent
    monkeypatch.setattr(agent, '_managed_world_root', lambda: tmp_path)
    locator = SimpleNamespace(kind='build', object_id=doc, expected_revision=repaired['loaded_revision'],
                              expected_content_sha256=hashlib.sha256(repaired['markdown'].encode()).hexdigest())
    body = SimpleNamespace(primary_work=locator, surface=SimpleNamespace(surface_id='build'),
                           build_image_move_capture=None)
    assert agent._build_work_resolver(body, {'kind': 'world', 'id': world}).object_id == doc
    with connect(application_state_dsn) as conn:
        conn.execute("UPDATE content.page_metadata SET document_class = 'adventure' WHERE work_object_id = %s::uuid", (doc,))
        conn.commit()
    assert first.post('/api/live/index-graph/world', headers={'X-DMB-Index-Graph-CSRF': token}).status_code == 200
    assert first.get(f'/api/live/workspace-documents/{doc}/snapshot').json()['record']['document_class'] == 'adventure'
    assert second.get(f'/api/live/workspace-documents/{doc}/snapshot').status_code == 403
    other = second.get('/api/live/workspace-documents/pages/inventory', params={'world_id': other_world})
    assert other.status_code == 200 and other.json()['records'][0]['document_id'] != doc
    assert first.post('/api/live/index-graph/reset', headers={'X-DMB-Index-Graph-CSRF': token}).status_code == 200
    assert first.get(f'/api/live/workspace-documents/{doc}/snapshot').status_code in (401, 403)


def test_guest_build_rejects_cross_world_and_missing_csrf(guests):
    (first, token, world), (second, other_token, other_world) = guests[0]
    body = {"title": "Foreign", "world_id": other_world, "campaign_id": other_world, "kind": "worldbuilding_source", "source_domain": "worldbuilding", "document_class": "lore", "authority_state": "draft", "visibility_state": "internal"}
    assert first.post("/api/live/workspace-documents", headers={"X-DMB-Index-Graph-CSRF": token}, json=body).status_code == 403
    body.update(world_id=world, campaign_id=world)
    assert first.post("/api/live/workspace-documents", json=body).status_code == 403
    assert first.post("/api/live/workspace-documents", headers={"Origin": "https://bad.example", "X-DMB-Index-Graph-CSRF": token}, json=body).status_code == 403
    assert first.get("/api/live/world-containers").status_code == 401
    assert first.get("/api/live/workspace-documents/pages/inventory", params=[("world_id", world), ("world_id", other_world)]).status_code in (400, 403)


def test_guest_document_limit_is_atomic_under_concurrent_creates(guests, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from apps.live_control_server.services import guest_build_access

    (client, token, world), _ = guests[0]
    monkeypatch.setattr(guest_build_access, "MAX_GUEST_PAGES", 1)
    body = {"title": "Guest note", "world_id": world, "campaign_id": world,
            "kind": "worldbuilding_source", "source_domain": "worldbuilding", "document_class": "lore",
            "authority_state": "draft", "visibility_state": "internal"}
    def create():
        return client.post("/api/live/workspace-documents", headers={"X-DMB-Index-Graph-CSRF": token}, json=body)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: create(), range(2)))
    assert sorted(response.status_code for response in results) == [200, 409]
    inventory = client.get("/api/live/workspace-documents/pages/inventory", params={"world_id": world})
    assert inventory.status_code == 200
    assert len(inventory.json()["records"]) == 1


def test_guest_revision_budget_does_not_replace_saved_content(guests, monkeypatch):
    from apps.live_control_server.services import guest_build_access

    (client, token, world), _ = guests[0]
    monkeypatch.setattr(guest_build_access, "MAX_GUEST_REVISIONS", 1)
    headers = {"X-DMB-Index-Graph-CSRF": token}
    body = {"title": "Guest note", "world_id": world, "campaign_id": world,
            "kind": "worldbuilding_source", "source_domain": "worldbuilding", "document_class": "lore",
            "authority_state": "draft", "visibility_state": "internal"}
    document = client.post("/api/live/workspace-documents", headers=headers, json=body).json()["document_id"]
    submitted = []
    def save(text):
        prepared = client.post("/api/live/tiptap/markdown-write/prepare", headers=headers,
                               json={"document_id": document, "markdown": text})
        assert prepared.status_code == 200
        receipt = prepared.json()
        packet = {"document_id": document, "markdown": text,
                  "writer_confirm_token": receipt["writer_confirm_token"],
                  "expected_revision": receipt["registry_revision"]}
        submitted.append(packet)
        return client.post("/api/live/tiptap/markdown-write/commit", headers=headers, json=packet)
    first_save = save("First saved version")
    assert first_save.status_code == 200
    assert client.post("/api/live/tiptap/markdown-write/commit", headers=headers, json=submitted[0]).status_code == 200
    assert save("Second saved version").status_code == 409
    snapshot = client.get(f"/api/live/workspace-documents/{document}/snapshot")
    assert snapshot.status_code == 200
    assert snapshot.json()["markdown"] == "First saved version\n"


def test_authenticated_identity_does_not_fall_back_to_guest_cookie(guests):
    from apps.live_control_server.services.dms_principal import DmsPrincipal
    (client, token, world), _ = guests[0]
    async def signed_in(_request):
        return DmsPrincipal(subject="different-owner")
    client.app.state.dms_principal_resolver = signed_in
    body = {"title": "Guest note", "world_id": world, "campaign_id": world,
            "kind": "worldbuilding_source", "source_domain": "worldbuilding", "document_class": "lore",
            "authority_state": "draft", "visibility_state": "internal"}
    assert client.post("/api/live/workspace-documents", headers={"X-DMB-Index-Graph-CSRF": token}, json=body).status_code == 403


@pytest.mark.parametrize("kind", ["page", "plan"])
def test_reset_waits_for_guest_commit_transaction(guests, application_state_dsn, monkeypatch, kind):
    import time
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    from application_state.engine import connect
    from apps.live_control_server.services import guest_build_access

    (client, token, world), _ = guests[0]
    headers = {"X-DMB-Index-Graph-CSRF": token}
    if kind == "plan":
        monkeypatch.setenv("DMB_HOSTED_GUEST_PLAN_ENABLED", "1")
        body = {"title": "Race plan", "world_id": world, "scope_mode": "world"}
        doc = client.post("/api/live/workspace-documents/world-plans", headers=headers, json=body).json()["document_id"]
        scope = {"scope_mode": "world", "world_id": world, "schema_version": "dmb_tiptap_markdown_write_prepare_v2"}
    else:
        body = {"title": "Race note", "world_id": world, "campaign_id": world,
                "kind": "worldbuilding_source", "source_domain": "worldbuilding", "document_class": "lore",
                "authority_state": "draft", "visibility_state": "internal"}
        doc = client.post("/api/live/workspace-documents", headers=headers, json=body).json()["document_id"]
        scope = {}
    prepared = client.post("/api/live/tiptap/markdown-write/prepare", headers=headers,
                           json={"document_id": doc, "markdown": "A racing edit", **scope}).json()
    packet = {"document_id": doc, "markdown": "A racing edit", "writer_confirm_token": prepared["writer_confirm_token"],
              "expected_revision": prepared["registry_revision"]}
    if kind == "plan": packet.update({**scope, "schema_version": "dmb_tiptap_markdown_write_commit_v2"})
    entered, release = Event(), Event()
    original = guest_build_access.guest_write_capacity
    def hold_transaction(*args, **kwargs):
        original(*args, **kwargs)
        if not kwargs.get("creating"):
            entered.set()
            if not release.wait(10):
                raise RuntimeError("guest commit race test timed out")
    monkeypatch.setattr(guest_build_access, "guest_write_capacity", hold_transaction)
    with ThreadPoolExecutor(max_workers=2) as pool:
        commit = pool.submit(client.post, "/api/live/tiptap/markdown-write/commit", headers=headers, json=packet)
        try:
            assert entered.wait(10)
            reset = pool.submit(client.post, "/api/live/index-graph/reset", headers=headers)
            deadline = time.monotonic() + 5
            with connect(application_state_dsn) as connection:
                while time.monotonic() < deadline:
                    connection.execute('SELECT pg_stat_clear_snapshot()')
                    waiting = connection.execute(
                        "SELECT count(*) FROM pg_stat_activity WHERE datname = current_database() AND wait_event_type = 'Lock'"
                    ).fetchone()[0]
                    if waiting:
                        break
                    time.sleep(0.05)
            assert waiting > 0, "reset never reached the session lock"
        finally:
            release.set()
        assert commit.result(timeout=10).status_code in (200, 401, 403)
        assert reset.result(timeout=10).status_code == 200
    assert client.get(f"/api/live/workspace-documents/{doc}").status_code in (401, 403)


@pytest.mark.parametrize(("limit", "value"), [("MAX_GUEST_REVISIONS", 1), ("MAX_GUEST_SAVED_BYTES", 12)])
def test_guest_saved_content_limits_are_atomic_across_documents(guests, monkeypatch, limit, value):
    from concurrent.futures import ThreadPoolExecutor
    from apps.live_control_server.services import guest_build_access

    (client, token, world), _ = guests[0]
    monkeypatch.setattr(guest_build_access, limit, value)
    headers = {"X-DMB-Index-Graph-CSRF": token}
    body = {"title": "Guest note", "world_id": world, "campaign_id": world,
            "kind": "worldbuilding_source", "source_domain": "worldbuilding", "document_class": "lore",
            "authority_state": "draft", "visibility_state": "internal"}
    documents = [client.post("/api/live/workspace-documents", headers=headers, json=body).json()["document_id"] for _ in range(2)]
    packets = []
    for document in documents:
        prepared = client.post("/api/live/tiptap/markdown-write/prepare", headers=headers,
                               json={"document_id": document, "markdown": "New clue"}).json()
        packets.append({"document_id": document, "markdown": "New clue",
                        "writer_confirm_token": prepared["writer_confirm_token"],
                        "expected_revision": prepared["registry_revision"]})
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda packet: client.post("/api/live/tiptap/markdown-write/commit", headers=headers, json=packet), packets))
    assert sorted(response.status_code for response in results) == [200, 409]


def test_guest_combat_tracker_scopes_encounters_and_reset(guests, monkeypatch):
    from apps.live_control_server.routes import combat_encounters
    contexts, _, _ = guests
    (first, csrf, world), (other, other_csrf, other_world) = contexts
    first.app.include_router(combat_encounters.router)
    monkeypatch.setattr(combat_encounters, '_verified_world', lambda value: value)
    monkeypatch.setenv('DMB_HOSTED_GUEST_PLAY_ENABLED', '1')
    root = '/api/live/combat/encounters'
    headers = {'X-DMB-Index-Graph-CSRF': csrf}
    assert first.get(root, params={'world_id': world}).json() == []
    assert first.post(root, params={'world_id': world}, json={'title': 'Guest fight', 'ruleset_id': 'dnd5e.manual-tracking'}).status_code == 403
    made = first.post(root, params={'world_id': world}, headers=headers, json={'title': 'Guest fight', 'ruleset_id': 'dnd5e.manual-tracking'})
    assert made.status_code == 200, made.text
    encounter = made.json(); ident = encounter['encounter_id']
    assert first.get(root, params={'world_id': world}).json()[0]['encounter_id'] == ident
    assert other.get(root, params={'world_id': other_world}).json() == []
    assert other.get(f'{root}/{ident}', params={'world_id': world}).status_code == 403
    assert other.get(f'{root}/{ident}', params={'world_id': other_world}).status_code == 404
    draft = dict(encounter['draft']); draft['title'] = 'Updated fight'
    saved = first.put(f'{root}/{ident}', params={'world_id': world}, headers=headers, json={'expected_revision': encounter['revision'], 'draft': draft})
    assert saved.status_code == 200, saved.text
    assert saved.json()['draft']['title'] == 'Updated fight'
    assert first.put(f'{root}/{ident}', params={'world_id': world}, headers=headers, json={'expected_revision': encounter['revision'], 'draft': draft}).status_code == 409
    assert first.get(root, params=[('world_id', world), ('world_id', other_world)]).status_code in (400, 403)
    assert first.post('/api/live/index-graph/reset', headers=headers).status_code == 200
    assert first.get(f'{root}/{ident}', params={'world_id': world}).status_code in (401, 403)
    assert other.get(root, params={'world_id': other_world}).json() == []


def test_guest_combat_capacity_and_reset_serialization(guests, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    from apps.live_control_server.routes import combat_encounters
    from apps.live_control_server.services import guest_build_access
    (client, csrf, world), _ = guests[0]
    client.app.include_router(combat_encounters.router)
    monkeypatch.setattr(combat_encounters, '_verified_world', lambda value: value)
    monkeypatch.setenv('DMB_HOSTED_GUEST_PLAY_ENABLED', '1')
    monkeypatch.setattr(guest_build_access, 'MAX_GUEST_COMBAT_ENCOUNTERS', 1)
    headers = {'X-DMB-Index-Graph-CSRF': csrf}
    root = '/api/live/combat/encounters'
    body = {'title': 'Guest fight', 'ruleset_id': 'dnd5e.manual-tracking'}
    made = client.post(root, params={'world_id': world}, headers=headers, json=body)
    assert made.status_code == 200, made.text
    assert client.post(root, params={'world_id': world}, headers=headers, json=body).status_code == 409
    entered, release = Event(), Event()
    original = guest_build_access.guest_combat_capacity
    def holding(request, conn, world_id, *, creating):
        original(request, conn, world_id, creating=creating)
        if not creating:
            entered.set()
            assert release.wait(15)
    monkeypatch.setattr(guest_build_access, 'guest_combat_capacity', holding)
    saved = made.json(); draft = dict(saved['draft']); draft['title'] = 'Last update'
    with ThreadPoolExecutor(max_workers=2) as pool:
        pending = pool.submit(client.put, f"{root}/{saved['encounter_id']}", params={'world_id': world}, headers=headers,
                              json={'expected_revision': saved['revision'], 'draft': draft})
        try:
            assert entered.wait(15)
            reset = pool.submit(client.post, '/api/live/index-graph/reset', headers=headers)
            import time
            time.sleep(.2)
            assert not reset.done()
        finally:
            release.set()
        assert pending.result(timeout=15).status_code in (200, 403)
        assert reset.result(timeout=15).status_code == 200
    assert client.get(root, params={'world_id': world}).status_code in (401, 403)


def test_prepared_apprentice_plan_guest_isolation_and_reset(guests, monkeypatch, tmp_path, application_state_dsn):
    import hashlib
    import json
    from application_state.index_graph import guest_apprentice_plan

    contexts, _, source = guests
    (first, token, world), (second, other_token, other_world) = contexts
    bundle = tmp_path / 'release.json'
    bundle.write_text(json.dumps({'version': 1, 'graph_space': source['world_id'],
                                  'graph_revision': source['revision_id'],
                                  'documents': [{'title': "Sizzek's Apprentice", 'markdown': 'Source.'}]}))
    digest = hashlib.sha256(bundle.read_bytes()).hexdigest()
    monkeypatch.setenv('DMB_GUEST_DOCUMENT_BUNDLE', str(bundle))
    monkeypatch.setenv('DMB_GUEST_DOCUMENT_BUNDLE_SHA256', digest)
    monkeypatch.setenv('DMB_HOSTED_GUEST_PLAN_ENABLED', '1')
    monkeypatch.setattr(guest_apprentice_plan, '_SOURCE_SHA256', hashlib.sha256(b'Source.').hexdigest())
    for client, csrf in ((first, token), (second, other_token)):
        res = client.post('/api/live/index-graph/world', headers={'X-DMB-Index-Graph-CSRF': csrf})
        assert res.status_code == 200, res.text
    path = '/api/live/workspace-documents/world-plans'
    a = first.get(path, params={'world_id': world}).json()['records']
    b = second.get(path, params={'world_id': other_world}).json()['records']
    assert len(a) == len(b) == 1
    doc = a[0]['document_id']
    assert a[0]['title'] == "Sizzek's Apprentice" and doc != b[0]['document_id']
    snapshot = first.get(f'/api/live/workspace-documents/{doc}/snapshot')
    assert snapshot.status_code == 200 and 'scene:trap-room' in snapshot.json()['markdown']
    assert second.get(f'/api/live/workspace-documents/{doc}/snapshot').status_code == 403
    assert first.post('/api/live/index-graph/world', headers={'X-DMB-Index-Graph-CSRF': token}).status_code == 200
    assert len(first.get(path, params={'world_id': world}).json()['records']) == 1
    monkeypatch.setenv('DMB_HOSTED_GUEST_PLAY_ENABLED', '1')
    from apps.live_control_server.routes import combat_encounters
    first.app.include_router(combat_encounters.router)
    for client, csrf in ((first, token), (second, other_token)):
        assert client.post('/api/live/index-graph/world', headers={'X-DMB-Index-Graph-CSRF': csrf}).status_code == 200
    combat_path = '/api/live/combat/encounters'
    encounters = first.get(combat_path, params={'world_id': world})
    assert encounters.status_code == 200, encounters.text
    encounter, = encounters.json()['records'] if isinstance(encounters.json(), dict) else encounters.json()
    assert encounter['draft']['title'] == 'Funhouse: The Closing Walls'
    assert sum(actor['name'].startswith('Skeleton ') for actor in encounter['draft']['entities']) == 6
    other_encounters = second.get(combat_path, params={'world_id': other_world})
    other_records = other_encounters.json()['records'] if isinstance(other_encounters.json(), dict) else other_encounters.json()
    assert other_records[0]['encounter_id'] != encounter['encounter_id']
    assert second.get(f"{combat_path}/{encounter['encounter_id']}", params={'world_id': other_world}).status_code in (403, 404)
    draft = dict(encounter['draft']); draft['title'] = 'Guest combat edit'
    saved_combat = first.put(f"{combat_path}/{encounter['encounter_id']}", params={'world_id': world},
                             headers={'X-DMB-Index-Graph-CSRF': token},
                             json={'expected_revision': encounter['revision'], 'draft': draft})
    assert saved_combat.status_code == 200, saved_combat.text
    assert first.post('/api/live/index-graph/world', headers={'X-DMB-Index-Graph-CSRF': token}).status_code == 200
    reopened_combat = first.get(f"{combat_path}/{encounter['encounter_id']}", params={'world_id': world})
    assert reopened_combat.status_code == 200 and reopened_combat.json()['draft']['title'] == 'Guest combat edit'
    revision = first.get(f'/api/live/workspace-documents/{doc}/committed-revision')
    assert revision.status_code == 200, revision.text
    pin = revision.json()
    source_request = {'playable_artifact_id': doc, 'expected_playable_revision': pin['revision_n'],
                      'expected_playable_work_revision_id': pin['work_revision_id'],
                      'expected_playable_content_sha256': pin['content_sha256']}
    headers = {'X-DMB-Index-Graph-CSRF': token}
    preview = first.post('/api/live/world-play-runs/v2/preparation', params={'world_id': world, 'entry_scene_id': 'scene:contract'}, headers=headers, json=source_request)
    assert preview.status_code == 200, preview.text
    from uuid import UUID
    run = str(UUID(world.removeprefix('guest-')))
    run_path = f'/api/live/world-play-runs/v2/{run}'
    created = first.put(run_path, params={'world_id': world}, headers=headers, json=preview.json()['request'])
    assert created.status_code == 200, created.text
    assert created.json()['run']['progress']['current_scene_id'] == 'scene:contract'
    assert first.put(run_path, params={'world_id': world}, headers=headers, json=preview.json()['request']).status_code == 200
    assert second.get(run_path, params={'world_id': world}).status_code == 403
    content_path = f'{run_path}/content'
    content = first.get(content_path, params={'world_id': world})
    assert content.status_code == 200, content.text
    body = content.json()
    command = str(UUID('11111111-1111-4111-8111-111111111111'))
    command_path = f'{content_path}/commands/{command}'
    edit = {'schema_version': 'dmb_world_play_run_content_commit_v1', 'expected_origin': body['origin'],
            'expected_edition_revision': body['edition_revision'], 'expected_content_sha256': body['content_sha256'],
            'markdown': body['markdown'] + '\nA guest clue.\n'}
    assert first.put(command_path, params={'world_id': world}, json=edit).status_code == 403
    assert second.put(command_path, params={'world_id': world}, headers={'X-DMB-Index-Graph-CSRF': other_token}, json=edit).status_code == 403
    saved = first.put(command_path, params={'world_id': world}, headers=headers, json=edit)
    assert saved.status_code == 200, saved.text
    assert first.put(command_path, params={'world_id': world}, headers=headers, json=edit).status_code == 200
    assert first.get(command_path, params={'world_id': world}).status_code == 200
    assert first.get(content_path, params={'world_id': world}).json()['markdown'].endswith('A guest clue.\n')
    assert 'A guest clue.' not in first.get(f'/api/live/workspace-documents/{doc}/snapshot').json()['markdown']
    other_command = f"{content_path}/commands/22222222-2222-4222-8222-222222222222"
    assert first.put(other_command, params={'world_id': world}, headers=headers, json=edit).status_code == 409
    assert second.get(content_path, params={'world_id': world}).status_code == 403
    review_path = f'{run_path}/review'
    review = first.get(review_path, params={'world_id': world})
    assert review.status_code == 200 and review.json()['review'] is None
    assert second.get(review_path, params={'world_id': world}).status_code == 403
    current_content = first.get(content_path, params={'world_id': world}).json()
    review_body = {'action': 'end', 'expected_revision': 0,
                   'expected_run_revision': created.json()['run']['run_revision'],
                   'expected_content_sha256': current_content['content_sha256'], 'final_thoughts': ''}
    review_command = f'{review_path}/commands/33333333-3333-4333-8333-333333333333'
    assert first.put(review_command, params={'world_id': world}, json=review_body).status_code == 403
    ended = first.put(review_command, params={'world_id': world}, headers=headers, json=review_body)
    assert ended.status_code == 200 and ended.json()['status'] == 'ended', ended.text
    from apps.live_control_server.services import guest_build_access
    monkeypatch.setattr(guest_build_access, 'MAX_GUEST_PLAY_REVIEWS', 1)
    assert first.put(review_command, params={'world_id': world}, headers=headers, json=review_body).status_code == 200
    reopen_path = f'{review_path}/commands/44444444-4444-4444-8444-444444444444'
    reopen = {**review_body, 'action': 'reopen', 'expected_revision': 1}
    limited_review = first.put(reopen_path, params={'world_id': world}, headers=headers, json=reopen)
    assert limited_review.status_code == 409 and 'limit' in limited_review.text
    monkeypatch.setattr(guest_build_access, 'MAX_GUEST_PLAY_REVIEWS', 256)
    reopened = first.put(reopen_path, params={'world_id': world}, headers=headers, json=reopen)
    assert reopened.status_code == 200 and reopened.json()['status'] == 'playing', reopened.text
    # A second guest's review write must hold the same session lock as reset.
    other_doc = b[0]['document_id']
    other_pin = second.get(f'/api/live/workspace-documents/{other_doc}/committed-revision').json()
    other_source = {'playable_artifact_id': other_doc, 'expected_playable_revision': other_pin['revision_n'],
                    'expected_playable_work_revision_id': other_pin['work_revision_id'],
                    'expected_playable_content_sha256': other_pin['content_sha256']}
    other_headers = {'X-DMB-Index-Graph-CSRF': other_token}
    other_preview = second.post('/api/live/world-play-runs/v2/preparation', params={'world_id': other_world, 'entry_scene_id': 'scene:contract'}, headers=other_headers, json=other_source)
    assert other_preview.status_code == 200, other_preview.text
    other_run = str(UUID(other_world.removeprefix('guest-')))
    other_run_path = f'/api/live/world-play-runs/v2/{other_run}'
    other_created = second.put(other_run_path, params={'world_id': other_world}, headers=other_headers, json=other_preview.json()['request'])
    assert other_created.status_code == 200, other_created.text
    other_content = second.get(f'{other_run_path}/content', params={'world_id': other_world}).json()
    other_review = {'action': 'end', 'expected_revision': 0, 'expected_run_revision': other_created.json()['run']['run_revision'],
                    'expected_content_sha256': other_content['content_sha256'], 'final_thoughts': ''}
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    entered_review, release_review = Event(), Event()
    original_review_capacity = guest_build_access.guest_play_review_capacity
    def hold_review(request, conn, scoped_world, payload_bytes, replay):
        original_review_capacity(request, conn, scoped_world, payload_bytes, replay)
        if replay is False:
            entered_review.set()
            if not release_review.wait(15): raise RuntimeError('guest review race timed out')
    monkeypatch.setattr(guest_build_access, 'guest_play_review_capacity', hold_review)
    with ThreadPoolExecutor(max_workers=2) as pool:
        pending_review = pool.submit(second.put, f'{other_run_path}/review/commands/55555555-5555-4555-8555-555555555555', params={'world_id': other_world}, headers=other_headers, json=other_review)
        try:
            assert entered_review.wait(15)
            resetting_other = pool.submit(second.post, '/api/live/index-graph/reset', headers=other_headers)
            import time
            from application_state.engine import connect
            deadline = time.monotonic() + 5
            with connect(application_state_dsn) as observer:
                while time.monotonic() < deadline:
                    observer.execute('SELECT pg_stat_clear_snapshot()')
                    waiting = observer.execute("SELECT count(*) FROM pg_stat_activity WHERE datname = current_database() AND wait_event_type = 'Lock'").fetchone()[0]
                    if waiting: break
                    time.sleep(.05)
            assert waiting and not resetting_other.done()
        finally:
            release_review.set()
        assert pending_review.result(timeout=15).status_code in (200, 401, 403)
        assert resetting_other.result(timeout=15).status_code == 200
    assert second.get(f'{other_run_path}/review', params={'world_id': other_world}).status_code in (401, 403)
    assert first.get(review_path, params={'world_id': world}).status_code == 200
    # Reset must serialize with a content commit, not revoke the session midway.
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    from apps.live_control_server.services import guest_build_access
    current = first.get(content_path, params={'world_id': world}).json()
    next_edit = {**edit, 'expected_edition_revision': current['edition_revision'],
                 'expected_content_sha256': current['content_sha256'],
                 'markdown': current['markdown'] + '\nAnother guest clue.\n'}
    monkeypatch.setattr(guest_build_access, 'MAX_GUEST_PLAY_EDITS', 1)
    assert first.put(command_path, params={'world_id': world}, headers=headers, json=edit).status_code == 200
    limited = first.put(other_command, params={'world_id': world}, headers=headers, json=next_edit)
    assert limited.status_code == 409 and 'limit' in limited.text
    monkeypatch.setattr(guest_build_access, 'MAX_GUEST_PLAY_EDITS', 256)
    entered, release = Event(), Event()
    original_capacity = guest_build_access.guest_play_edit_capacity
    def hold_capacity(request, conn, scoped_world, content_bytes, replay):
        original_capacity(request, conn, scoped_world, content_bytes, replay)
        if replay is False:
            entered.set()
            if not release.wait(15): raise RuntimeError('guest Play edit race timed out')
    monkeypatch.setattr(guest_build_access, 'guest_play_edit_capacity', hold_capacity)
    with ThreadPoolExecutor(max_workers=2) as pool:
        pending = pool.submit(first.put, other_command, params={'world_id': world}, headers=headers, json=next_edit)
        try:
            assert entered.wait(15)
            resetting = pool.submit(first.post, '/api/live/index-graph/reset', headers=headers)
            import time
            from application_state.engine import connect
            deadline = time.monotonic() + 5
            with connect(application_state_dsn) as observer:
                while time.monotonic() < deadline:
                    observer.execute('SELECT pg_stat_clear_snapshot()')
                    waiting = observer.execute("SELECT count(*) FROM pg_stat_activity WHERE datname = current_database() AND wait_event_type = 'Lock'").fetchone()[0]
                    if waiting:
                        break
                    time.sleep(.05)
            assert waiting and not resetting.done(), 'reset did not wait for the guest transaction lock'
        finally:
            release.set()
        assert pending.result(timeout=15).status_code in (200, 401, 403)
        assert resetting.result(timeout=15).status_code == 200
    assert first.get(content_path, params={'world_id': world}).status_code in (401, 403)
    assert first.get(review_path, params={'world_id': world}).status_code in (401, 403)
    assert first.get(run_path, params={'world_id': world}).status_code in (401, 403)
    assert first.get(f"{combat_path}/{encounter['encounter_id']}", params={'world_id': world}).status_code in (401, 403)
    assert second.get(f"{combat_path}/{other_records[0]['encounter_id']}", params={'world_id': other_world}).status_code in (401, 403)
    assert first.get(f'/api/live/workspace-documents/{doc}/snapshot').status_code in (401, 403)


def test_guest_play_content_routes_are_narrow_and_feature_gated(monkeypatch):
    from apps.live_control_server.services.guest_build_access import matches_guest_build_route
    run = '11111111-1111-4111-8111-111111111111'
    cmd = '22222222-2222-4222-8222-222222222222'
    root = f'/api/live/world-play-runs/v2/{run}/content'
    monkeypatch.setenv('DMB_HOSTED_GUEST_PLAN_ENABLED', '1')
    monkeypatch.delenv('DMB_HOSTED_GUEST_PLAY_ENABLED', raising=False)
    assert not matches_guest_build_route('PUT', f'{root}/commands/{cmd}')
    monkeypatch.setenv('DMB_HOSTED_GUEST_PLAY_ENABLED', '1')
    assert matches_guest_build_route('PUT', f'{root}/commands/{cmd}')
    assert matches_guest_build_route('GET', f'{root}/commands/{cmd}')
    assert matches_guest_build_route('GET', f'{root}/revisions/0')
    assert not matches_guest_build_route('PUT', f'{root}/revisions/0')
    assert not matches_guest_build_route('POST', f'{root}/commands/{cmd}')
    assert not matches_guest_build_route('GET', f'{root}/proposals')
    review = f'/api/live/world-play-runs/v2/{run}/review'
    assert matches_guest_build_route('GET', review)
    assert matches_guest_build_route('PUT', f'{review}/commands/{cmd}')
    assert not matches_guest_build_route('GET', f'{review}/commands/{cmd}')
    assert not matches_guest_build_route('POST', review)
