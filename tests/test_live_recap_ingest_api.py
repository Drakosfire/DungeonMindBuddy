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


def _seed_corpus(tmp_path: Path) -> Path:
    corpus = tmp_path / "corpus/eldyrwild-markdown"
    campaign = corpus / "Longmont Campaign/Campaign 2"
    (campaign / "_ingest_staging").mkdir(parents=True, exist_ok=True)
    (campaign / "Session Recaps").mkdir(parents=True, exist_ok=True)
    return corpus


@pytest.fixture
def isolated_session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    for name in ("live_packet.json", "surface_layout.json", "current_state.json"):
        shutil.copy2(SEED_SESSION / name, tmp_path / name)
    (tmp_path / "event_log.jsonl").write_text("", encoding="utf-8")
    (tmp_path / "job_queue.jsonl").write_text("", encoding="utf-8")
    monkeypatch.setenv(SESSION_DIR_ENV, str(tmp_path))
    corpus = _seed_corpus(tmp_path)
    monkeypatch.setenv(CORPUS_ENV, str(corpus))
    return tmp_path


@pytest.fixture
def client(isolated_session: Path) -> TestClient:
    return TestClient(create_app())


def _raw_text() -> str:
    return (
        "Session 22 Recap\n\n"
        "The group turns their focus toward the Reach road.\n\n"
        "After another failed attempt to contact Mirathorn, Caeylynn keeps watch."
    )


def test_stage_preview_accepts_raw_text_and_returns_status_schema(client: TestClient, isolated_session: Path) -> None:
    response = client.post(
        "/api/live/recap-ingest",
        json={
            "operation": "stage_preview",
            "campaign_id": "longmont-c2",
            "session": 22,
            "raw_text": _raw_text(),
            "slug": "Mireward Road and Lysandro",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["schema"] == "dmb_raw_recap_ingest_status_v1"
    assert body["campaign_id"] == "longmont-c2"
    assert "recap_preview_created" in body["states"]
    assert body["authority"]["canonical_recap"] == "canon_play"
    assert isinstance(body["entity_spelling_audit"], list)


def test_stage_preview_stages_and_previews_only(client: TestClient, isolated_session: Path) -> None:
    response = client.post(
        "/api/live/recap-ingest",
        json={
            "operation": "stage_preview",
            "campaign_id": "longmont-c2",
            "session": 22,
            "raw_text": _raw_text(),
            "slug": "Mireward Road and Lysandro",
        },
    )
    assert response.status_code == 200
    body = response.json()
    corpus = Path(isolated_session / "corpus/eldyrwild-markdown")
    staged = corpus / str(body["paths"]["staged_raw_notes"])
    canonical = corpus / str(body["paths"]["canonical_recap"])
    assert staged.is_file()
    assert not canonical.exists()


def test_stage_preview_rejects_empty_raw_text(client: TestClient) -> None:
    response = client.post(
        "/api/live/recap-ingest",
        json={
            "operation": "stage_preview",
            "campaign_id": "longmont-c2",
            "session": 22,
            "raw_text": "   ",
            "slug": "Mireward Road and Lysandro",
        },
    )
    assert response.status_code == 422


def test_stage_preview_rejects_raw_path_input(client: TestClient) -> None:
    response = client.post(
        "/api/live/recap-ingest",
        json={
            "operation": "stage_preview",
            "campaign_id": "longmont-c2",
            "session": 22,
            "raw_text": _raw_text(),
            "raw_path": "/tmp/notes.md",
            "slug": "Mireward Road and Lysandro",
        },
    )
    assert response.status_code == 422


def test_apply_normalize_requires_non_generic_slug_or_title(client: TestClient) -> None:
    response = client.post(
        "/api/live/recap-ingest",
        json={
            "operation": "apply_normalize",
            "campaign_id": "longmont-c2",
            "session": 22,
            "slug": "Recap",
        },
    )
    assert response.status_code == 422


def test_apply_normalize_reuses_staged_raw_and_returns_breadcrumb_required(
    client: TestClient, isolated_session: Path
) -> None:
    stage = client.post(
        "/api/live/recap-ingest",
        json={
            "operation": "stage_preview",
            "campaign_id": "longmont-c2",
            "session": 22,
            "raw_text": _raw_text(),
            "slug": "Mireward Road and Lysandro",
        },
    )
    assert stage.status_code == 200
    apply = client.post(
        "/api/live/recap-ingest",
        json={
            "operation": "apply_normalize",
            "campaign_id": "longmont-c2",
            "session": 22,
            "slug": "Mireward Road and Lysandro",
        },
    )
    assert apply.status_code == 200
    body = apply.json()
    assert body["status"] == "breadcrumb_required"
    corpus = Path(isolated_session / "corpus/eldyrwild-markdown")
    canonical = corpus / str(body["paths"]["canonical_recap"])
    assert canonical.exists()


def test_materialize_session_memory_returns_breadcrumb_required_when_missing(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/live/recap-ingest",
        json={
            "operation": "materialize_session_memory",
            "campaign_id": "longmont-c2",
            "session": 22,
            "slug": "Mireward Road and Lysandro",
            "check": True,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "breadcrumb_required"
    assert "session_memory_skipped" in body["states"]


def test_api_never_writes_live_workspace_files(client: TestClient, isolated_session: Path) -> None:
    watched = {
        name: (isolated_session / name).read_bytes()
        for name in ("live_packet.json", "event_log.jsonl", "job_queue.jsonl", "current_state.json")
    }
    response = client.post(
        "/api/live/recap-ingest",
        json={
            "operation": "stage_preview",
            "campaign_id": "longmont-c2",
            "session": 22,
            "raw_text": _raw_text(),
            "slug": "Mireward Road and Lysandro",
        },
    )
    assert response.status_code == 200
    for name, value in watched.items():
        assert (isolated_session / name).read_bytes() == value


def test_api_never_writes_embedding_or_retrieval_indexes(client: TestClient, isolated_session: Path) -> None:
    response = client.post(
        "/api/live/recap-ingest",
        json={
            "operation": "stage_preview",
            "campaign_id": "longmont-c2",
            "session": 22,
            "raw_text": _raw_text(),
            "slug": "Mireward Road and Lysandro",
        },
    )
    assert response.status_code == 200
    corpus = Path(isolated_session / "corpus/eldyrwild-markdown")
    for file in corpus.rglob("*"):
        if not file.is_file():
            continue
        assert "embedding" not in file.name.lower()
        assert file.suffix not in {".faiss", ".npy"}


def test_invalid_operation_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/live/recap-ingest",
        json={
            "operation": "not_valid",
            "campaign_id": "longmont-c2",
            "session": 22,
            "slug": "Mireward Road and Lysandro",
        },
    )
    assert response.status_code == 422
