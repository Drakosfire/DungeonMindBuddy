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
    assert session_ids == {"session-22", "session-23"}


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
