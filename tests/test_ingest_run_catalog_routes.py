from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from apps.live_control_server.main import create_app
from application_state.errors import (
    ApplicationStateIntegrityError,
    ApplicationStateMigrationError,
    ApplicationStateUnavailableError,
)
from application_state.ingest.service import create_extraction_run
from graph_memory.ingestion.extraction_run import (
    ExtractionRun,
    ExtractionRunComponentKind,
    ExtractionRunComponentRef,
    ExtractionRunStatus,
)


@pytest.fixture
def client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, application_state_dsn: str
) -> TestClient:
    monkeypatch.setattr("apps.live_control_server.routes.graph_preview.repo_root", lambda: tmp_path)
    return TestClient(create_app())


def _run(*, run_id: str | None = None, **overrides) -> ExtractionRun:
    now = "2026-09-03T18:00:00Z"
    payload = {
        "run_id": run_id or f"er_{uuid4().hex[:12]}",
        "source_artifact_id": "sa_world_1",
        "source_domain": "recap",
        "status": ExtractionRunStatus.REVIEWABLE,
        "revision": 1,
        "campaign_id": "longmont-c2",
        "session_id": "session-23",
        "created_at": now,
        "updated_at": now,
        "components": {
            "source_artifact": ExtractionRunComponentRef(
                kind=ExtractionRunComponentKind.SOURCE_ARTIFACT,
                uri="repo://missing.md",
                sha256="a" * 64,
                exists=False,
            ),
            "source_span_index": ExtractionRunComponentRef(
                kind=ExtractionRunComponentKind.SOURCE_SPAN_INDEX,
                uri="repo://missing-spans.json",
                sha256="b" * 64,
                exists=False,
            ),
            "candidate_graph": ExtractionRunComponentRef(
                kind=ExtractionRunComponentKind.CANDIDATE_GRAPH,
                uri="repo://missing-graph.json",
                sha256="c" * 64,
                exists=False,
            ),
        },
    }
    payload.update(overrides)
    return ExtractionRun.model_validate(payload)


def test_w1_list_reads_app_state_only_when_legacy_registry_explodes(
    client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, application_state_dsn: str
) -> None:
    created = create_extraction_run(_run(run_id="er_canonical_a"))
    missing_out = tmp_path / "out/graph_memory/runs"
    assert not missing_out.exists()

    def _boom(*_args, **_kwargs):
        raise AssertionError("legacy graph ingest registry must not be consulted")

    monkeypatch.setattr(
        "apps.live_control_server.services.graph_ingest_run_registry.discover_graph_ingest_runs",
        _boom,
    )
    monkeypatch.setattr(
        "apps.live_control_server.routes.graph_preview.discover_graph_ingest_runs",
        _boom,
    )

    response = client.get("/api/live/graph-preview/extraction-runs")
    assert response.status_code == 200
    body = response.json()
    assert body["schema_version"] == "dmb_extraction_run_catalog_v1"
    assert [row["run_id"] for row in body["runs"]] == [created.run_id]
    assert body["runs"][0]["status"] == "reviewable"
    assert body["runs"][0]["revision"] == 1
    assert "manifest_path" not in body["runs"][0]
    assert "preview_union_available" not in body["runs"][0]


def test_w2_w10_missing_out_and_missing_component_bytes_do_not_hide_run(
    client: TestClient, tmp_path: Path, application_state_dsn: str
) -> None:
    created = create_extraction_run(_run(run_id="er_bytes_missing"))
    assert not (tmp_path / "out/graph_memory/runs").exists()
    response = client.get("/api/live/graph-preview/extraction-runs")
    assert response.status_code == 200
    assert any(row["run_id"] == created.run_id for row in response.json()["runs"])
    exact = client.get(f"/api/live/graph-preview/extraction-runs/{created.run_id}")
    assert exact.status_code == 200
    assert exact.json()["run_id"] == created.run_id


def test_w11_zero_rows_is_empty_success(
    client: TestClient, application_state_dsn: str
) -> None:
    response = client.get("/api/live/graph-preview/extraction-runs")
    assert response.status_code == 200
    assert response.json() == {
        "schema_version": "dmb_extraction_run_catalog_v1",
        "runs": [],
    }


def test_w12_unavailable_maps_typed_code(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, application_state_dsn: str
) -> None:
    def _raise():
        raise ApplicationStateUnavailableError("dsn missing")

    monkeypatch.setattr(
        "apps.live_control_server.services.ingest_run_catalog.list_extraction_runs",
        _raise,
    )
    response = client.get("/api/live/graph-preview/extraction-runs")
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "ingest_run_catalog_unavailable"


def test_w12_schema_unavailable_maps_typed_code(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, application_state_dsn: str
) -> None:
    def _raise():
        raise ApplicationStateMigrationError("behind head")

    monkeypatch.setattr(
        "apps.live_control_server.services.ingest_run_catalog.list_extraction_runs",
        _raise,
    )
    response = client.get("/api/live/graph-preview/extraction-runs")
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "ingest_run_catalog_schema_unavailable"


def test_w13_integrity_maps_typed_code(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, application_state_dsn: str
) -> None:
    def _raise():
        raise ApplicationStateIntegrityError("catalog lineage broken")

    monkeypatch.setattr(
        "apps.live_control_server.services.ingest_run_catalog.list_extraction_runs",
        _raise,
    )
    response = client.get("/api/live/graph-preview/extraction-runs")
    assert response.status_code == 500
    assert response.json()["detail"]["code"] == "ingest_run_catalog_integrity_error"
