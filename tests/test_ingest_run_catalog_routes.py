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
    client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, application_state_dsn: str
) -> None:
    import hashlib

    from apps.live_control_server.services import extract_promote as promote_svc
    from apps.live_control_server.services import promotable_ingest_run as promotable_mod
    from apps.live_control_server.services.source_artifact_registry import (
        create_source_artifact_from_workspace_document,
    )
    from apps.live_control_server.services.workspace_document_registry import (
        create_workspace_document,
        mark_workspace_document_committed,
    )

    # Exact-review resolves SourceArtifact + component bytes through extract_promote's
    # repo_root; pin it to the same tmp_path as the SourceArtifact registry.
    monkeypatch.setattr(promote_svc, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(promotable_mod, "repo_root", lambda: tmp_path)

    # Valid SourceArtifact identity first — W10 requires the evidence seam to
    # reach missing run-pinned component bytes, not unknown source_artifact_id.
    record = create_workspace_document(
        tmp_path,
        title="W10 Lore",
        campaign_id="eldyrwild",
        kind="worldbuilding_source",
        source_domain="worldbuilding",
        document_class="lore",
        authority_state="draft",
        visibility_state="internal",
    )
    committed = mark_workspace_document_committed(
        tmp_path, record.document_id, expected_revision=1
    )
    source_path = tmp_path / committed.target_relpath
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_bytes = b"# W10\n\nCanonical source for missing-bytes witness.\n"
    source_path.write_bytes(source_bytes)
    source_digest = hashlib.sha256(source_bytes).hexdigest()
    artifact = create_source_artifact_from_workspace_document(
        tmp_path,
        document_id=committed.document_id,
        expected_revision=committed.revision,
        expected_content_sha256=source_digest,
    )

    missing_span_uri = "repo://out/graph_memory/runs/er_bytes_missing/missing-spans.json"
    missing_graph_uri = "repo://out/graph_memory/runs/er_bytes_missing/missing-graph.json"
    created = create_extraction_run(
        _run(
            run_id="er_bytes_missing",
            source_artifact_id=artifact.source_artifact_id,
            source_domain="worldbuilding",
            campaign_id="eldyrwild",
            session_id=None,
            components={
                "source_artifact": ExtractionRunComponentRef(
                    kind=ExtractionRunComponentKind.SOURCE_ARTIFACT,
                    uri=artifact.uri,
                    sha256=source_digest,
                    exists=True,
                ),
                "source_span_index": ExtractionRunComponentRef(
                    kind=ExtractionRunComponentKind.SOURCE_SPAN_INDEX,
                    uri=missing_span_uri,
                    sha256="b" * 64,
                    exists=False,
                ),
                "candidate_graph": ExtractionRunComponentRef(
                    kind=ExtractionRunComponentKind.CANDIDATE_GRAPH,
                    uri=missing_graph_uri,
                    sha256="c" * 64,
                    exists=False,
                ),
            },
        )
    )
    assert not (tmp_path / "out/graph_memory/runs").exists()

    def _boom(*_args, **_kwargs):
        raise AssertionError("legacy graph ingest registry must not be consulted")

    monkeypatch.setattr(
        "apps.live_control_server.services.graph_ingest_run_registry.discover_graph_ingest_runs",
        _boom,
    )
    monkeypatch.setattr(
        "apps.live_control_server.services.promotable_ingest_run._find_manifests_for_run_id",
        _boom,
    )

    response = client.get("/api/live/graph-preview/extraction-runs")
    assert response.status_code == 200
    assert any(row["run_id"] == created.run_id for row in response.json()["runs"])
    exact = client.get(f"/api/live/graph-preview/extraction-runs/{created.run_id}")
    assert exact.status_code == 200
    assert exact.json()["run_id"] == created.run_id
    assert exact.json()["source_artifact_id"] == artifact.source_artifact_id

    # W10: identity + SourceArtifact fixed; missing run-pinned bytes fail exact review.
    review = client.get(f"/api/live/extract-promote/runs/{created.run_id}/review-package")
    assert review.status_code == 422
    body = review.json()
    detail = body.get("detail") if isinstance(body, dict) else body
    payload = detail if isinstance(detail, dict) else body
    assert isinstance(payload, dict)
    message = str(payload.get("message") or payload)
    assert "component file missing" in message.lower()
    assert "unknown source_artifact_id" not in message.lower()
    assert "manifest" not in message.lower() or "fallback" not in message.lower()
    assert not payload.get("fallback_run_id")

    again = client.get("/api/live/graph-preview/extraction-runs")
    assert any(row["run_id"] == created.run_id for row in again.json()["runs"])


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
