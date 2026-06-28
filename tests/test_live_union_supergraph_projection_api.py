from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from apps.live_control_server.main import create_app
from graph_memory.union_supergraph.load import DEFAULT_FIXTURE_PATH


def test_union_supergraph_projection_api_returns_session_23_payload() -> None:
    payload = _get_projection_payload()

    assert payload["session_id"] == "session-23"
    assert payload["campaign_id"] == "longmont-c2"
    assert payload["graph_id"] == "longmont-c2:union-supergraph"
    assert set(payload) == {
        "campaign_id",
        "session_id",
        "graph_id",
        "focus",
        "node_views",
        "mentions",
    }


def test_union_supergraph_projection_api_contains_global_pc_caelynn() -> None:
    payload = _get_projection_payload()

    caelynn = payload["node_views"]["pc_caelynn"]
    assert caelynn["node_id"] == "pc_caelynn"
    assert caelynn["label"] == "Caelynn"
    assert caelynn["kind"] == "pc"
    assert caelynn["role"] == "pc"
    assert caelynn["anchored_to_focus_session"] is True


def test_union_supergraph_projection_api_preserves_focus_and_non_focus_evidence() -> None:
    payload = _get_projection_payload()

    badges = {
        badge["evidence_ref_id"]: badge
        for badge in payload["node_views"]["pc_caelynn"]["evidence_badges"]
    }

    focus_badge = badges["evidence:session-23:caelynn:recap-mention"]
    assert focus_badge["is_focus_session_evidence"] is True
    assert focus_badge["source_domain"] == "recap"

    worldbuilding_badge = badges["evidence:worldbuilding:caelynn:character-note"]
    assert worldbuilding_badge["is_focus_session_evidence"] is False
    assert worldbuilding_badge["source_domain"] == "worldbuilding"


def test_union_supergraph_projection_api_preserves_focus_and_non_focus_adjacency() -> None:
    payload = _get_projection_payload()

    adjacency = {
        candidate["node_id"]: candidate
        for candidate in payload["node_views"]["pc_caelynn"]["adjacency"]
    }

    session_event = adjacency["event_session_23_mireward_gate"]
    assert session_event["anchored_to_focus_session"] is True
    assert session_event["predicate"] == "participated_in"
    assert session_event["source_domains"] == ["recap"]

    mirathorn = adjacency["loc_mirathorn"]
    assert mirathorn["anchored_to_focus_session"] is False
    assert mirathorn["predicate"] == "connected_to"
    assert mirathorn["source_domains"] == ["worldbuilding"]


def test_union_supergraph_projection_api_preserves_focus_metadata() -> None:
    payload = _get_projection_payload()

    focus = payload["focus"]
    assert focus["focus_session_id"] == "session-23"
    assert "pc_caelynn" in focus["focused_node_ids"]
    assert "event_session_23_mireward_gate" in focus["focused_node_ids"]
    assert (
        "evidence:session-23:caelynn:recap-mention"
        in focus["focused_evidence_ref_ids"]
    )


def test_union_supergraph_projection_api_returns_json_safe_payload() -> None:
    payload = _get_projection_payload()

    json.dumps(payload)
    assert _is_json_safe(payload)


def test_union_supergraph_projection_api_accepts_explicit_store_path() -> None:
    response = _client().get(
        "/api/live/graph-preview/union-supergraph/projection",
        params={"session_id": "session-23", "store_path": str(DEFAULT_FIXTURE_PATH)},
    )

    assert response.status_code == 200
    assert response.json()["node_views"]["pc_caelynn"]["node_id"] == "pc_caelynn"


def test_union_supergraph_projection_api_missing_store_returns_404(
    tmp_path: Path,
) -> None:
    missing_store_path = tmp_path / "missing-union-supergraph.json"

    response = _client().get(
        "/api/live/graph-preview/union-supergraph/projection",
        params={"session_id": "session-23", "store_path": str(missing_store_path)},
    )

    assert response.status_code == 404
    assert str(missing_store_path) in response.json()["detail"]


def _get_projection_payload() -> dict[str, Any]:
    response = _client().get(
        "/api/live/graph-preview/union-supergraph/projection",
        params={"session_id": "session-23"},
    )
    assert response.status_code == 200
    return response.json()


def _client() -> TestClient:
    return TestClient(create_app())


def _is_json_safe(value: Any) -> bool:
    if value is None or isinstance(value, str | int | float | bool):
        return True
    if isinstance(value, list):
        return all(_is_json_safe(item) for item in value)
    if isinstance(value, dict):
        return all(
            isinstance(key, str) and _is_json_safe(item)
            for key, item in value.items()
        )
    return False
