from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator

from apps.live_control_server.config import SESSION_DIR_ENV
from apps.live_control_server.main import create_app

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "evals/c2_live_prep/live/schemas"
SEED_SESSION = ROOT / "evals/c2_live_prep/live/session_22"
COMMITTED_EVENT_LOG = SEED_SESSION / "event_log.jsonl"
COMMITTED_JOB_QUEUE = SEED_SESSION / "job_queue.jsonl"


def _load_schema(name: str) -> dict:
    return json.loads((SCHEMA_DIR / name).read_text(encoding="utf-8"))


@pytest.fixture
def isolated_session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    for name in ("live_packet.json", "surface_layout.json", "current_state.json"):
        shutil.copy2(SEED_SESSION / name, tmp_path / name)
    (tmp_path / "event_log.jsonl").write_text("", encoding="utf-8")
    (tmp_path / "job_queue.jsonl").write_text("", encoding="utf-8")
    monkeypatch.setenv(SESSION_DIR_ENV, str(tmp_path))
    return tmp_path


@pytest.fixture
def client(isolated_session: Path) -> TestClient:
    return TestClient(create_app())


def test_query_weather_7_persists_event_and_job(
    client: TestClient,
    isolated_session: Path,
) -> None:
    before_events = COMMITTED_EVENT_LOG.read_bytes()
    before_jobs = COMMITTED_JOB_QUEUE.read_bytes()

    response = client.post(
        "/api/live/query",
        json={
            "campaign_id": "longmont-c2",
            "session": 22,
            "mode": "live",
            "text": "Weather 7. Caelynn Nature 19.",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert "Hail dent" in body["answer"]
    assert body["classification"]["event_type"] == "roll_result"
    assert len(body["events_written"]) >= 1
    assert len(body["jobs_queued"]) >= 1

    events = (isolated_session / "event_log.jsonl").read_text(encoding="utf-8").strip().splitlines()
    jobs = (isolated_session / "job_queue.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(events) == 1
    assert len(jobs) == 1

    event_validator = Draft202012Validator(
        _load_schema("live_event.schema.json"),
        format_checker=Draft202012Validator.FORMAT_CHECKER,
    )
    job_validator = Draft202012Validator(
        _load_schema("live_job.schema.json"),
        format_checker=Draft202012Validator.FORMAT_CHECKER,
    )
    event_row = json.loads(events[0])
    job_row = json.loads(jobs[0])
    event_validator.validate(event_row)
    job_validator.validate(job_row)
    assert event_row["derived_fields"]["skill_check"]["total"] == 19
    assert job_row["job_type"] == "benchmark_candidate"

    assert COMMITTED_EVENT_LOG.read_bytes() == before_events
    assert COMMITTED_JOB_QUEUE.read_bytes() == before_jobs


def test_get_state_and_events_after_query(client: TestClient) -> None:
    client.post(
        "/api/live/query",
        json={
            "campaign_id": "longmont-c2",
            "session": 22,
            "mode": "live",
            "text": "Weather 16.",
        },
    )
    state = client.get("/api/live/state").json()
    assert state["derived"] is True
    assert state["recent_event_count"] >= 1

    events_body = client.get("/api/live/events").json()
    assert len(events_body["events"]) >= 1
    assert events_body["events"][-1]["event_type"] == "roll_result"


def test_context_question_does_not_resolve_roll(client: TestClient) -> None:
    response = client.post(
        "/api/live/query",
        json={
            "campaign_id": "longmont-c2",
            "session": 22,
            "mode": "live",
            "text": "What is Lysandra feeling at the gate?",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["classification"]["latency_mode"] == "context_lookup"
    assert "Hail dent" not in body["answer"]


def test_invalid_campaign_returns_400(client: TestClient) -> None:
    response = client.post(
        "/api/live/query",
        json={
            "campaign_id": "wrong-campaign",
            "session": 22,
            "mode": "live",
            "text": "Weather 7.",
        },
    )
    assert response.status_code == 400


def test_get_jobs_after_canon_correction(client: TestClient) -> None:
    client.post(
        "/api/live/query",
        json={
            "campaign_id": "longmont-c2",
            "session": 22,
            "mode": "live",
            "text": "Lysandro is her father.",
        },
    )
    jobs_body = client.get("/api/live/jobs").json()
    job_types = {row["job_type"] for row in jobs_body["jobs"]}
    assert "post_session_propagation" in job_types
