from pathlib import Path

from fastapi.testclient import TestClient

from apps.live_control_server.main import app
from apps.live_control_server.services import graph_existing_object_resolver as resolver_module
from apps.live_control_server.services.graph_existing_object_resolver import (
    GraphReviewExistingObjectResolverRequest,
    GraphReviewResolverSelectedNode,
    resolve_existing_object_candidates,
)


def _request(live_run_manifest_path=None, **node_overrides):
    node = {
        "node_id": "selected-stone-bridge",
        "label": "Stone Bridge",
        "kind": "location",
        "role": "source_evidence",
        "aliases": [],
        "summary": "River crossing landmark.",
        "source_domains": ["gold_fixture"],
        "adjacent_labels": ["Stone Bridge"],
        "evidence_ref_ids": [],
    }
    node.update(node_overrides)
    return GraphReviewExistingObjectResolverRequest(
        campaign_id="longmont-c1",
        session_id="session-1",
        lane_role="live",
        selected_node=GraphReviewResolverSelectedNode(**node),
        live_run_manifest_path=live_run_manifest_path,
    )


def test_exact_label_match_returns_high_confidence_candidate():
    response = resolve_existing_object_candidates(_request())
    assert response.schema == "dmb_graph_review_existing_object_resolver_response_v1"
    assert response.candidates
    top = response.candidates[0]
    assert "Stone Bridge" in top.label
    assert top.confidence == "high"
    assert top.suggested_action == "link_existing_later"
    assert "exact label match" in top.matched_features


def test_similar_label_returns_review_candidate_without_claiming_write():
    response = resolve_existing_object_candidates(_request(label="Old Stone crossing"))
    assert response.candidates
    top = response.candidates[0]
    assert top.confidence in {"medium", "low", "high"}
    assert top.suggested_action in {"manual_review_needed", "link_existing_later"}
    assert "written" not in top.reason.lower()


def test_incompatible_kind_reduces_confidence_or_requires_manual_review():
    exact = resolve_existing_object_candidates(_request()).candidates[0]
    incompatible = resolve_existing_object_candidates(_request(kind="character")).candidates[0]
    assert incompatible.score < exact.score
    assert incompatible.suggested_action in {"manual_review_needed", "link_existing_later"}


def test_selected_live_candidate_is_excluded(monkeypatch):
    def fake_live_candidates(repo, manifest_path):
        return [
            {
                "candidate_id": "live-node-1",
                "label": "Live Only X",
                "kind": "location",
                "role": "source_evidence",
                "aliases": [],
                "source_domains": ["live_projection"],
                "adjacent_labels": [],
                "source": "live_projection",
            },
            {
                "candidate_id": "live-node-2",
                "label": "Live Only X",
                "kind": "location",
                "role": "source_evidence",
                "aliases": [],
                "source_domains": ["live_projection"],
                "adjacent_labels": [],
                "source": "live_projection",
            },
        ]

    monkeypatch.setattr(resolver_module, "_candidate_dicts_from_live", fake_live_candidates)
    request = _request(node_id="live-node-1", label="Live Only X", live_run_manifest_path="fake.json")
    response = resolve_existing_object_candidates(request)
    assert all(candidate.candidate_id != "live-node-1" for candidate in response.candidates)
    assert any(candidate.candidate_id == "live-node-2" for candidate in response.candidates)


def test_endpoint_does_not_mutate_gold_fixture_file():
    fixture = Path("evals/graph_memory_layer/examples/session_1_candidate_graph_gold/candidate_graph_gold.json")
    before = fixture.read_bytes()
    client = TestClient(app)
    response = client.post(
        "/api/live/graph-preview/existing-object-resolver/candidates",
        json=_request().model_dump(mode="json"),
    )
    assert response.status_code == 200
    assert response.json()["candidates"][0]["suggested_action"]
    assert fixture.read_bytes() == before


def test_unsupported_campaign_session_is_clear_422():
    client = TestClient(app)
    payload = _request().model_dump(mode="json")
    payload["campaign_id"] = "wrong-campaign"
    response = client.post("/api/live/graph-preview/existing-object-resolver/candidates", json=payload)
    assert response.status_code == 422
    assert "belongs to" in response.json()["detail"]


def test_session_without_gold_fixture_can_search_npc_registry():
    response = resolve_existing_object_candidates(
        GraphReviewExistingObjectResolverRequest(
            campaign_id="longmont-c1",
            session_id="session-3",
            lane_role="live",
            selected_node=GraphReviewResolverSelectedNode(
                node_id="__graph_review_query_search__",
                label="bubbles",
            ),
            query="bubbles",
            include_gm_private=True,
        )
    )
    assert response.candidates
    bubble_candidates = [
        candidate
        for candidate in response.candidates
        if "bubble" in candidate.label.lower()
    ]
    assert bubble_candidates
    assert any("float goat" in candidate.label.lower() for candidate in bubble_candidates)
    assert any("gold fixture" in warning.lower() for warning in response.warnings)
