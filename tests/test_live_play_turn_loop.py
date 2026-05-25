from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from src.live_play.live_turn import handle_live_turn

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "evals/c2_live_prep/live/schemas"
PACKET_PATH = ROOT / "evals/c2_live_prep/live/session_22/live_packet.json"
EVENT_LOG = ROOT / "evals/c2_live_prep/live/session_22/event_log.jsonl"


def _load_schema(name: str) -> dict[str, Any]:
    return json.loads((SCHEMA_DIR / name).read_text(encoding="utf-8"))


def _event_validator() -> Draft202012Validator:
    schema = _load_schema("live_event.schema.json")
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(
        schema,
        format_checker=Draft202012Validator.FORMAT_CHECKER,
    )


def _job_validator() -> Draft202012Validator:
    schema = _load_schema("live_job.schema.json")
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(
        schema,
        format_checker=Draft202012Validator.FORMAT_CHECKER,
    )


def _assert_jobs_valid(jobs: list[dict[str, object]], job_validator: Draft202012Validator) -> None:
    assert jobs, "expected at least one top-level job row"
    for job in jobs:
        job_validator.validate(job)


@pytest.fixture
def packet() -> dict:
    return json.loads(PACKET_PATH.read_text(encoding="utf-8"))


@pytest.fixture
def event_validator() -> Draft202012Validator:
    return _event_validator()


@pytest.fixture
def job_validator() -> Draft202012Validator:
    return _job_validator()


def test_handle_weather_7_with_skill_check(
    packet: dict,
    event_validator: Draft202012Validator,
    job_validator: Draft202012Validator,
) -> None:
    result = handle_live_turn(
        packet,
        "Weather 7. Caelynn Nature 19.",
        root=ROOT,
        created_at="2026-05-25T12:00:00Z",
        event_id_factory=lambda: "evt-test-weather-7",
    )
    assert result.classification.latency_mode == "fast_live"
    assert result.classification.event_type == "roll_result"
    assert "Hail dent" in result.answer
    assert len(result.events_to_write) == 1
    event = result.events_to_write[0]
    event_validator.validate(event)
    assert event["derived_fields"]["skill_check"] == {
        "actor": "Caelynn",
        "skill": "Nature",
        "total": 19,
    }
    assert event["derived_fields"]["table_id"] == "T-WX"
    assert event["derived_fields"]["roll"] == 7
    assert any(s in result.next_suggestions for s in ("T-NPC", "R5", "T-DIL"))
    _assert_jobs_valid(result.jobs_to_queue, job_validator)
    assert result.jobs_to_queue[0]["job_type"] == "benchmark_candidate"


def test_handle_weather_7_without_period(
    packet: dict,
    event_validator: Draft202012Validator,
    job_validator: Draft202012Validator,
) -> None:
    result = handle_live_turn(
        packet,
        "Weather 7",
        root=ROOT,
        created_at="2026-05-25T12:00:00Z",
        event_id_factory=lambda: "evt-test-weather-7-bare",
    )
    assert result.classification.event_type == "roll_result"
    assert "Hail dent" in result.answer
    event_validator.validate(result.events_to_write[0])
    _assert_jobs_valid(result.jobs_to_queue, job_validator)


def test_handle_grobnok_open_loop(packet: dict, event_validator: Draft202012Validator) -> None:
    result = handle_live_turn(
        packet,
        "Grobnok does not call in the morning.",
        root=ROOT,
        created_at="2026-05-25T12:00:00Z",
        event_id_factory=lambda: "evt-test-grobnok",
    )
    assert result.classification.event_type == "open_loop_update"
    assert "evening" in result.answer.lower() and "owed" in result.answer.lower()
    event = result.events_to_write[0]
    event_validator.validate(event)
    assert event["derived_fields"]["status"] == "owed"


def test_handle_lysandro_canon_correction(
    packet: dict,
    event_validator: Draft202012Validator,
    job_validator: Draft202012Validator,
) -> None:
    result = handle_live_turn(
        packet,
        "Lysandro is her father.",
        root=ROOT,
        created_at="2026-05-25T12:00:00Z",
        event_id_factory=lambda: "evt-test-lysandro",
    )
    assert result.classification.event_type == "canon_correction"
    event = result.events_to_write[0]
    event_validator.validate(event)
    assert event["derived_fields"]["correction"] == "Lysandro is her father."
    job_types = {job["job_type"] for job in result.jobs_to_queue}
    assert "post_session_propagation" in job_types
    _assert_jobs_valid(result.jobs_to_queue, job_validator)
    propagation = next(j for j in result.jobs_to_queue if j["job_type"] == "post_session_propagation")
    assert propagation["payload"]["correction"] == "Lysandro is her father."
    assert any(
        job["job_type"] == "post_session_propagation"
        for job in event["jobs_to_queue"]
    )


def test_handle_caelynn_canon_commit(
    packet: dict,
    event_validator: Draft202012Validator,
    job_validator: Draft202012Validator,
) -> None:
    result = handle_live_turn(
        packet,
        "Caelynn bottles the puddle water.",
        root=ROOT,
        created_at="2026-05-25T12:00:00Z",
        event_id_factory=lambda: "evt-test-caelynn-commit",
    )
    assert result.classification.event_type == "canon_commit"
    event_validator.validate(result.events_to_write[0])
    job_types = {job["job_type"] for job in result.jobs_to_queue}
    assert "append_staging" in job_types
    assert "benchmark_candidate" in job_types
    _assert_jobs_valid(result.jobs_to_queue, job_validator)


def test_handle_context_question_no_roll(packet: dict, event_validator: Draft202012Validator) -> None:
    result = handle_live_turn(
        packet,
        "What is Lysandra feeling at the gate?",
        root=ROOT,
        created_at="2026-05-25T12:00:00Z",
        event_id_factory=lambda: "evt-test-context",
    )
    assert result.classification.latency_mode == "context_lookup"
    assert result.classification.event_type == "context_question"
    assert "Hail dent" not in result.answer
    assert "context lookup" in result.answer.lower()
    assert "context_lookup_not_executed_in_L2" in result.diagnostics
    event_validator.validate(result.events_to_write[0])


def test_handle_live_turn_does_not_mutate_seed_jsonl(packet: dict) -> None:
    before = EVENT_LOG.read_bytes()
    handle_live_turn(packet, "Weather 16.", root=ROOT, created_at="2026-05-25T12:00:00Z")
    assert EVENT_LOG.read_bytes() == before
