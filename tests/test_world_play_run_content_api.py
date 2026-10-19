"""Actual authenticated ASGI routes backed by disposable PostgreSQL."""

from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from apps.live_control_server.routes.play_runs import router
from tests.application_state.test_play_run_editions_postgres import (
    create_source_run,
    request_for,
    read,
    WORLD,
)


@pytest.fixture
def api(monkeypatch):
    monkeypatch.setenv("DMB_AGENT_GRAPH_AUTH_MODE", "local_operator")
    monkeypatch.setenv("DMB_AGENT_GRAPH_AUTH_ENVIRONMENT", "local")
    monkeypatch.setenv(
        "DMB_AGENT_GRAPH_LOCAL_OPERATOR_TOKEN",
        "synthetic-edition-operator-token-000000",
    )
    app = FastAPI()
    app.include_router(router)
    return TestClient(app, client=("127.0.0.1", 45000))


def test_authenticated_content_history_recovery_and_legacy_run_dto(
    application_state_dsn, api
):
    _, _, aggregate = create_source_run()
    run_id = str(aggregate.run.run_id)
    path = f"/api/live/world-play-runs/v2/{run_id}"
    content_path = path + "/content"
    headers = {"Authorization": "Bearer synthetic-edition-operator-token-000000"}
    params = {"world_id": WORLD}
    assert api.get(content_path, params=params).status_code == 401
    assert api.get(content_path + "/revisions/0", params=params).status_code == 401
    cmd = str(uuid4())
    command_path = content_path + "/commands/" + cmd
    assert api.get(command_path, params=params).status_code == 401
    assert api.put(command_path, params=params, json={}).status_code == 401
    initial = api.get(content_path, headers=headers, params=params)
    assert initial.status_code == 200
    assert initial.json()["source"] == "pinned"
    request = request_for(read(run_id)).model_dump(mode="json")
    assert api.get(command_path, headers=headers, params=params).status_code == 404
    accepted = api.put(command_path, headers=headers, params=params, json=request)
    assert accepted.status_code == 200, accepted.text
    first_receipt = accepted.json()
    assert api.get(command_path, headers=headers, params=params).json() == first_receipt
    request2 = request_for(read(run_id), "Next edit").model_dump(mode="json")
    assert (
        api.put(
            content_path + "/commands/" + str(uuid4()),
            headers=headers,
            params=params,
            json=request2,
        ).status_code
        == 200
    )
    assert (
        api.put(command_path, headers=headers, params=params, json=request).json()
        == first_receipt
    )
    assert (
        api.get(content_path + "/revisions/1", headers=headers, params=params).json()[
            "markdown"
        ]
        == request["markdown"]
    )
    assert (
        api.get(content_path + "/revisions/0", headers=headers, params=params).json()[
            "markdown"
        ]
        == initial.json()["markdown"]
    )
    assert (
        api.get(
            content_path + "/revisions/99", headers=headers, params=params
        ).status_code
        == 404
    )
    assert (
        api.get(path, params=params).json()["playable_content_sha256"]
        == initial.json()["content_sha256"]
    )
    assert (
        api.get(content_path, headers=headers, params={"world_id": "wrong"}).status_code
        == 404
    )
    assert (
        api.put(
            command_path, headers=headers, params={"world_id": "wrong"}, json=request
        ).status_code
        == 404
    )
    assert (
        api.put(command_path, headers=headers, params=params, json=request2).status_code
        == 409
    )


@pytest.mark.parametrize(
    "mutation", ["extra", "bool", "uuid", "hash", "schema", "oversize", "noop"]
)
def test_strict_command_body_limits(application_state_dsn, api, mutation):
    _, _, run = create_source_run()
    run_id = str(run.run.run_id)
    body = request_for(read(run_id)).model_dump(mode="json")
    expected = 422
    if mutation == "extra":
        body["surprise"] = True
    if mutation == "bool":
        body["expected_edition_revision"] = False
    if mutation == "uuid":
        body["expected_origin"]["playable_artifact_id"] = "BAD"
    if mutation == "hash":
        body["expected_content_sha256"] = "A" * 64
    if mutation == "schema":
        body["schema_version"] = "unknown"
    if mutation == "oversize":
        body["markdown"] = "é" * 1048576
        expected = 413
    if mutation == "noop":
        body["markdown"] = read(run_id).markdown
    response = api.put(
        f"/api/live/world-play-runs/v2/{run_id}/content/commands/{uuid4()}",
        params={"world_id": WORLD},
        headers={"Authorization": "Bearer synthetic-edition-operator-token-000000"},
        json=body,
    )
    assert response.status_code == expected, response.text
    assert read(run_id).edition_revision == 0
