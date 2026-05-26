from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from apps.live_control_server.schema_validation import validate_before_append
from src.live_play.current_state_derive import derive_current_state_fields
from src.live_play.live_store import append_jsonl, iter_jsonl, load_json, write_json


def _paths(base: Path) -> dict[str, Path]:
    return {
        "packet": base / "live_packet.json",
        "layout": base / "surface_layout.json",
        "events": base / "event_log.jsonl",
        "jobs": base / "job_queue.jsonl",
        "state": base / "current_state.json",
    }


def load_session(base: Path) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    paths = _paths(base)
    packet = load_json(paths["packet"])
    layout = load_json(paths["layout"])
    events = iter_jsonl(paths["events"]) if paths["events"].is_file() else []
    jobs = iter_jsonl(paths["jobs"]) if paths["jobs"].is_file() else []
    return packet, layout, events, jobs


def append_events_and_jobs(
    base: Path,
    events: list[dict[str, Any]],
    jobs: list[dict[str, Any]],
) -> None:
    paths = _paths(base)
    paths["events"].parent.mkdir(parents=True, exist_ok=True)
    paths["jobs"].parent.mkdir(parents=True, exist_ok=True)
    if not paths["events"].is_file():
        paths["events"].write_text("", encoding="utf-8")
    if not paths["jobs"].is_file():
        paths["jobs"].write_text("", encoding="utf-8")
    validate_before_append(events, jobs)
    for event in events:
        append_jsonl(paths["events"], event)
    for job in jobs:
        append_jsonl(paths["jobs"], job)


def refresh_current_state(base: Path) -> dict[str, Any]:
    packet, layout, events, jobs = load_session(base)
    derived = derive_current_state_fields(packet, layout, events, jobs)
    state = {
        "schema_version": "0.1.0",
        "campaign_id": packet["campaign_id"],
        "session": packet["session"],
        "derived": True,
        "authoritative": False,
        "derived_from": [
            "live_packet.json",
            "surface_layout.json",
            "event_log.jsonl",
            "job_queue.jsonl",
        ],
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        **derived,
    }
    write_json(_paths(base)["state"], state)
    return state


def events_since(events: list[dict[str, Any]], since_id: str | None) -> list[dict[str, Any]]:
    """Return events strictly after ``since_id``. Unknown cursor → empty list (no full-log replay)."""
    if not since_id:
        return events
    seen = False
    tail: list[dict[str, Any]] = []
    for event in events:
        if seen:
            tail.append(event)
        elif event.get("id") == since_id:
            seen = True
    return tail
