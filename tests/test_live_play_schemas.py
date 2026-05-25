from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from src.live_play.current_state_derive import derive_current_state_fields
from src.live_play.live_store import append_jsonl, iter_jsonl, load_json, write_json
from src.live_play.surface_layout_invariants import (
    validate_catalog_layout_consistency,
    validate_surface_layout_invariants,
)

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "evals/c2_live_prep/live/schemas"
SESSION_DIR = ROOT / "evals/c2_live_prep/live/session_22"


def _load_schema(name: str) -> dict[str, Any]:
    return json.loads((SCHEMA_DIR / name).read_text(encoding="utf-8"))


def _validator(name: str) -> Draft202012Validator:
    schema = _load_schema(name)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(
        schema,
        format_checker=Draft202012Validator.FORMAT_CHECKER,
    )


def _validate_surface_layout(layout: dict[str, Any]) -> None:
    _validator("live_surface_layout.schema.json").validate(layout)
    validate_surface_layout_invariants(layout)


def _sample_event() -> dict[str, Any]:
    return {
        "schema_version": "0.1.0",
        "id": "evt-test-weather-7",
        "created_at": "2026-05-25T00:00:00Z",
        "campaign_id": "longmont-c2",
        "session": 22,
        "session_clock": "Day 1 / march beat 1",
        "event_type": "roll_result",
        "event_origin": "user_input",
        "latency_mode": "fast_live",
        "input_text": "Weather 7. Caelynn Nature 19.",
        "summary": "Resolved a storm weather roll and queued later benchmark review.",
        "derived_fields": {
            "table_id": "T-WX",
            "roll": 7,
            "skill_check": {"actor": "Caelynn", "skill": "Nature", "total": 19},
        },
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


def _sample_system_surface_event() -> dict[str, Any]:
    return {
        "schema_version": "0.1.0",
        "id": "evt-test-surface-layout",
        "created_at": "2026-05-25T00:00:00Z",
        "campaign_id": "longmont-c2",
        "session": 22,
        "session_clock": "n/a",
        "event_type": "surface_config_updated",
        "event_origin": "server",
        "latency_mode": None,
        "input_text": None,
        "summary": "GM enabled the open_loops module in the live surface layout.",
        "derived_fields": {"layout_version": 2},
        "provenance": {
            "source_paths": [
                {
                    "path": "evals/c2_live_prep/live/session_22/surface_layout.json",
                    "role": "surface_layout",
                    "notes": None,
                }
            ],
            "generated_by": "test_live_play_schemas",
            "notes": None,
        },
        "jobs_to_queue": [],
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


def _packet_paths(packet: dict[str, Any]) -> list[str]:
    paths: list[str] = []
    for row in packet["source_paths"]:
        paths.append(row["path"])
    for table in packet["known_roll_tables"]:
        paths.append(table["source_path"])
    for loop in packet["open_loops"]:
        for row in loop.get("source_paths", []):
            paths.append(row["path"])
    for row in packet["roll_stack"]:
        paths.append(row["source_path"])
    return paths


def test_live_schemas_load_and_seed_json_validates() -> None:
    packet = load_json(SESSION_DIR / "live_packet.json")
    layout = load_json(SESSION_DIR / "surface_layout.json")
    _validator("live_packet.schema.json").validate(packet)
    _validate_surface_layout(layout)


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


def test_system_surface_config_event_validates_without_user_input_fields() -> None:
    _validator("live_event.schema.json").validate(_sample_system_surface_event())


def test_write_json_round_trips_surface_layout_atomically(tmp_path: Path) -> None:
    layout = load_json(SESSION_DIR / "surface_layout.json")
    target = tmp_path / "surface_layout.json"
    write_json(target, layout)

    assert load_json(target) == layout
    assert target.read_text(encoding="utf-8").endswith("\n")
    _validate_surface_layout(load_json(target))


def test_current_state_derived_fields_match_authoritative_sources() -> None:
    packet = load_json(SESSION_DIR / "live_packet.json")
    layout = load_json(SESSION_DIR / "surface_layout.json")
    events = iter_jsonl(SESSION_DIR / "event_log.jsonl")
    jobs = iter_jsonl(SESSION_DIR / "job_queue.jsonl")
    state = load_json(SESSION_DIR / "current_state.json")

    assert state["derived"] is True
    assert state["authoritative"] is False
    assert state["derived_from"] == [
        "live_packet.json",
        "surface_layout.json",
        "event_log.jsonl",
        "job_queue.jsonl",
    ]

    derived = derive_current_state_fields(packet, layout, events, jobs)
    assert state["now"] == derived["now"]
    assert state["now"] == packet["current_state_seed"]
    assert state["open_loop_count"] == derived["open_loop_count"]
    assert state["pending_roll_tables"] == derived["pending_roll_tables"]
    assert state["enabled_surface_modules"] == derived["enabled_surface_modules"]
    assert state["queued_job_count"] == derived["queued_job_count"]
    assert state["recent_event_count"] == derived["recent_event_count"]


def test_surface_catalog_and_layout_seed_required_modules() -> None:
    packet = load_json(SESSION_DIR / "live_packet.json")
    layout = load_json(SESSION_DIR / "surface_layout.json")

    catalog = {module["module_id"]: module for module in packet["surface_catalog"]}
    assert catalog["chat"]["required"] is True
    assert catalog["record"]["required"] is True
    assert {"now", "open_loops", "roll_stack", "sources", "queue"}.issubset(catalog)

    catalog_ids = [row["module_id"] for row in packet["surface_catalog"]]
    layout_ids = [row["module_id"] for row in layout["modules"]]
    assert len(catalog_ids) == len(set(catalog_ids))
    assert set(layout_ids).issubset(set(catalog_ids))
    validate_catalog_layout_consistency(packet, layout)

    enabled_layout = {module["module_id"]: module for module in layout["modules"] if module["enabled"]}
    assert "chat" in enabled_layout
    assert "record" in enabled_layout
    assert any(module_id not in {"chat", "record"} for module_id in enabled_layout)
    _validate_surface_layout(layout)


def test_layout_rejects_module_not_in_surface_catalog() -> None:
    packet = load_json(SESSION_DIR / "live_packet.json")
    layout = load_json(SESSION_DIR / "surface_layout.json")
    orphan = copy.deepcopy(layout)
    orphan["modules"].append(
        {
            "module_id": "not_in_catalog",
            "slot": "sidebar",
            "order": 99,
            "enabled": True,
            "collapsed": False,
        }
    )
    with pytest.raises(ValueError, match="not in surface_catalog"):
        validate_catalog_layout_consistency(packet, orphan)


def test_surface_layout_rejects_missing_chat() -> None:
    layout = load_json(SESSION_DIR / "surface_layout.json")
    without_chat = copy.deepcopy(layout)
    without_chat["modules"] = [row for row in without_chat["modules"] if row["module_id"] != "chat"]
    with pytest.raises(ValidationError):
        _validator("live_surface_layout.schema.json").validate(without_chat)


def test_surface_layout_rejects_missing_record() -> None:
    layout = load_json(SESSION_DIR / "surface_layout.json")
    without_record = copy.deepcopy(layout)
    without_record["modules"] = [row for row in without_record["modules"] if row["module_id"] != "record"]
    with pytest.raises(ValidationError):
        _validator("live_surface_layout.schema.json").validate(without_record)


def test_surface_layout_rejects_disabled_chat() -> None:
    layout = load_json(SESSION_DIR / "surface_layout.json")
    disabled_chat = copy.deepcopy(layout)
    for row in disabled_chat["modules"]:
        if row["module_id"] == "chat":
            row["enabled"] = False
    with pytest.raises(ValidationError):
        _validator("live_surface_layout.schema.json").validate(disabled_chat)


def test_surface_layout_rejects_disabled_record() -> None:
    layout = load_json(SESSION_DIR / "surface_layout.json")
    disabled_record = copy.deepcopy(layout)
    for row in disabled_record["modules"]:
        if row["module_id"] == "record":
            row["enabled"] = False
    with pytest.raises(ValidationError):
        _validator("live_surface_layout.schema.json").validate(disabled_record)


def test_surface_layout_rejects_duplicate_module_ids() -> None:
    layout = load_json(SESSION_DIR / "surface_layout.json")
    duplicate = copy.deepcopy(layout)
    duplicate["modules"].append(copy.deepcopy(duplicate["modules"][0]))
    _validator("live_surface_layout.schema.json").validate(duplicate)
    with pytest.raises(ValueError, match="duplicate module_id"):
        validate_surface_layout_invariants(duplicate)


def test_schema_rejects_invalid_timestamp() -> None:
    event = _sample_event()
    event["created_at"] = "not-a-date-time"
    with pytest.raises(ValidationError):
        _validator("live_event.schema.json").validate(event)


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


def test_live_packet_source_paths_exist_on_disk() -> None:
    packet = load_json(SESSION_DIR / "live_packet.json")
    for rel_path in _packet_paths(packet):
        assert (ROOT / rel_path).is_file(), rel_path


def test_load_json_rejects_non_object(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text("[1, 2, 3]\n", encoding="utf-8")
    with pytest.raises(TypeError, match="expected JSON object"):
        load_json(path)


def test_iter_jsonl_rejects_non_object_row(tmp_path: Path) -> None:
    path = tmp_path / "bad.jsonl"
    path.write_text('{"ok": true}\n"not-an-object"\n', encoding="utf-8")
    with pytest.raises(TypeError, match="expected JSON object"):
        iter_jsonl(path)


def test_iter_jsonl_rejects_invalid_json_line(tmp_path: Path) -> None:
    path = tmp_path / "bad.jsonl"
    path.write_text('{"ok": true}\n{not json}\n', encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        iter_jsonl(path)
