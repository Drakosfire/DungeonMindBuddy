"""Offline tests for the Stage A session-events run report writer.

All tests are purely offline — no network calls, no model invocations.

Pinning behaviour:
- the per-run sidecar JSON includes the model's parsed_events array verbatim
  (added 2026-04-22 to unblock downstream consumers like Stage C/D from
  hand-frozen fixture files; tracked via Backlog "Stage C — propagate
  Stage A referenced_slugs[] enrichment back into the cohort sidecar artifacts")
- the schema version reflects the v2 shape
- empty/missing parsed_events serializes as []
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import pytest

from evals.session_events_extraction_vertical_slice.session_events_run_report import (
    REPORT_SCHEMA_VERSION,
    write_session_events_run_report,
)


def _baseline_kwargs(tmp_path: Path) -> dict:
    return {
        "scenario_id": "session_events_session_test",
        "model_id": "gpt-test",
        "gates_passed": True,
        "per_gate_verdict": {"SE1": "PASS", "SE2": "PASS", "SE3": "PASS", "SE4": "PASS", "SE5": "PASS"},
        "violations": {"SE1": [], "SE2": [], "SE3": [], "SE4": [], "SE5": []},
        "grader_telemetry": {"event_count": 2, "participants_seen": ["caelynn"]},
        "cost_usd": 0.0123,
        "usage": {"input_tokens": 100, "output_tokens": 50, "cached_tokens": 0},
        "scenario": {"grading": {"min_event_count": 1}},
        "runs_root": tmp_path,
    }


def test_sidecar_persists_parsed_events(tmp_path: Path) -> None:
    parsed_events = [
        {
            "event_name": "Recover debris from the broken riverside structure",
            "event_class": "discovery",
            "participants": ["bonogo", "stafl", "baergrom"],
            "referenced_slugs": ["kirfan"],
            "outcomes": ["The party drags planks free from the river current."],
            "time_scope": "scene",
            "certainty": "observed",
        },
        {
            "event_name": "Stafl rallies the town defenses",
            "event_class": "social_conflict",
            "participants": ["stafl"],
            "referenced_slugs": [],
            "outcomes": ["Stafl organizes flood-defense crews along the bank."],
            "time_scope": "scene",
            "certainty": "observed",
        },
    ]

    paths, _summary = write_session_events_run_report(
        parsed_events=parsed_events,
        **_baseline_kwargs(tmp_path),
    )

    sidecar = json.loads(paths.sidecar_json.read_text(encoding="utf-8"))

    assert sidecar["schema"] == REPORT_SCHEMA_VERSION
    assert "parsed_events" in sidecar, (
        "Stage A sidecar must persist parsed_events so downstream consumers "
        "(Stage C/D) can read events without hand-frozen fixture files."
    )
    assert sidecar["parsed_events"] == parsed_events
    # referenced_slugs[] preservation is a cross-stage contract — check explicitly
    assert sidecar["parsed_events"][0]["referenced_slugs"] == ["kirfan"]


def test_sidecar_handles_empty_parsed_events(tmp_path: Path) -> None:
    paths, _ = write_session_events_run_report(
        parsed_events=[],
        **_baseline_kwargs(tmp_path),
    )
    sidecar = json.loads(paths.sidecar_json.read_text(encoding="utf-8"))
    assert sidecar["parsed_events"] == []


def test_parsed_events_are_copied_not_referenced(tmp_path: Path) -> None:
    parsed_events = [{"event_name": "foo", "participants": []}]
    paths, _ = write_session_events_run_report(
        parsed_events=parsed_events,
        **_baseline_kwargs(tmp_path),
    )
    sidecar = json.loads(paths.sidecar_json.read_text(encoding="utf-8"))
    parsed_events[0]["event_name"] = "MUTATED"
    assert sidecar["parsed_events"][0]["event_name"] == "foo", (
        "report writer must defensively copy parsed_events so post-write mutation "
        "of the runner's local list cannot corrupt the persisted sidecar"
    )


def test_legacy_sidecar_also_persists_parsed_events(tmp_path: Path) -> None:
    parsed_events = [{"event_name": "single_event", "participants": ["caelynn"]}]
    paths, _ = write_session_events_run_report(
        parsed_events=parsed_events,
        **_baseline_kwargs(tmp_path),
    )
    legacy = json.loads(paths.legacy_json.read_text(encoding="utf-8"))
    assert legacy["parsed_events"] == parsed_events
