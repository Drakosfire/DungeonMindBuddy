from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from src.live_play.live_store import append_jsonl, iter_jsonl, load_json, write_json

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "evals/c2_live_prep/live/schemas"
SESSION_DIR = ROOT / "evals/c2_live_prep/live/session_22"


def _load_schema(name: str) -> dict[str, Any]:
    return json.loads((SCHEMA_DIR / name).read_text(encoding="utf-8"))


def _validator(name: str) -> Draft202012Validator:
    schema = _load_schema(name)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def _sample_event() -> dict[str, Any]:
    return {
        "schema_version": "0.1.0",
        "id": "evt-test-weather-7",
        "created_at": "2026-05-25T00:00:00Z",
        "campaign_id": "longmont-c2",
        "session": 22,
        "session_clock": "Day 1 / march beat 1",
        "event_type": "roll_result",
        "latency_mode": "fast_live",
        "input_text": "Weather 7. Caelynn Nature 19.",
        "summary": "Resolved a storm weather roll and queued later benchmark review.",
        "derived_fields": {"table_id": "T-WX", "roll": 7, "skill_check": {"actor": "Caelynn", "skill": "Nature", "total": 19}},
        "provenance": {
            "source_paths": [
                {
                    "path": "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Prep/session_22/travel_storm_weather_d20.md",
                    "role": "roll_table",
                    "notes": "Resolved by row number after the player roll.",
                }
            ],
            "generated_by": "test_live_play_schemas",
            "notes": None,
        },
        "jobs_to_queue": [
            {
                "job_type": "benchmark_candidate",
                "payload": {"source_event_id": "evt-test-weather-7"},
                "reason": "Live prompt belongs in the Session 22 regression set.",
            }
        ],
    }


def _sample_job() -> dict[str, Any]:
    return {
        "schema_version": "0.1.0",
        "id": "job-test-benchmark-candidate",
        "created_at": "2026-05-25T00:00:00Z",
        "job_type": "benchmark_candidate",
        "status": "queued",
        "payload": {"source_event_id": "evt-test-weather-7"},
        "created_from_event_id": "evt-test-weather-7",
        "dependencies": [],
        "provenance": {
            "source_paths": [
                {
                    "path": "evals/c2_live_prep/live/session_22/event_log.jsonl",
                    "role": "source_event_log",
                    "notes": None,
                }
            ],
            "generated_by": "test_live_play_schemas",
            "notes": None,
        },
    }


def test_live_schemas_load_and_seed_json_validates() -> None:
    validators = {
        "live_packet.json": _validator("live_packet.schema.json"),
        "surface_layout.json": _validator("live_surface_layout.schema.json"),
    }
    for filename, validator in validators.items():
        validator.validate(load_json(SESSION_DIR / filename))


def test_seed_jsonl_rows_validate_when_present() -> None:
    event_validator = _validator("live_event.schema.json")
    job_validator = _validator("live_job.schema.json")

    for row in iter_jsonl(SESSION_DIR / "event_log.jsonl"):
        event_validator.validate(row)
    for row in iter_jsonl(SESSION_DIR / "job_queue.jsonl"):
        job_validator.validate(row)
    for row in iter_jsonl(SESSION_DIR / "benchmark_candidates.jsonl"):
        assert isinstance(row, dict)


def test_append_jsonl_writes_valid_event_and_job_rows(tmp_path: Path) -> None:
    event_path = tmp_path / "event_log.jsonl"
    job_path = tmp_path / "job_queue.jsonl"
    event_path.write_text("", encoding="utf-8")
    job_path.write_text("", encoding="utf-8")

    append_jsonl(event_path, _sample_event())
    append_jsonl(job_path, _sample_job())

    event_rows = iter_jsonl(event_path)
    job_rows = iter_jsonl(job_path)
    assert len(event_rows) == 1
    assert len(job_rows) == 1
    _validator("live_event.schema.json").validate(event_rows[0])
    _validator("live_job.schema.json").validate(job_rows[0])


def test_write_json_round_trips_surface_layout(tmp_path: Path) -> None:
    layout = load_json(SESSION_DIR / "surface_layout.json")
    target = tmp_path / "surface_layout.json"
    write_json(target, layout)

    assert load_json(target) == layout
    assert target.read_text(encoding="utf-8").endswith("\n")
    _validator("live_surface_layout.schema.json").validate(load_json(target))


def test_current_state_is_explicitly_derived_not_authoritative() -> None:
    current_state = load_json(SESSION_DIR / "current_state.json")

    assert current_state["derived"] is True
    assert current_state["authoritative"] is False
    assert current_state["derived_from"] == ["live_packet.json", "surface_layout.json", "event_log.jsonl", "job_queue.jsonl"]


def test_surface_catalog_and_layout_seed_required_modules() -> None:
    packet = load_json(SESSION_DIR / "live_packet.json")
    layout = load_json(SESSION_DIR / "surface_layout.json")

    catalog = {module["module_id"]: module for module in packet["surface_catalog"]}
    assert catalog["chat"]["required"] is True
    assert catalog["record"]["required"] is True
    assert {"now", "open_loops", "roll_stack", "sources", "queue"}.issubset(catalog)

    enabled_layout = {module["module_id"]: module for module in layout["modules"] if module["enabled"]}
    assert "chat" in enabled_layout
    assert "record" in enabled_layout
    assert any(module_id not in {"chat", "record"} for module_id in enabled_layout)


def test_schema_rejects_invalid_enum_and_missing_required_field() -> None:
    layout = load_json(SESSION_DIR / "surface_layout.json")
    invalid_slot = copy.deepcopy(layout)
    invalid_slot["modules"][0]["slot"] = "dashboard"
    with pytest.raises(ValidationError):
        _validator("live_surface_layout.schema.json").validate(invalid_slot)

    event = _sample_event()
    del event["provenance"]
    with pytest.raises(ValidationError):
        _validator("live_event.schema.json").validate(event)
