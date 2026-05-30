from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator

from apps.live_control_server.config import SESSION_DIR_ENV
from apps.live_control_server.main import create_app
from apps.live_control_server.session_store import load_session
from src.live_play.projections import build_session_plan_projection

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "evals/c2_live_prep/live/schemas/plan_view.schema.json"
SAMPLE_PATH = ROOT / "evals/c2_live_prep/live/session_22/plan_view.sample.json"
SEED_SESSION = ROOT / "evals/c2_live_prep/live/session_22"
ALLOWED_TARGET_TYPES = {
    "event",
    "roll_table",
    "npc",
    "location",
    "runbook_section",
    "job",
    "open_loop",
    "source_packet",
}


def _validator() -> Draft202012Validator:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    return Draft202012Validator(schema, format_checker=Draft202012Validator.FORMAT_CHECKER)


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


def test_builder_returns_non_authoritative_payload() -> None:
    packet, _, events, jobs = load_session(SEED_SESSION)
    projection = build_session_plan_projection(
        packet,
        events,
        jobs,
        generated_at="2026-05-28T00:00:00Z",
    )
    assert projection["authoritative"] is False
    assert projection["campaign_id"] == packet["campaign_id"]
    assert projection["session"] == packet["session"]
    assert projection["timeline"]
    _validator().validate(projection)


def test_builder_rows_have_human_labels_and_typed_refs() -> None:
    packet, _, events, jobs = load_session(SEED_SESSION)
    projection = build_session_plan_projection(packet, events, jobs, generated_at="2026-05-28T00:00:00Z")
    for row in projection["timeline"]:
        assert isinstance(row["label"], str) and row["label"].strip()
        assert isinstance(row["summary"], str) and row["summary"].strip()
        for ref in row["refs"]:
            assert ref["target_type"] in ALLOWED_TARGET_TYPES
            assert isinstance(ref["target_id"], str) and ref["target_id"].strip()
            assert isinstance(ref["label"], str) and ref["label"].strip()


def test_sample_fixture_validates_against_schema() -> None:
    sample = json.loads(SAMPLE_PATH.read_text(encoding="utf-8"))
    _validator().validate(sample)
    assert sample["authoritative"] is False
    assert 5 <= len(sample["timeline"]) <= 8


def test_get_plan_view_endpoint_returns_valid_payload(client: TestClient) -> None:
    response = client.get("/api/live/plan-view")
    assert response.status_code == 200
    body = response.json()
    _validator().validate(body)
    assert body["authoritative"] is False
    assert body["timeline"]


def test_builder_uses_planning_beats_when_present(tmp_path: Path) -> None:
    import shutil

    from src.live_play.session_bootstrap import bootstrap_session_workspace
    from src.live_play.session_paths import live_sessions_root

    fixture = ROOT / "tests/fixtures/live_bootstrap/session_22_fresh_recap.md"
    out = live_sessions_root() / "_pytest" / tmp_path.name / "session_23"
    if out.exists():
        shutil.rmtree(out)
    bootstrap_session_workspace(
        recap_path=fixture,
        campaign_id="longmont-c2",
        session=23,
        output_dir=out,
        source_session=22,
    )
    try:
        packet, _, events, jobs = load_session(out)
        projection = build_session_plan_projection(packet, events, jobs, generated_at="2026-05-29T00:00:00Z")
        assert len(projection["timeline"]) >= 2
        assert projection["timeline"][0]["id"].startswith("beat-")
    finally:
        if out.exists():
            shutil.rmtree(out, ignore_errors=True)


def test_get_plan_view_endpoint_is_read_only(client: TestClient, isolated_session: Path) -> None:
    events_before = (isolated_session / "event_log.jsonl").read_text(encoding="utf-8")
    jobs_before = (isolated_session / "job_queue.jsonl").read_text(encoding="utf-8")

    response = client.get("/api/live/plan-view")
    assert response.status_code == 200

    events_after = (isolated_session / "event_log.jsonl").read_text(encoding="utf-8")
    jobs_after = (isolated_session / "job_queue.jsonl").read_text(encoding="utf-8")
    assert events_after == events_before
    assert jobs_after == jobs_before
