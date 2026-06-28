from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import apps.live_control_server.routes.graph_preview as graph_preview_route
import apps.live_control_server.services.union_supergraph_projection_adapter as adapter_module
from apps.live_control_server.main import create_app
from evals.graph_memory_layer.graph_preview_runner import (
    GraphPreviewRunnerOptions,
    run_graph_preview_extraction,
)
from graph_memory.ingestion import GraphIngestRunStatus
from graph_memory.union_supergraph.preview_run_materialize import (
    PreviewUnionMaterializeOptions,
    materialize_preview_union_store_from_graph_ingest_run,
)

FIXTURE_DIR = (
    Path(__file__).resolve().parents[1]
    / "tests/fixtures/graph_memory/category_preview_runner"
)
RECAP_PATH = FIXTURE_DIR / "session_24_normalized_recap.md"
CANDIDATE_PATH = FIXTURE_DIR / "candidate_graph_fixture.json"


def test_api_lists_graph_ingest_runs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _preview_union_ready_run(tmp_path, monkeypatch, "out/graph_memory/runs/ready")
    _patch_repo_roots(tmp_path, monkeypatch)

    response = _client().get("/api/live/graph-preview/graph-ingest/runs")

    assert response.status_code == 200
    payload = response.json()
    assert payload["schema_version"] == "dmb_graph_ingest_run_registry_v1"
    assert len(payload["runs"]) == 1
    assert payload["runs"][0]["status"] == "preview_union_store_ready"


def test_api_returns_latest_preview_union_store_ready_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _preview_union_ready_run(tmp_path, monkeypatch, "out/graph_memory/runs/ready")
    _patch_repo_roots(tmp_path, monkeypatch)

    response = _client().get(
        "/api/live/graph-preview/graph-ingest/latest",
        params={"campaign_id": "longmont-c2", "session_id": "session-24"},
    )

    assert response.status_code == 200
    assert (
        response.json()["run"]["preview_union_store_path"]
        == "out/graph_memory/runs/ready/preview_union_supergraph.json"
    )


def test_api_latest_returns_404_when_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_repo_roots(tmp_path, monkeypatch)

    response = _client().get(
        "/api/live/graph-preview/graph-ingest/latest",
        params={"campaign_id": "longmont-c2", "session_id": "session-24"},
    )

    assert response.status_code == 404
    assert (
        "no preview_union_store_ready graph-ingest run found"
        in response.json()["detail"]
    )


def test_projection_api_can_use_latest_graph_ingest_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _preview_union_ready_run(tmp_path, monkeypatch, "out/graph_memory/runs/ready")
    _patch_repo_roots(tmp_path, monkeypatch)

    response = _client().get(
        "/api/live/graph-preview/union-supergraph/projection",
        params={
            "campaign_id": "longmont-c2",
            "session_id": "session-24",
            "use_latest_graph_ingest": "true",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["graph_id"] == "longmont-c2:preview-union-supergraph"
    assert payload["session_id"] == "session-24"
    assert "character_mira" in payload["node_views"]


def _preview_union_ready_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, output_dir: str
):
    monkeypatch.chdir(tmp_path)
    source = tmp_path / "session_24_normalized_recap.md"
    candidate = tmp_path / "candidate_graph_fixture.json"
    source.write_text(RECAP_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    candidate.write_text(CANDIDATE_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    runner_result = run_graph_preview_extraction(
        GraphPreviewRunnerOptions(
            campaign_id="longmont-c2",
            session_id="session-24",
            normalized_recap_path=source,
            output_dir=Path(output_dir),
            candidate_graph_path=candidate,
        )
    )
    assert runner_result.status == GraphIngestRunStatus.CANDIDATE_VALIDATION_READY
    return materialize_preview_union_store_from_graph_ingest_run(
        PreviewUnionMaterializeOptions(manifest_path=runner_result.manifest_path)
    )


def _patch_repo_roots(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(graph_preview_route, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(adapter_module, "repo_root", lambda: tmp_path)


def _client() -> TestClient:
    return TestClient(create_app())
