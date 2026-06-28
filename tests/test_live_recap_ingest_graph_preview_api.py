from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.live_control_server.config import SESSION_DIR_ENV
from apps.live_control_server.main import create_app

ROOT = Path(__file__).resolve().parents[1]
SEED_SESSION = ROOT / "evals/c2_live_prep/live/session_22"
CORPUS_ENV = "DUNGEONMIND_RECAP_INGEST_CORPUS_ROOT"
FIXTURE_DIR = ROOT / "tests/fixtures/graph_memory/category_preview_runner"
CANDIDATE_FIXTURE = FIXTURE_DIR / "candidate_graph_fixture.json"


@pytest.fixture
def client_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[TestClient, Path, Path]:
    for name in ("live_packet.json", "surface_layout.json", "current_state.json"):
        shutil.copy2(SEED_SESSION / name, tmp_path / name)
    (tmp_path / "event_log.jsonl").write_text("", encoding="utf-8")
    (tmp_path / "job_queue.jsonl").write_text("", encoding="utf-8")
    monkeypatch.setenv(SESSION_DIR_ENV, str(tmp_path))

    corpus = ROOT / "out/test_recap_ingest_graph_preview/corpus"
    graph_runs = ROOT / "out/graph_memory/runs/longmont-c2/session-22"
    shutil.rmtree(corpus.parent, ignore_errors=True)
    shutil.rmtree(graph_runs, ignore_errors=True)
    campaign = corpus / "Longmont Campaign/Campaign 2"
    (campaign / "_ingest_staging").mkdir(parents=True, exist_ok=True)
    (campaign / "Session Recaps").mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv(CORPUS_ENV, str(corpus))

    candidate = ROOT / "out/test_recap_ingest_graph_preview/candidate_graph_fixture.json"
    candidate.parent.mkdir(parents=True, exist_ok=True)
    candidate.write_text(CANDIDATE_FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
    try:
        yield TestClient(create_app()), corpus, candidate
    finally:
        shutil.rmtree(corpus.parent, ignore_errors=True)
        shutil.rmtree(graph_runs, ignore_errors=True)


def _prepare_normalized(client: TestClient) -> None:
    raw = "Session 22 Recap\n\nThe group scouts the Mireward road and regroups at dusk."
    stage = client.post(
        "/api/live/recap-ingest",
        json={
            "operation": "stage_preview",
            "campaign_id": "longmont-c2",
            "session": 22,
            "raw_text": raw,
            "slug": "Mireward Road Dogfood",
        },
    )
    assert stage.status_code == 200
    apply = client.post(
        "/api/live/recap-ingest",
        json={
            "operation": "apply_normalize",
            "campaign_id": "longmont-c2",
            "session": 22,
            "slug": "Mireward Road Dogfood",
        },
    )
    assert apply.status_code == 200


def test_recap_ingest_build_graph_preview_bundle_from_normalized_recap(client_env: tuple[TestClient, Path, Path]) -> None:
    client, _corpus, _candidate = client_env
    _prepare_normalized(client)

    response = client.post(
        "/api/live/recap-ingest",
        json={"operation": "build_graph_preview_bundle", "campaign_id": "longmont-c2", "session": 22},
    )

    assert response.status_code == 200
    body = response.json()
    graph = body["ingest_report"]["graph_preview"]
    assert graph["status"] == "source_span_bundle_ready"
    assert (ROOT / graph["manifest_path"]).is_file()
    assert "graph_source_bundle_ready" in body["states"]
    assert "Candidate graph extraction is not wired yet" in graph["blocked_reason"]


def test_recap_ingest_materialize_preview_supergraph_blocks_without_candidate_graph(client_env: tuple[TestClient, Path, Path]) -> None:
    client, _corpus, _candidate = client_env
    _prepare_normalized(client)
    client.post(
        "/api/live/recap-ingest",
        json={"operation": "build_graph_preview_bundle", "campaign_id": "longmont-c2", "session": 22},
    )

    response = client.post(
        "/api/live/recap-ingest",
        json={"operation": "materialize_preview_supergraph", "campaign_id": "longmont-c2", "session": 22},
    )

    assert response.status_code == 200
    graph = response.json()["ingest_report"]["graph_preview"]
    assert "candidate graph required" in graph["blocked_reason"]
    assert graph["preview_union_store_path"] is None


def test_recap_ingest_materialize_preview_supergraph_with_candidate_graph_path(client_env: tuple[TestClient, Path, Path]) -> None:
    client, _corpus, candidate = client_env
    _prepare_normalized(client)

    response = client.post(
        "/api/live/recap-ingest",
        json={
            "operation": "materialize_preview_supergraph",
            "campaign_id": "longmont-c2",
            "session": 22,
            "candidate_graph_path": candidate.relative_to(ROOT).as_posix(),
        },
    )

    assert response.status_code == 200
    body = response.json()
    graph = body["ingest_report"]["graph_preview"]
    assert graph["status"] == "preview_union_store_ready"
    assert graph["can_open_union_graph"] is True
    assert (ROOT / graph["preview_union_store_path"]).is_file()
    assert "preview_union_store_ready" in body["states"]


def test_recap_ingest_rejects_unsafe_candidate_graph_path(client_env: tuple[TestClient, Path, Path]) -> None:
    client, _corpus, _candidate = client_env
    _prepare_normalized(client)

    response = client.post(
        "/api/live/recap-ingest",
        json={
            "operation": "build_graph_preview_bundle",
            "campaign_id": "longmont-c2",
            "session": 22,
            "candidate_graph_path": "../escape.json",
        },
    )

    assert response.status_code == 422
