from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from apps.live_control_server.main import create_app

REPO_ROOT = Path(__file__).resolve().parents[1]


def _client() -> TestClient:
    return TestClient(create_app())


def test_manual_review_beds_endpoint_lists_c1s1_and_mirathorn() -> None:
    response = _client().get("/api/live/graph-preview/manual-review/beds")

    assert response.status_code == 200
    payload = response.json()
    assert payload["schema_version"] == "dmb_graph_manual_review_beds_v1"
    bed_ids = {bed["bed_id"] for bed in payload["beds"]}
    assert bed_ids == {"c1s1-stonebridge", "mirathorn-city"}
    for bed in payload["beds"]:
        assert set(bed["variant_names"]) == {"baseline", "edge_and_node_packet"}


def test_manual_review_bed_detail_has_prompt_contexts_and_pass_grouped_nodes() -> None:
    response = _client().get("/api/live/graph-preview/manual-review/beds/c1s1-stonebridge")

    assert response.status_code == 200
    payload = response.json()
    assert payload["schema_version"] == "dmb_graph_manual_review_bed_v1"
    assert set(payload["node_prompt_contexts"].keys()) == {
        "actor_pass",
        "location_pass",
        "collective_pass",
        "object_pass",
        "thread_pass",
    }
    assert payload["edge_prompt_context"]

    baseline = payload["variants"]["baseline"]
    assert baseline["node_count"] == len(baseline["nodes"])
    assert baseline["edge_count"] == len(baseline["edges"])
    pass_names = {node["pass_name"] for node in baseline["nodes"]}
    assert pass_names <= {
        "actor_pass",
        "location_pass",
        "collective_pass",
        "object_pass",
        "thread_pass",
        None,
    }

    edge = baseline["edges"][0]
    assert edge["from_label"]
    assert edge["to_label"]


def test_manual_review_bed_detail_unknown_bed_returns_404() -> None:
    response = _client().get("/api/live/graph-preview/manual-review/beds/unknown-bed")

    assert response.status_code == 404
