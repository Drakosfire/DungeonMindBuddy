from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from apps.live_control_server.schema_validation import validate_before_append
from src.live_play.live_store import append_jsonl
from src.live_play.projections.commands import ProjectionCommand
from src.live_play.projections.invalidation import ProjectionInvalidation
from src.live_play.projections.targets import ProjectionTarget
from src.live_play.projections.write_results import ProjectionConflict, ProjectionWriteResult

SUPPORTED_TARGET_TYPE = Literal["event", "roll_table"]
MAX_OBSERVATION_LEN = 2000
ALLOWED_PAYLOAD_KEYS = frozenset({"observation", "session_clock", "visibility"})


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _make_write_id() -> str:
    return f"write-{uuid.uuid4().hex[:12]}"


def _make_event_id() -> str:
    return f"evt-observation-{uuid.uuid4().hex[:12]}"


def _conflict_result(
    *,
    command: ProjectionCommand,
    conflict_type: str,
    message: str,
    diagnostics: list[str] | None = None,
) -> ProjectionWriteResult:
    return ProjectionWriteResult(
        write_id=_make_write_id(),
        status="rejected",
        conflicts=[
            ProjectionConflict(
                conflict_type=conflict_type,
                message=message,
                target=command.target,
                recoverable=True,
            )
        ],
        diagnostics=diagnostics or [],
    )


def _canonical_target(
    *,
    command: ProjectionCommand,
    packet: dict[str, Any],
    events: list[dict[str, Any]],
) -> ProjectionTarget | None:
    if command.target.target_type == "event":
        for event in events:
            if event.get("id") != command.target.target_id:
                continue
            summary = str(event.get("summary") or "").strip()
            label = summary or command.target.label
            return ProjectionTarget(
                target_type="event",
                target_id=command.target.target_id,
                label=label,
                source_status="authoritative",
                metadata=command.target.metadata,
            )
        return None
    if command.target.target_type == "roll_table":
        for row in packet.get("known_roll_tables", []):
            if row.get("table_id") != command.target.target_id:
                continue
            title = str(row.get("title") or "").strip() or command.target.label
            return ProjectionTarget(
                target_type="roll_table",
                target_id=command.target.target_id,
                label=title,
                source_status="authoritative",
                metadata=command.target.metadata,
            )
        return None
    return None


def _validate_observation_payload(command: ProjectionCommand) -> tuple[str, str, str] | ProjectionWriteResult:
    unknown = sorted(set(command.payload.keys()) - ALLOWED_PAYLOAD_KEYS)
    if unknown:
        return _conflict_result(
            command=command,
            conflict_type="invalid_payload",
            message=f"unsupported payload fields: {', '.join(unknown)}",
        )
    observation = str(command.payload.get("observation") or "").strip()
    if not observation:
        return _conflict_result(
            command=command,
            conflict_type="invalid_payload",
            message="payload.observation is required",
        )
    if len(observation) > MAX_OBSERVATION_LEN:
        return _conflict_result(
            command=command,
            conflict_type="invalid_payload",
            message=f"payload.observation exceeds max length {MAX_OBSERVATION_LEN}",
        )
    session_clock = str(command.payload.get("session_clock") or "live-control").strip() or "live-control"
    visibility = command.payload.get("visibility")
    if visibility is None:
        visibility = "live_note"
    if visibility != "live_note":
        return _conflict_result(
            command=command,
            conflict_type="invalid_payload",
            message="payload.visibility must be 'live_note' when provided",
        )
    return observation, session_clock, str(visibility)


def _find_existing_idempotent_observation(
    *,
    command: ProjectionCommand,
    events: list[dict[str, Any]],
) -> str | None:
    key = (command.idempotency_key or "").strip()
    if not key:
        return None
    for event in events:
        if event.get("event_type") != "state_note":
            continue
        derived = event.get("derived_fields")
        if not isinstance(derived, dict):
            continue
        if derived.get("command_type") != "append_observation":
            continue
        if derived.get("idempotency_key") != key:
            continue
        event_id = event.get("id")
        if isinstance(event_id, str) and event_id:
            return event_id
    return None


