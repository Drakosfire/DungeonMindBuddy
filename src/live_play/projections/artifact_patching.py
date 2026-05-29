from __future__ import annotations

import difflib
import os
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from apps.live_control_server.schema_validation import validate_before_append
from src.live_play.live_store import append_jsonl
from src.live_play.projections.artifacts import file_state_token_for_text
from src.live_play.projections.commands import ProjectionCommand
from src.live_play.projections.invalidation import ProjectionInvalidation
from src.live_play.projections.targets import ProjectionTarget
from src.live_play.projections.write_results import (
    ProjectionConflict,
    ProjectionWriteResult,
    ProjectionWriteStatus,
)
from src.live_play.roll_table_registry import RollTableRef, parse_roll_table_text

ALLOWED_PATCH_PAYLOAD_KEYS = frozenset(
    {"expected_file_state_token", "old_text", "new_text", "rationale", "dry_run"}
)
FORBIDDEN_PATCH_PAYLOAD_KEYS = frozenset(
    {"source_path", "file_path", "path", "absolute_path", "relative_path", "artifact_path", "repo_path"}
)
MAX_PATCH_TEXT_LENGTH = 20_000
MAX_PATCHED_ARTIFACT_LENGTH = 200_000
MAX_DIFF_LENGTH = 12_000


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _make_write_id() -> str:
    return f"write-{uuid.uuid4().hex[:12]}"


def _make_patch_event_id() -> str:
    return f"evt-patch-{uuid.uuid4().hex[:12]}"


def _result(
    *,
    status: ProjectionWriteStatus,
    command: ProjectionCommand,
    conflicts: list[ProjectionConflict] | None = None,
    diagnostics: list[str] | None = None,
    events_appended: list[str] | None = None,
    artifacts_changed: list[ProjectionTarget] | None = None,
    invalidations: list[ProjectionInvalidation] | None = None,
    metadata: dict[str, Any] | None = None,
) -> ProjectionWriteResult:
    return ProjectionWriteResult(
        write_id=_make_write_id(),
        status=status,
        events_appended=events_appended or [],
        artifacts_changed=artifacts_changed or [],
        invalidations=invalidations or [],
        conflicts=conflicts or [],
        diagnostics=diagnostics or [],
        metadata=metadata or {},
    )


def _rejected(
    *,
    command: ProjectionCommand,
    conflict_type: str,
    message: str,
    diagnostics: list[str] | None = None,
) -> ProjectionWriteResult:
    return _result(
        status="rejected",
        command=command,
        conflicts=[
            ProjectionConflict(
                conflict_type=conflict_type,
                message=message,
                target=command.target,
                recoverable=True,
            )
        ],
        diagnostics=diagnostics,
    )


def _conflict(
    *,
    command: ProjectionCommand,
    conflict_type: str,
    message: str,
    diagnostics: list[str] | None = None,
) -> ProjectionWriteResult:
    return _result(
        status="conflict",
        command=command,
        conflicts=[
            ProjectionConflict(
                conflict_type=conflict_type,
                message=message,
                target=command.target,
                recoverable=True,
            )
        ],
        diagnostics=diagnostics,
    )


