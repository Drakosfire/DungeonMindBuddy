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
