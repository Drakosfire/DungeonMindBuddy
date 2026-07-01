"""Tests for recap artifact registry."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.live_control_server.config import SESSION_DIR_ENV, repo_root
from apps.live_control_server.main import create_app
from apps.live_control_server.services.recap_artifacts import (
    RECAP_ARTIFACTS_ENV,
    RecapArtifactRecord,
    list_recap_artifact_records,
    normalize_session_id,
    resolve_recap_artifact_record,
    sync_recap_artifacts_registry,
    upsert_recap_artifact_record,
)

ROOT = Path(__file__).resolve().parents[1]
SEED_SESSION = ROOT / "evals/c2_live_prep/live/session_22"


@pytest.fixture
def isolated_session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    import shutil

    for name in ("live_packet.json", "surface_layout.json", "current_state.json"):
        shutil.copy2(SEED_SESSION / name, tmp_path / name)
    (tmp_path / "event_log.jsonl").write_text("", encoding="utf-8")
    (tmp_path / "job_queue.jsonl").write_text("", encoding="utf-8")
    monkeypatch.setenv(SESSION_DIR_ENV, str(tmp_path))
    return tmp_path


@pytest.fixture
def client(isolated_session: Path) -> TestClient:
    return TestClient(create_app())


@pytest.fixture
def registry_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "registries" / "recap_artifacts.json"
    monkeypatch.setenv(RECAP_ARTIFACTS_ENV, str(path))
    return path


def test_normalize_session_id() -> None:
    assert normalize_session_id(22) == "session-22"
    assert normalize_session_id("22") == "session-22"
    assert normalize_session_id("session-23") == "session-23"


def test_sync_builds_session_22_record(registry_path: Path) -> None:
    document = sync_recap_artifacts_registry(ROOT)
    assert document.records
    record = next((r for r in document.records if r.session_id == "session-22"), None)
    assert record is not None
    assert record.campaign_id == "longmont-c2"
    assert record.run_bundle_uri.endswith("session_22_category_study")
    assert record.graph_run_refs
    assert record.default_graph_run_uri is None
    assert registry_path.is_file()


def test_registry_contains_locators_not_bodies(registry_path: Path) -> None:
    sync_recap_artifacts_registry(ROOT)
    payload = json.loads(registry_path.read_text(encoding="utf-8"))
    serialized = json.dumps(payload)
    assert "candidate_graph" not in serialized
    assert "reconciled_candidate_graph" not in serialized
    assert "llm_response" not in serialized


def test_resolve_by_campaign_and_session(registry_path: Path) -> None:
    sync_recap_artifacts_registry(ROOT)
    record = resolve_recap_artifact_record(
        ROOT,
        campaign_id="longmont-c2",
        session_id="session-22",
    )
    assert record.session_id == "session-22"
    assert record.source_recap_path.endswith("Session 22 - Mireward Road and Lysandro.md")


def test_resolve_session_21_record(registry_path: Path) -> None:
    sync_recap_artifacts_registry(ROOT)
    record = resolve_recap_artifact_record(
        ROOT,
        campaign_id="longmont-c2",
        session_id="session-21",
    )
    assert record.session_id == "session-21"
    assert record.run_bundle_uri.endswith("session_21_category_study")
    assert record.source_recap_path.endswith("Session 21 - Drake Nest Mirathorn Call.md")


def test_upsert_explicit_record(registry_path: Path) -> None:
    sync_recap_artifacts_registry(ROOT)
    now = "2026-06-27T00:00:00Z"
    record = RecapArtifactRecord(
        artifact_id="longmont-c2/session-99",
        campaign_id="longmont-c2",
        session_id="session-99",
        source_recap_path="corpus/example/session-99.md",
        run_bundle_uri="evals/graph_memory_layer/runs/live_recap_ingest/session_99_test",
        run_manifest_uri="evals/graph_memory_layer/runs/live_recap_ingest/session_99_test/run_manifest.json",
        source_span_index_uri="evals/graph_memory_layer/runs/live_recap_ingest/session_99_test/source_span_index.json",
        registered_at=now,
        updated_at=now,
        registry_source="explicit",
    )
    upsert_recap_artifact_record(ROOT, record)
    records = list_recap_artifact_records(ROOT, campaign_id="longmont-c2")
    assert any(r.artifact_id == "longmont-c2/session-99" for r in records)


def test_sync_merges_session_1_eval_projection_dogfood(registry_path: Path) -> None:
    document = sync_recap_artifacts_registry(ROOT)
    record = next(
        (r for r in document.records if r.campaign_id == "longmont-c1" and r.session_id == "session-1"),
        None,
    )
    assert record is not None
    assert record.run_manifest_uri.endswith(
        "session_1_vocabulary_ablation_projection_dogfood/graph_ingest_run_manifest.json"
    )
    assert record.graph_run_refs
    assert record.source_span_index_uri.endswith("source_span_index.json")


def test_get_recap_artifacts_api(client: TestClient, registry_path: Path) -> None:
    response = client.get(
        "/api/live/graph-preview/artifacts",
        params={"campaign_id": "longmont-c2"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["schema_version"] == "dmb_recap_artifacts_registry_v1"
    assert any(r["session_id"] == "session-22" for r in body["records"])


def test_recap_by_session_id_api(client: TestClient, registry_path: Path) -> None:
    response = client.get(
        "/api/live/graph-preview/recap",
        params={"campaign_id": "longmont-c2", "session_id": "session-22"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["schema_version"] == "dmb_recap_graph_presentation_v1"
    assert body["nodes"]


def test_recap_by_session_21_without_graph_runs(client: TestClient, registry_path: Path) -> None:
    response = client.get(
        "/api/live/graph-preview/recap",
        params={"campaign_id": "longmont-c2", "session_id": "session-21"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["schema_version"] == "dmb_recap_graph_presentation_v1"
    assert "Drake Nest" in body["markdown"] or "Mirathorn" in body["markdown"]
    assert body["links"] == []