def _build_observation_event(
    *,
    command: ProjectionCommand,
    target: ProjectionTarget,
    packet: dict[str, Any],
    observation: str,
    session_clock: str,
    visibility: str,
) -> dict[str, Any]:
    event_id = _make_event_id()
    summary_text = observation if len(observation) <= 120 else f"{observation[:117]}..."
    return {
        "schema_version": "0.1.0",
        "id": event_id,
        "created_at": _now_utc(),
        "campaign_id": packet["campaign_id"],
        "session": packet["session"],
        "session_clock": session_clock,
        "event_type": "state_note",
        "event_origin": "server",
        "latency_mode": None,
        "input_text": None,
        "summary": (
            f"Observation appended to {target.target_type} {target.target_id}: "
            f"{summary_text}"
        ),
        "derived_fields": {
            "command_type": "append_observation",
            "target": target.model_dump(mode="json"),
            "observation": observation,
            "visibility": visibility,
            "idempotency_key": command.idempotency_key,
            "requested_by": command.requested_by.model_dump(mode="json"),
        },
        "provenance": {
            "source_paths": [
                {
                    "path": "event_log.jsonl",
                    "role": "command_bus",
                    "notes": "Appended via POST /api/live/commands append_observation.",
                }
            ],
            "generated_by": "live_control_server",
            "notes": "First controlled command-bus write path.",
        },
        "jobs_to_queue": [],
    }


def execute_projection_command(
    *,
    command: ProjectionCommand,
    base: Path,
    packet: dict[str, Any],
    events: list[dict[str, Any]],
    jobs: list[dict[str, Any]],
) -> ProjectionWriteResult:
    del jobs  # PR85 command path must not mutate or queue jobs.
    if command.command_type != "append_observation":
        return _conflict_result(
            command=command,
            conflict_type="unsupported_command",
            message=f"unsupported command_type for PR85: {command.command_type}",
        )
    if command.lane != "observed_play":
        return _conflict_result(
            command=command,
            conflict_type="invalid_lane",
            message="append_observation requires lane observed_play",
        )
    if command.target.target_type not in ("event", "roll_table"):
        return _conflict_result(
            command=command,
            conflict_type="unsupported_target",
            message=f"unsupported target type for PR85: {command.target.target_type}",
        )

    target = _canonical_target(command=command, packet=packet, events=events)
    if target is None:
        return _conflict_result(
            command=command,
            conflict_type="unknown_target",
            message=(
                f"unknown target id for {command.target.target_type}: "
                f"{command.target.target_id}"
            ),
        )

    payload_check = _validate_observation_payload(command)
    if isinstance(payload_check, ProjectionWriteResult):
        return payload_check
    observation, session_clock, visibility = payload_check

    existing_id = _find_existing_idempotent_observation(command=command, events=events)
    if existing_id is not None:
        return ProjectionWriteResult(
            write_id=_make_write_id(),
            status="noop",
            events_appended=[existing_id],
            diagnostics=["duplicate idempotency_key; no new event appended"],
        )

    event_row = _build_observation_event(
        command=command,
        target=target,
        packet=packet,
        observation=observation,
        session_clock=session_clock,
        visibility=visibility,
    )
    validate_before_append([event_row], [])

    event_log_path = base / "event_log.jsonl"
    event_log_path.parent.mkdir(parents=True, exist_ok=True)
    if not event_log_path.exists():
        event_log_path.write_text("", encoding="utf-8")
    append_jsonl(event_log_path, event_row)

    invalidations = [
        ProjectionInvalidation(
            projection_key="live.events",
            target=None,
            reason="append_observation appended live event",
        ),
        ProjectionInvalidation(
            projection_key="live.plan_view",
            target=None,
            reason="event log changed",
        ),
        ProjectionInvalidation(
            projection_key="live.artifact",
            target=target,
            reason="observation appended for target",
        ),
        ProjectionInvalidation(
            projection_key="live.capabilities",
            target=target,
            reason="command result may affect target affordances",
        ),
    ]
    return ProjectionWriteResult(
        write_id=_make_write_id(),
        status="accepted",
        events_appended=[str(event_row["id"])],
        jobs_queued=[],
        artifacts_changed=[],
        invalidations=invalidations,
    )
