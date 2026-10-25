from uuid import uuid4
from unittest.mock import Mock
from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from apps.live_control_server.routes import (
    conversation_work_plans as routes,
    conversation_library,
)


@pytest.fixture
def client(monkeypatch):
    token = "synthetic-plan-operator-token-123456"
    for k, v in {
        "DMB_AGENT_GRAPH_AUTH_MODE": "local_operator",
        "DMB_AGENT_GRAPH_AUTH_ENVIRONMENT": "local",
        "DMB_AGENT_GRAPH_LOCAL_OPERATOR_TOKEN": token,
    }.items():
        monkeypatch.setenv(k, v)
    verified = Mock(return_value="world-one")
    monkeypatch.setattr(conversation_library, "_verified_world_id", verified)
    service = {
        n: Mock(return_value={"fixture": n}) for n in ("read", "save", "continue_step")
    }
    for n, m in service.items():
        monkeypatch.setattr(routes.work_plan, n, m)
    app = FastAPI()
    app.include_router(routes.router)
    return (
        TestClient(
            app,
            client=("127.0.0.1", 5000),
            headers={"Authorization": "Bearer " + token},
        ),
        verified,
        service,
    )


@pytest.mark.parametrize(
    "method,suffix,body",
    [
        ("GET", "", None),
        (
            "PUT",
            "",
            {
                "expected_revision": 0,
                "steps": [
                    {
                        "step_id": str(uuid4()),
                        "text": "Discuss the owner",
                        "selected": True,
                    }
                ],
            },
        ),
        (
            "POST",
            "/continue",
            {
                "expected_revision": 1,
                "step_id": str(uuid4()),
                "command_id": str(uuid4()),
            },
        ),
    ],
)
def test_auth_selector_and_exact_scope(client, method, suffix, body):
    c, verified, service = client
    cid = uuid4()
    tid = uuid4()
    path = (
        f"/api/live/agent/worlds/world-one/conversations/{cid}/work-plans/{tid}{suffix}"
    )
    assert (
        c.request(
            method, path, json=body, headers={"Authorization": "Bearer wrong"}
        ).status_code
        == 401
    )
    verified.assert_not_called()
    assert c.request(method, path + "?unexpected=1", json=body).status_code == 422
    assert c.request(method, path, json=body).status_code == 200
    name = {"GET": "read", "PUT": "save", "POST": "continue_step"}[method]
    assert service[name].call_args.args[:3] == ("world-one", cid, tid)
    if body:
        assert c.request(method, path, json={**body, "extra": True}).status_code == 422
