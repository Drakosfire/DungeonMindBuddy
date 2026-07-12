"""HTTP-boundary tests for the PR006D2 bootstrap contract."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.live_control_server.main import create_app

STATUS_URL = "/api/live/world-graph-bootstrap/status"
PREPARE_URL = "/api/live/world-graph-bootstrap/prepare"
CONFIRM_URL = "/api/live/world-graph-bootstrap/confirm"


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("DUNGEONMIND_WORLD_GRAPH_ROOT", str(tmp_path))
    return TestClient(create_app())


def test_status_serializes_strict_camel_case_contract(client: TestClient) -> None:
    response = client.get(STATUS_URL)

    assert response.status_code == 200
    payload = response.json()
    assert payload["schema"] == "dmb_world_graph_bootstrap_status_v1"
    assert payload["state"] == "ready"
    assert payload["worldId"] == "eldyrwild"
    assert payload["campaignId"] == "longmont-c2"
    assert "focusSessionId" in payload
    assert "review" in payload
    assert "trustBoundary" in payload
    assert "current_head_revision_id" not in json.dumps(payload)


def test_prepare_rejects_server_owned_selectors_and_writes_nothing(
    client: TestClient,
    tmp_path: Path,
) -> None:
    response = client.post(
        PREPARE_URL,
        json={"actor": "gm", "bundleId": "not-client-selectable"},
    )
    assert response.status_code == 422

    query_response = client.post(
        f"{PREPARE_URL}?root=/tmp/foreign&worldId=foreign",
        json={"actor": "gm"},
    )
    assert query_response.status_code == 422
    assert query_response.json()["code"] == "invalid_request"
    assert not any(tmp_path.iterdir())


def test_prepare_and_confirm_routes_use_one_contract(client: TestClient) -> None:
    prepared_response = client.post(PREPARE_URL, json={"actor": "gm"})

    assert prepared_response.status_code == 200
    prepared = prepared_response.json()
    assert prepared["schema"] == "dmb_world_graph_bootstrap_prepare_v1"
    assert prepared["prepared"] is True
    assert prepared["proposalId"]
    assert prepared["confirmToken"]
    assert prepared["review"]["summary"]["nodeCount"] == 12
    assert prepared["effects"]["predictedRevisionCount"] == 7

    confirmed_response = client.post(
        CONFIRM_URL,
        json={
            "actor": "gm",
            "proposalId": prepared["proposalId"],
            "confirmToken": prepared["confirmToken"],
        },
    )
    assert confirmed_response.status_code == 200
    confirmed = confirmed_response.json()
    assert confirmed["schema"] == "dmb_world_graph_bootstrap_confirm_v1"
    assert confirmed["published"] is True
    assert confirmed["state"] == "active"
    assert confirmed["receipt"]["nodeCount"] == 12
    assert confirmed["receipt"]["edgeCount"] == 11

    repeat_response = client.post(
        CONFIRM_URL,
        json={
            "actor": "gm",
            "proposalId": prepared["proposalId"],
            "confirmToken": prepared["confirmToken"],
        },
    )
    assert repeat_response.status_code == 200
    assert repeat_response.json()["published"] is False
    assert repeat_response.json()["state"] == "active"


def test_confirm_error_is_stable_and_does_not_leak_paths(client: TestClient, tmp_path: Path) -> None:
    response = client.post(
        CONFIRM_URL,
        json={
            "actor": "gm",
            "proposalId": "wrong",
            "confirmToken": "wrong",
        },
    )

    assert response.status_code == 409
    payload = response.json()
    assert payload["schema"] == "dmb_world_graph_bootstrap_error_v1"
    assert payload["code"] in {"proposal_mismatch", "stale_confirmation"}
    assert str(tmp_path) not in json.dumps(payload)
    assert "JSONDecodeError" not in json.dumps(payload)


def test_status_rejects_root_query_selector(client: TestClient) -> None:
    response = client.get(f"{STATUS_URL}?root=/tmp/foreign")

    assert response.status_code == 422
    assert response.json()["code"] == "invalid_request"
