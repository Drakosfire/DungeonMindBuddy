from uuid import uuid4
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from apps.live_control_server.routes import conversation_library as routes


@pytest.fixture
def client(monkeypatch):
    token = "synthetic-library-operator-token-123456"
    monkeypatch.setenv("DMB_AGENT_GRAPH_AUTH_MODE", "local_operator")
    monkeypatch.setenv("DMB_AGENT_GRAPH_AUTH_ENVIRONMENT", "local")
    monkeypatch.setenv("DMB_AGENT_GRAPH_LOCAL_OPERATOR_TOKEN", token)
    world = Mock(return_value="world-one")
    monkeypatch.setattr(routes, "_verified_world_id", world)
    service = SimpleNamespace(
        list_library=Mock(return_value={"items": []}),
        get_name=Mock(return_value={"title": "Synthetic"}),
        read_turns=Mock(return_value={"turns": []}),
        read_messages=Mock(return_value={"messages": []}),
        read_active_messages=Mock(return_value={"messages": []}),
        rename=Mock(return_value={"title": "Saved"}),
    )
    for name in vars(service):
        monkeypatch.setattr(routes.library, name, getattr(service, name))
    app = FastAPI()
    app.include_router(routes.router)
    return SimpleNamespace(
        app=app,
        client=TestClient(
            app,
            client=("127.0.0.1", 54000),
            headers={"Authorization": "Bearer " + token},
        ),
        world=world,
        service=service,
    )


@pytest.mark.parametrize(
    "suffix,method",
    [
        ("", "GET"),
        ("/" + str(uuid4()) + "/name", "GET"),
        ("/" + str(uuid4()) + "/turns", "GET"),
        ("/" + str(uuid4()) + "/messages", "GET"),
        ("/" + str(uuid4()) + "/name", "PUT"),
    ],
)
def test_guard_precedes_world_and_library_io(client, suffix, method):
    unauthorized = TestClient(client.app, client=("127.0.0.1", 54001))
    result = unauthorized.request(
        method,
        "/api/live/agent/worlds/world-one/conversations" + suffix,
        json={"title": "Name", "expected_revision": 0} if method == "PUT" else None,
    )
    assert result.status_code == 401
    client.world.assert_not_called()
    for name in vars(client.service):
        getattr(client.service, name).assert_not_called()


def test_strict_selectors_and_exact_target(client):
    path = "/api/live/agent/worlds/world-one/conversations"
    cid = uuid4()
    assert client.client.get(path + "?status=archived&limit=25").status_code == 200
    client.service.list_library.assert_called_once_with(
        "world-one", status="archived", limit=25, before=None
    )
    assert client.client.get(path + "?status=archived&status=all").status_code == 422
    assert client.client.get(path + "?unknown=1").status_code == 422
    assert (
        client.client.put(
            path + "/" + str(cid) + "/name",
            json={"title": "Named work", "expected_revision": 0},
        ).status_code
        == 200
    )
    assert client.service.rename.call_args.args[:2] == ("world-one", cid)
    assert (
        client.client.put(
            path + "/" + str(cid) + "/name",
            json={"title": "Named", "expected_revision": 0, "extra": True},
        ).status_code
        == 422
    )


def test_retry_context_is_authenticated_and_uses_exact_scoped_turn_ids(client,monkeypatch):
    from application_state.agent_conversation import retry
    read=Mock(return_value={'schema':'dmb_turn_retry_context_v1'})
    monkeypatch.setattr(retry,'read_context',read)
    cid,tid=uuid4(),uuid4()
    url=f'/api/live/agent/worlds/world-one/conversations/{cid}/retry-context'
    response=client.client.get(url,params={'turn_ids':str(tid)})
    assert response.status_code==200
    read.assert_called_once_with('world-one',cid,[tid])
    read.reset_mock()
    assert client.client.get(url,params={'turn_ids':str(tid),'extra':'bad'}).status_code==422
    assert client.client.get(url,params={'turn_ids':'not-a-turn'}).status_code==422
    assert not read.called
    assert client.client.get(url,params={'turn_ids':str(tid)},headers={'Authorization':'Bearer invalid'}).status_code in {401,403}
    assert not read.called


def test_retained_discussion_input_is_authenticated_read_only_and_strict(client, monkeypatch):
    from application_state.agent_conversation import retry
    read = Mock(return_value={"schema": "dmb_build_retained_discussion_retry_input_v1"})
    monkeypatch.setattr(retry, "read_discussion_retry_input", read)
    cid, tid = uuid4(), uuid4()
    url = f"/api/live/agent/worlds/world-one/conversations/{cid}/turns/{tid}/discussion-retry-input"
    assert client.client.get(url, params={"revision": 4}, headers={"Authorization": "Bearer invalid"}).status_code in {401, 403}
    read.assert_not_called()
    assert client.client.get(url + "?revision=4&revision=5").status_code == 422
    assert client.client.get(url + "?revision=4&extra=x").status_code == 422
    read.assert_not_called()
    assert client.client.get(url, params={"revision": 4}).status_code == 200
    read.assert_called_once_with("world-one", cid, tid, 4)


