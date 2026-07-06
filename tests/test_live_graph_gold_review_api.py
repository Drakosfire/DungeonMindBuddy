from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import apps.live_control_server.routes.graph_preview as graph_preview_route
import apps.live_control_server.services.graph_gold_review as graph_gold_review_module
import apps.live_control_server.services.union_supergraph_projection_adapter as adapter_module
from apps.live_control_server.main import create_app
from apps.live_control_server.services.graph_ingest_run_registry import GraphIngestRunRegistryError
from evals.graph_memory_layer.graph_preview_runner import (
    GraphPreviewRunnerOptions,
    run_graph_preview_extraction,
)
from evals.graph_memory_layer.session_23_candidate_graph_gold_fixture import (
    load_gold_candidate_graph_dict,
)
from evals.graph_memory_layer.session_1_recap_ingest_fixture import (
    load_expected_normalized_recap as load_session_1_expected_normalized_recap,
)
from evals.graph_memory_layer.session_23_recap_ingest_fixture import load_expected_normalized_recap
from graph_memory.ingestion.graph_ingest_run import GraphIngestRunStatus
from graph_memory.union_supergraph.preview_run_materialize import (
    PreviewUnionMaterializeOptions,
    materialize_preview_union_store_from_graph_ingest_run,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_gold_review_sessions_endpoint_lists_s22_and_s23() -> None:
    response = _client().get("/api/live/graph-preview/gold-review/sessions")

    assert response.status_code == 200
    payload = response.json()
    assert payload["schema_version"] == "dmb_graph_gold_review_sessions_v1"
    session_ids = {item["session_id"] for item in payload["sessions"]}
    assert session_ids == {"session-1", "session-22", "session-23", "mirathorn-city"}


def test_gold_review_compare_without_live_run_returns_gold_only_scores(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _raise_no_run(*_args: object, **_kwargs: object) -> None:
        raise GraphIngestRunRegistryError(
            "no preview_union_store_ready graph-ingest run found",
            status_code=404,
        )

    monkeypatch.setattr(
        graph_gold_review_module,
        "resolve_latest_preview_union_graph_ingest_run",
        _raise_no_run,
    )
    response = _client().get(
        "/api/live/graph-preview/gold-review/compare",
        params={"campaign_id": "longmont-c2", "session_id": "session-23"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["schema_version"] == "dmb_graph_gold_review_compare_v1"
    assert payload["gold_fixture_id"] == "graph-memory:session-23-candidate-graph-gold:v0"
    assert payload["live_run"] is None
    assert payload["comparison"]["scores"]["node_recall"] == 0.0
    assert payload["comparison"]["coverage"]["gold_nodes_total"] > 0


def test_gold_review_compare_uses_graph_ingest_candidate_graph(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest_path = _preview_union_ready_run_for_session_23(tmp_path, monkeypatch)
    _patch_repo_roots(tmp_path, monkeypatch)

    response = _client().get(
        "/api/live/graph-preview/gold-review/compare",
        params={
            "campaign_id": "longmont-c2",
            "session_id": "session-23",
            "manifest_path": manifest_path,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["live_run"]["manifest_path"] == manifest_path
    assert payload["comparison"]["scores"]["node_recall"] == 1.0
    assert payload["comparison"]["scores"]["edge_recall"] == 1.0


def test_gold_review_evidence_endpoint_returns_side_by_side_payload(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest_path = _preview_union_ready_run_for_session_23(tmp_path, monkeypatch)
    _patch_repo_roots(tmp_path, monkeypatch)

    response = _client().get(
        "/api/live/graph-preview/gold-review/evidence",
        params={
            "campaign_id": "longmont-c2",
            "session_id": "session-23",
            "manifest_path": manifest_path,
            "object_kind": "nodes",
            "object_id": "node:lysandro",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["schema_version"] == "dmb_graph_gold_review_evidence_v1"
    assert payload["matched"] is True
    assert payload["gold"]["object_id"] == "node:lysandro"
    assert payload["live"]["object_id"] == "node:lysandro"
    assert payload["gold"]["evidence"]
    assert payload["live"]["evidence"]


def test_gold_review_projection_endpoint_renders_session_1_gold_recap_read_only() -> None:
    fixture_path = REPO_ROOT / "evals/graph_memory_layer/examples/session_1_candidate_graph_gold/candidate_graph_gold.json"
    before = fixture_path.read_bytes()

    response = _client().get(
        "/api/live/graph-preview/gold-review/projection",
        params={"campaign_id": "longmont-c1", "session_id": "session-1"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["source_kind"] == "gold_fixture"
    assert payload["campaign_id"] == "longmont-c1"
    assert payload["session_id"] == "session-1"
    assert payload["gold_fixture_relpath"] == (
        "evals/graph_memory_layer/examples/session_1_candidate_graph_gold/candidate_graph_gold.json"
    )
    # The gold source recap has no inline dmb-node links (it's plain corpus
    # prose); anchored mentions get one spliced into the *returned* markdown so
    # the frontend can render pills by parsing links directly out of the text,
    # the same way it does for the live lane. The underlying corpus fixture on
    # disk is never touched.
    assert payload["markdown"] != load_session_1_expected_normalized_recap()
    assert "node:heroes-party" in payload["node_views"]
    assert payload["node_views"]["node:heroes-party"]["label"] == "Heroes / Party"
    heroes_mention = next(
        mention for mention in payload["mentions"] if mention["node_id"] == "node:heroes-party"
    )
    assert heroes_mention["anchor_status"] == "anchored"
    assert isinstance(heroes_mention["start_offset"], int)
    assert isinstance(heroes_mention["end_offset"], int)
    slice_ = payload["markdown"][heroes_mention["start_offset"] : heroes_mention["end_offset"]]
    assert slice_ == f"[{heroes_mention['label']}](dmb-node:node:heroes-party)"
    assert fixture_path.read_bytes() == before


def test_gold_review_projection_rejects_unsupported_fixture_version() -> None:
    response = _client().get(
        "/api/live/graph-preview/gold-review/projection",
        params={
            "campaign_id": "longmont-c1",
            "session_id": "session-1",
            "fixture_version": "not-a-real-version",
        },
    )

    assert response.status_code == 422
    assert "fixture_version selection is not supported yet" in response.json()["detail"]


def test_gold_review_projection_keeps_unanchored_nodes_non_fatal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = graph_gold_review_module._session_entry("session-1")["load_gold_graph_dict"]()

    def _load_gold_graph_with_unanchored_node() -> dict[str, object]:
        graph = json.loads(json.dumps(original))
        graph["nodes"].append(
            {
                "node_id": "node:unanchored-test",
                "label": "Unanchored Test Node",
                "node_type": "npc",
                "evidence_refs": [
                    {
                        "source_anchor_id": "anchor:not-in-session-1-markdown",
                        "source_artifact_id": "source-artifact:session-1-normalized-recap",
                        "label": "missing",
                    }
                ],
            }
        )
        return graph

    monkeypatch.setitem(
        graph_gold_review_module._session_entry("session-1"),
        "load_gold_graph_dict",
        _load_gold_graph_with_unanchored_node,
    )

    payload = graph_gold_review_module.build_gold_graph_projection(
        campaign_id="longmont-c1",
        session_id="session-1",
    ).model_dump(mode="json")

    assert "node:unanchored-test" in payload["node_views"]
    mention = next(
        item for item in payload["mentions"] if item["node_id"] == "node:unanchored-test"
    )
    assert mention["anchor_status"] == "unanchored"
    assert mention["start_offset"] is None


def test_gold_review_vocabulary_ablation_endpoint_loads_session_23_artifact() -> None:
    response = _client().get(
        "/api/live/graph-preview/gold-review/vocabulary-ablation",
        params={"campaign_id": "longmont-c2", "session_id": "session-23"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["schema_version"] == "dmb_vocabulary_ablation_dogfood_v1"
    assert payload["session_id"] == "session-23"
    assert payload["comparison"]["best_variant"] == "edge_and_node_packet"
    assert len(payload["variant_setup"]) == 4


def test_gold_review_vocabulary_ablation_endpoint_404_for_unsupported_session() -> None:
    response = _client().get(
        "/api/live/graph-preview/gold-review/vocabulary-ablation",
        params={"campaign_id": "longmont-c2", "session_id": "session-22"},
    )

    assert response.status_code == 404


def test_gold_review_service_is_not_imported_by_ingest_extraction_paths() -> None:
    import apps.live_control_server.services.recap_graph_preview_ingest as ingest_module
    import apps.live_control_server.routes.recap_ingest as recap_route

    source_paths = {
        Path(ingest_module.__file__).read_text(encoding="utf-8"),
        Path(recap_route.__file__).read_text(encoding="utf-8"),
    }
    assert all("graph_gold_review" not in source for source in source_paths)


def _preview_union_ready_run_for_session_23(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> str:
    monkeypatch.chdir(tmp_path)
    recap_path = tmp_path / "session_23_normalized_recap.md"
    candidate_path = tmp_path / "candidate_graph.json"
    recap_path.write_text(load_expected_normalized_recap(), encoding="utf-8")
    candidate_path.write_text(
        json.dumps(load_gold_candidate_graph_dict(), indent=2),
        encoding="utf-8",
    )
    runner_result = run_graph_preview_extraction(
        GraphPreviewRunnerOptions(
            campaign_id="longmont-c2",
            session_id="session-23",
            normalized_recap_path=recap_path,
            output_dir=Path("out/graph_memory/runs/session_23_gold_review"),
            candidate_graph_path=candidate_path,
        )
    )
    assert runner_result.status == GraphIngestRunStatus.CANDIDATE_VALIDATION_READY
    materialize_preview_union_store_from_graph_ingest_run(
        PreviewUnionMaterializeOptions(manifest_path=runner_result.manifest_path)
    )
    return "out/graph_memory/runs/session_23_gold_review/graph_ingest_run_manifest.json"


def _patch_repo_roots(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(graph_preview_route, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(adapter_module, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(graph_gold_review_module, "repo_root", lambda: tmp_path)


def _client() -> TestClient:
    return TestClient(create_app())