def _find_existing_patch_idempotency_event(
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
        derived_fields = event.get("derived_fields")
        if not isinstance(derived_fields, dict):
            continue
        if derived_fields.get("command_type") != "patch_artifact":
            continue
        if derived_fields.get("idempotency_key") != key:
            continue
        event_id = event.get("id")
        if isinstance(event_id, str) and event_id:
            return event_id
    return None


def _validate_patch_payload(command: ProjectionCommand) -> tuple[str, str, str, str | None, bool] | ProjectionWriteResult:
    payload = command.payload
    forbidden = sorted(set(payload.keys()) & FORBIDDEN_PATCH_PAYLOAD_KEYS)
    if forbidden:
        return _rejected(
            command=command,
            conflict_type="invalid_payload",
            message=f"forbidden payload fields: {', '.join(forbidden)}",
        )
    unknown = sorted(set(payload.keys()) - ALLOWED_PATCH_PAYLOAD_KEYS)
    if unknown:
        return _rejected(
            command=command,
            conflict_type="invalid_payload",
            message=f"unsupported payload fields: {', '.join(unknown)}",
        )
    expected_token = payload.get("expected_file_state_token")
    old_text = payload.get("old_text")
    new_text = payload.get("new_text")
    rationale = payload.get("rationale")
    dry_run = payload.get("dry_run", False)

    if not isinstance(expected_token, str) or not expected_token.strip():
        return _rejected(
            command=command,
            conflict_type="invalid_payload",
            message="payload.expected_file_state_token is required",
        )
    if not isinstance(old_text, str) or not old_text:
        return _rejected(
            command=command,
            conflict_type="invalid_payload",
            message="payload.old_text is required",
        )
    if not isinstance(new_text, str) or not new_text:
        return _rejected(
            command=command,
            conflict_type="invalid_payload",
            message="payload.new_text is required",
        )
    if old_text == new_text:
        return _rejected(
            command=command,
            conflict_type="invalid_payload",
            message="payload.old_text and payload.new_text must differ",
        )
    if len(old_text) > MAX_PATCH_TEXT_LENGTH or len(new_text) > MAX_PATCH_TEXT_LENGTH:
        return _rejected(
            command=command,
            conflict_type="invalid_payload",
            message=f"payload.old_text/new_text must be <= {MAX_PATCH_TEXT_LENGTH} characters",
        )
    normalized_rationale: str | None = None
    if rationale is not None:
        if not isinstance(rationale, str) or not rationale.strip():
            return _rejected(
                command=command,
                conflict_type="invalid_payload",
                message="payload.rationale must be a non-empty string when provided",
            )
        normalized_rationale = rationale.strip()
    if not isinstance(dry_run, bool):
        return _rejected(
            command=command,
            conflict_type="invalid_payload",
            message="payload.dry_run must be boolean when provided",
        )
    return expected_token.strip(), old_text, new_text, normalized_rationale, dry_run


def _resolve_roll_table_patch_target(
    *,
    command: ProjectionCommand,
    packet: dict[str, Any],
    root: Path,
) -> tuple[ProjectionTarget, RollTableRef, Path] | ProjectionWriteResult:
    if command.target.target_type != "roll_table":
        return _rejected(
            command=command,
            conflict_type="unsupported_target",
            message=f"patch_artifact supports only roll_table targets, got {command.target.target_type}",
        )
    roll_table_row: dict[str, Any] | None = None
    for row in packet.get("known_roll_tables", []):
        if row.get("table_id") == command.target.target_id:
            roll_table_row = row
            break
    if roll_table_row is None:
        return _rejected(
            command=command,
            conflict_type="unknown_target",
            message=f"unknown target id for roll_table: {command.target.target_id}",
        )
    source_path = str(roll_table_row.get("source_path") or "").strip()
    if not source_path:
        return _rejected(
            command=command,
            conflict_type="invalid_source_path",
            message="roll_table source_path missing from live packet",
        )
    root_resolved = root.resolve()
    resolved_source = (root / source_path).resolve()
    if not resolved_source.is_relative_to(root_resolved):
        return _rejected(
            command=command,
            conflict_type="invalid_source_path",
            message=f"roll_table source_path escapes repo root: {source_path}",
        )
    if not resolved_source.is_file():
        return _rejected(
            command=command,
            conflict_type="invalid_source_path",
            message=f"roll_table source_path is not a readable file: {source_path}",
        )
    ref = RollTableRef(
        table_id=str(roll_table_row["table_id"]),
        title=str(roll_table_row["title"]),
        dice=str(roll_table_row["dice"]),
        source_path=source_path,
        status=str(roll_table_row.get("status", "pending")),
        default_latency_mode=(
            str(roll_table_row["default_latency_mode"])
            if roll_table_row.get("default_latency_mode") is not None
            else None
        ),
    )
    canonical_target = ProjectionTarget(
        target_type="roll_table",
        target_id=ref.table_id,
        label=ref.title,
        source_status="authoritative",
        metadata=command.target.metadata,
    )
    return canonical_target, ref, resolved_source


def _write_text_atomic(path: Path, text: str) -> None:
    fd, tmp_path_str = tempfile.mkstemp(prefix=f".patch-{path.name}-", dir=str(path.parent))
    tmp_path = Path(tmp_path_str)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        tmp_path.replace(path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def _build_patch_metadata(
    *,
    source_path: str,
    file_state_token_before: str,
    file_state_token_after: str,
    old_text: str,
    new_text: str,
    replacement_count: int,
    dry_run: bool,
    unified_diff: str,
) -> dict[str, Any]:
    return {
        "patch": {
            "dry_run": dry_run,
            "source_path": source_path,
            "file_state_token_before": file_state_token_before,
            "file_state_token_after": file_state_token_after,
            "old_text_length": len(old_text),
            "new_text_length": len(new_text),
            "replacement_count": replacement_count,
            "unified_diff": unified_diff[:MAX_DIFF_LENGTH],
        }
    }


def _build_patch_audit_event(
    *,
    command: ProjectionCommand,
    target: ProjectionTarget,
    packet: dict[str, Any],
    source_path: str,
    file_state_token_before: str,
    file_state_token_after: str,
    old_text: str,
    new_text: str,
    rationale: str | None,
) -> dict[str, Any]:
    return {
        "schema_version": "0.1.0",
        "id": _make_patch_event_id(),
        "created_at": _now_utc(),
        "campaign_id": packet["campaign_id"],
        "session": packet["session"],
        "session_clock": "live-control",
        "event_type": "state_note",
        "event_origin": "server",
        "latency_mode": None,
        "input_text": None,
        "summary": f"Patched roll_table {target.target_id}: {target.label}",
        "derived_fields": {
            "command_type": "patch_artifact",
            "target": target.model_dump(mode="json"),
            "rationale": rationale,
            "source_path": source_path,
            "file_state_token_before": file_state_token_before,
            "file_state_token_after": file_state_token_after,
            "old_text_length": len(old_text),
            "new_text_length": len(new_text),
            "idempotency_key": command.idempotency_key,
        },
        "provenance": {
            "source_paths": [
                {
                    "path": "event_log.jsonl",
                    "role": "command_bus",
                    "notes": "Appended via POST /api/live/commands patch_artifact.",
                }
            ],
            "generated_by": "live_control_server",
            "notes": "Scoped roll-table patch audit event.",
        },
        "jobs_to_queue": [],
    }


def execute_patch_artifact_command(
    *,
    command: ProjectionCommand,
    base: Path,
    root: Path,
    packet: dict[str, Any],
    events: list[dict[str, Any]],
) -> ProjectionWriteResult:
    if command.lane != "prep_note":
        return _rejected(
            command=command,
            conflict_type="invalid_lane",
            message="patch_artifact requires lane prep_note",
        )

    payload_result = _validate_patch_payload(command)
    if isinstance(payload_result, ProjectionWriteResult):
        return payload_result
    expected_token, old_text, new_text, rationale, dry_run = payload_result

    resolved = _resolve_roll_table_patch_target(command=command, packet=packet, root=root)
    if isinstance(resolved, ProjectionWriteResult):
        return resolved
    target, ref, source_file = resolved

    existing_id = _find_existing_patch_idempotency_event(command=command, events=events)
    if existing_id is not None:
        return _result(
            status="noop",
            command=command,
            events_appended=[existing_id],
            diagnostics=["duplicate idempotency_key; no new patch applied"],
        )

    current_text = source_file.read_text(encoding="utf-8")
    token_before = file_state_token_for_text(Path(ref.source_path), current_text)
    if token_before != expected_token:
        return _conflict(
            command=command,
            conflict_type="stale_artifact",
            message="artifact changed since it was read; refresh before patching",
            diagnostics=["expected_file_state_token does not match current file state"],
        )

    replacement_count = current_text.count(old_text)
    if replacement_count == 0:
        return _rejected(
            command=command,
            conflict_type="invalid_artifact_patch",
            message="payload.old_text was not found in current artifact",
        )
    if replacement_count > 1:
        return _rejected(
            command=command,
            conflict_type="invalid_artifact_patch",
            message="payload.old_text must match exactly once in current artifact",
        )

    patched_text = current_text.replace(old_text, new_text, 1)
    if len(patched_text) > MAX_PATCHED_ARTIFACT_LENGTH:
        return _rejected(
            command=command,
            conflict_type="invalid_artifact_patch",
            message=f"patched artifact exceeds max size {MAX_PATCHED_ARTIFACT_LENGTH}",
        )
    try:
        parse_roll_table_text(ref, patched_text)
    except ValueError:
        return _rejected(
            command=command,
            conflict_type="invalid_artifact_patch",
            message="patched roll table failed parse validation",
        )

    token_after = file_state_token_for_text(Path(ref.source_path), patched_text)
    unified_diff = "".join(
        difflib.unified_diff(
            current_text.splitlines(keepends=True),
            patched_text.splitlines(keepends=True),
            fromfile=f"a/{ref.source_path}",
            tofile=f"b/{ref.source_path}",
            n=3,
        )
    )
    metadata = _build_patch_metadata(
        source_path=ref.source_path,
        file_state_token_before=token_before,
        file_state_token_after=token_after,
        old_text=old_text,
        new_text=new_text,
        replacement_count=replacement_count,
        dry_run=dry_run,
        unified_diff=unified_diff,
    )

    if dry_run:
        return _result(
            status="noop",
            command=command,
            diagnostics=["dry_run preview only; no file write or event append"],
            metadata=metadata,
        )

    _write_text_atomic(source_file, patched_text)

    event_row = _build_patch_audit_event(
        command=command,
        target=target,
        packet=packet,
        source_path=ref.source_path,
        file_state_token_before=token_before,
        file_state_token_after=token_after,
        old_text=old_text,
        new_text=new_text,
        rationale=rationale,
    )
    validate_before_append([event_row], [])
    event_log_path = base / "event_log.jsonl"
    event_log_path.parent.mkdir(parents=True, exist_ok=True)
    if not event_log_path.exists():
        event_log_path.write_text("", encoding="utf-8")
    append_jsonl(event_log_path, event_row)

    invalidations = [
        ProjectionInvalidation(
            projection_key="live.artifact",
            target=target,
            reason="roll table markdown patched",
        ),
        ProjectionInvalidation(
            projection_key="live.capabilities",
            target=target,
            reason="artifact patch changed target state",
        ),
        ProjectionInvalidation(
            projection_key="live.plan_view",
            target=None,
            reason="roll table patch may affect projected timeline language",
        ),
        ProjectionInvalidation(
            projection_key="live.events",
            target=None,
            reason="patch audit event appended",
        ),
    ]
    return _result(
        status="accepted",
        command=command,
        events_appended=[str(event_row["id"])],
        artifacts_changed=[target],
        invalidations=invalidations,
        metadata=metadata,
    )
