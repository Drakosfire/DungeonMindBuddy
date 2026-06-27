"""Tests for graph preview surface API."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.live_control_server.config import SESSION_DIR_ENV, repo_root
from apps.live_control_server.main import create_app
from apps.live_control_server.services.graph_preview_surface import (
    build_graph_preview_surface,
    build_latest_graph_preview_surface,
    discover_graph_preview_runs,
)

ROOT = Path(__file__).resolve().parents[1]
SEED_SESSION = ROOT / "evals/c2_live_prep/live/session_22"
VALID_RUN = (
    "evals/graph_memory_layer/artifacts/category_graph_model_study/"
    "2026-06-26/session_22_gpt-5-4-mini_run1"
)


@pytest.fixture
def isolated_session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    for name in ("live_packet.json", "surface_layout.json", "current_state.json"):
        import shutil

        shutil.copy2(SEED_SESSION / name, tmp_path / name)
    (tmp_path / "event_log.jsonl").write_text("", encoding="utf-8")
    (tmp_path / "job_queue.jsonl").write_text("", encoding="utf-8")
    monkeypatch.setenv(SESSION_DIR_ENV, str(tmp_path))
    return tmp_path


@pytest.fixture
def client(isolated_session: Path) -> TestClient:
    return TestClient(create_app())


def test_discover_graph_preview_runs_includes_committed_cohort() -> None:
    runs = discover_graph_preview_runs(repo_root())
    assert runs
    assert any("session_22" in r.run_dir for r in runs)


def test_build_graph_preview_surface_enriches_paragraph_evidence() -> None:
    fallback_run = (
        "evals/graph_memory_layer/artifacts/category_graph_model_study/"
        "2026-06-26/anchor_quote_n3/session_22_gpt-5-4-mini_run3"
    )
    run_dir = VALID_RUN
    if not (repo_root() / run_dir / "validation_report.json").is_file():
        if (repo_root() / fallback_run / "candidate_output.json").is_file():
            run_dir = fallback_run
        else:
            pytest.skip("category study artifact not present locally")
    payload = build_graph_preview_surface(repo_root(), run_dir)
    assert payload.schema_version == "dmb_graph_preview_surface_v1"
    assert payload.candidates
    with_evidence = [c for c in payload.candidates if c.evidence_refs]
    assert with_evidence
    has_spref = any(ref.source_span_ref_id for c in with_evidence for ref in c.evidence_refs)
    if has_spref:
        assert any(ref.paragraph_text for c in with_evidence for ref in c.evidence_refs)


def test_latest_surface_prefers_resolvable_run() -> None:
    runs = discover_graph_preview_runs(repo_root())
    if not runs:
        pytest.skip("no graph preview runs discovered")
    payload = build_latest_graph_preview_surface(repo_root())
    # If any discovered run carries spref-backed evidence, the default pick must be
    # one whose source-highlight panel can render (resolvable > 0), even when its
    # canonical IR is marked invalid.
    any_resolvable = False
    for run in runs:
        try:
            candidate = build_graph_preview_surface(repo_root(), run.run_dir)
        except Exception:
            continue
        if candidate.health.resolvable_evidence_ref_count > 0:
            any_resolvable = True
            break
    if any_resolvable:
        assert payload.health.resolvable_evidence_ref_count > 0


def test_get_graph_preview_latest(client: TestClient) -> None:
    response = client.get("/api/live/graph-preview/latest")
    assert response.status_code == 200
    body = response.json()
    assert body["schema_version"] == "dmb_graph_preview_surface_v1"
    assert body["health"]["node_count"] >= 1
    assert isinstance(body["candidates"], list)


def test_get_graph_preview_runs(client: TestClient) -> None:
    response = client.get("/api/live/graph-preview/runs")
    assert response.status_code == 200
    body = response.json()
    assert body["schema_version"] == "dmb_graph_preview_surface_v1"
    assert isinstance(body["runs"], list)


def test_get_graph_preview_by_run_dir(client: TestClient) -> None:
    if not (repo_root() / VALID_RUN / "validation_report.json").is_file():
        pytest.skip("category study artifact not present locally")
    response = client.get(
        "/api/live/graph-preview/latest",
        params={"run_dir": VALID_RUN},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["run_dir"] == VALID_RUN