def test_resume_guard_and_exact_route_owner(client):
    from unittest.mock import Mock
    cid=uuid4()
    service=SimpleNamespace(reopen_conversation=Mock())
    client.app.state.agent_conversation_service=service
    body=dict(world_id='world-one',conversation_id=str(cid),command_id=str(uuid4()),expected_pointer_revision=2,expected_active_conversation_id=None)
    path=f'/api/live/agent/worlds/world-one/conversations/{cid}/resume'
    denied=TestClient(client.app,client=('127.0.0.1',54001)).post(path,json=body)
    assert denied.status_code==401
    client.world.assert_not_called()
    service.reopen_conversation.assert_not_called()
    assert client.client.post(path,json=body|{'world_id':'other'}).status_code==422
    assert client.client.post(path,json=body|{'conversation_id':str(uuid4())}).status_code==422
    service.reopen_conversation.assert_not_called()


def test_mounted_resume_reuses_app_pointer_and_receipt(application_state_dsn,client):
    from application_state.agent_conversation import AgentConversationService
    from application_state.agent_conversation.types import ConversationCommand
    service=AgentConversationService()
    client.app.state.agent_conversation_service=service
    def new():
        pointer=service.get_world_pointer('world-one')
        return service.new_conversation(ConversationCommand(world_id='world-one',command_id=uuid4(),expected_pointer_revision=pointer.revision,expected_active_conversation_id=pointer.active_conversation_id))
    old=new()
    current=new()
    pointer=service.get_world_pointer('world-one')
    body=dict(world_id='world-one',conversation_id=str(old.conversation_id),command_id=str(uuid4()),expected_pointer_revision=pointer.revision,expected_active_conversation_id=str(current.conversation_id))
    path=f'/api/live/agent/worlds/world-one/conversations/{old.conversation_id}/resume'
    response=client.client.post(path,json=body)
    assert response.status_code==200,response.text
    assert response.json()['command_kind']=='reopen'
    assert service.get_world_pointer('world-one').active_conversation_id==old.conversation_id
    assert service.get_conversation('world-one',current.conversation_id).status=='archived'
    assert client.client.post(path,json=body).json()==response.json()
    newer=new()
    assert client.client.post(path,json=body).json()==response.json()
    assert service.get_world_pointer('world-one').active_conversation_id==newer.conversation_id
    stale=client.client.post(path,json=body|{'command_id':str(uuid4())})
    assert stale.status_code==409
    assert service.get_world_pointer('world-one').active_conversation_id==newer.conversation_id
    missing=uuid4()
    latest=service.get_world_pointer('world-one')
    assert client.client.post(f'/api/live/agent/worlds/world-one/conversations/{missing}/resume',json=body|{'conversation_id':str(missing),'command_id':str(uuid4()),'expected_pointer_revision':latest.revision,'expected_active_conversation_id':str(latest.active_conversation_id)}).status_code==404


@pytest.mark.parametrize("operation", ["trash", "restore"])
def test_lifecycle_auth_and_exact_target(client, monkeypatch, operation):
    from datetime import datetime, timezone
    from application_state.agent_conversation.types import ConversationCommandReceipt
    cid, command_id = uuid4(), uuid4()
    body = dict(world_id="world-one", conversation_id=str(cid), command_id=str(command_id), expected_pointer_revision=4, expected_active_conversation_id=None)
    native = Mock(return_value=ConversationCommandReceipt(world_id="world-one", conversation_id=cid, command_id=command_id, command_kind=operation, active_conversation_id=None, pointer_revision=5, recorded_at=datetime.now(timezone.utc)))
    monkeypatch.setattr(routes, "_conversation_service", lambda request: SimpleNamespace(set_conversation_trash=native))
    url = f"/api/live/agent/worlds/world-one/conversations/{cid}/{operation}"
    unauthorized = TestClient(client.app, client=("127.0.0.1", 54001))
    assert unauthorized.post(url, json=body).status_code == 401
    native.assert_not_called()
    assert client.client.post(url, json={**body, "world_id": "foreign"}).status_code == 422
    assert client.client.post(url, json={**body, "conversation_id": str(uuid4())}).status_code == 422
    assert client.client.post(url + "?unexpected=1", json=body).status_code == 422
    native.assert_not_called()
    assert client.client.post(url, json=body).status_code == 200
    assert native.call_args.kwargs == {"restore": operation == "restore"}


def test_message_preview_is_scoped_and_does_not_request_execution_details(client):
    cid = uuid4()
    url = f"/api/live/agent/worlds/world-one/conversations/{cid}/messages"
    assert client.client.get(url, params={"limit": 25, "before_sequence": 12}).status_code == 200
    client.service.read_messages.assert_called_once_with("world-one", cid, limit=25, before_sequence=12)
    client.service.read_turns.assert_not_called()
    assert client.client.get(url + "?limit=2&limit=3").status_code == 422
    assert client.client.get(url + "?unknown=1").status_code == 422


def test_active_messages_auth_scope_and_selector_use_the_light_owner(client):
    url = "/api/live/agent/worlds/world-one/conversations/active/messages"
    assert (
        client.client.get(url, params={"limit": 25, "before_sequence": 12}).status_code
        == 200
    )
    client.service.read_active_messages.assert_called_once_with(
        "world-one", limit=25, before_sequence=12
    )
    client.service.read_turns.assert_not_called()
    assert client.client.get(url + "?limit=2&limit=3").status_code == 422
    assert client.client.get(url + "?unknown=1").status_code == 422
    client.world.reset_mock()
    client.service.read_active_messages.reset_mock()
    assert TestClient(client.app).get(url).status_code == 403
    client.world.assert_not_called()
    client.service.read_active_messages.assert_not_called()
