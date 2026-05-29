from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from src.live_play.projections.targets import ProjectionTarget
from src.live_play.roll_table_registry import RollTableRef, load_parsed_table

ArtifactContentType = Literal["application/json", "text/markdown"]
ArtifactKind = Literal["event", "roll_table"]
ArtifactTargetType = Literal["event", "roll_table"]


class ArtifactReadError(Exception):
    def __init__(self, message: str, *, status_code: int) -> None:
        super().__init__(message)
        self.status_code = status_code


class UnknownArtifactTarget(ArtifactReadError):
    def __init__(self, target_type: ArtifactTargetType, target_id: str) -> None:
        super().__init__(
            f"unknown target id for {target_type}: {target_id}",
            status_code=404,
        )


class ArtifactSourceMissing(ArtifactReadError):
    def __init__(self, source_path: str) -> None:
        super().__init__(f"artifact source missing: {source_path}", status_code=500)


class ArtifactReadProvenance(BaseModel):
    source_path: str | None = None
    source_role: str | None = None
    generated_by: str = "live_control_server"
    notes: str | None = None


class ArtifactReadPayload(BaseModel):
    content_type: ArtifactContentType
    data: dict[str, Any] | None = None
    text: str | None = None


class ArtifactReadResponse(BaseModel):
    schema_version: str = "0.1.0"
    target: ProjectionTarget
    artifact_kind: ArtifactKind
    title: str
    read_only: bool = True
    file_state_token: str | None = None
    payload: ArtifactReadPayload
    provenance: ArtifactReadProvenance
    metadata: dict[str, Any] = Field(default_factory=dict)


def _sha256_hex(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _event_token(event_row: dict[str, Any]) -> str:
    canonical = json.dumps(event_row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return _sha256_hex(canonical.encode("utf-8"))


def file_state_token_for_text(path: Path, text: str) -> str:
    payload = f"{path.as_posix()}:{len(text)}:{_sha256_hex(text.encode('utf-8'))}"
    return _sha256_hex(payload.encode("utf-8"))


def _event_label(event_row: dict[str, Any]) -> str:
    summary = str(event_row.get("summary") or "").strip()
    if summary:
        return summary
    event_type = str(event_row.get("event_type") or "event").strip() or "event"
    event_id = str(event_row.get("id") or "unknown").strip() or "unknown"
    return f"{event_type}:{event_id}"


def _roll_table_ref(packet: dict[str, Any], table_id: str) -> RollTableRef:
    for row in packet.get("known_roll_tables", []):
        if row.get("table_id") != table_id:
            continue
        return RollTableRef(
            table_id=str(row["table_id"]),
            title=str(row["title"]),
            dice=str(row["dice"]),
            source_path=str(row["source_path"]),
            status=str(row.get("status", "pending")),
            default_latency_mode=(
                str(row["default_latency_mode"]) if row.get("default_latency_mode") is not None else None
            ),
        )
    raise UnknownArtifactTarget("roll_table", table_id)


def _resolve_allowed_source_path(root: Path, source_path: str) -> Path:
    candidate = (root / source_path).resolve()
    if not candidate.is_relative_to(root.resolve()):
        raise UnknownArtifactTarget("roll_table", source_path)
    return candidate


def read_event_artifact(*, target_id: str, events: list[dict[str, Any]]) -> ArtifactReadResponse:
    for event_row in events:
        if event_row.get("id") != target_id:
            continue
        title = _event_label(event_row)
        return ArtifactReadResponse(
            target=ProjectionTarget(
                target_type="event",
                target_id=target_id,
                label=title,
                source_status="authoritative",
                metadata={"event_type": event_row.get("event_type"), "created_at": event_row.get("created_at")},
            ),
            artifact_kind="event",
            title=title,
            file_state_token=_event_token(event_row),
            payload=ArtifactReadPayload(content_type="application/json", data=event_row),
            provenance=ArtifactReadProvenance(source_path="event_log.jsonl", source_role="event_log"),
            metadata={"event_type": event_row.get("event_type")},
        )
    raise UnknownArtifactTarget("event", target_id)


def read_roll_table_artifact(*, target_id: str, packet: dict[str, Any], root: Path) -> ArtifactReadResponse:
    ref = _roll_table_ref(packet, target_id)
    source = _resolve_allowed_source_path(root, ref.source_path)
    if not source.is_file():
        raise ArtifactSourceMissing(ref.source_path)

    text = source.read_text(encoding="utf-8")
    parsed = load_parsed_table(ref, root)
    if parsed.shape == "pipe":
        parsed_summary: dict[str, Any] = {"shape": "pipe", "row_count": len(parsed.pipe_rows)}
    else:
        parsed_summary = {
            "shape": "band",
            "band_count": len(parsed.band_sections),
            "row_count": sum(len(rows) for rows in parsed.band_sections.values()),
        }

    target = ProjectionTarget(
        target_type="roll_table",
        target_id=ref.table_id,
        label=ref.title,
        source_status="authoritative",
        metadata={"dice": ref.dice, "status": ref.status, "default_latency_mode": ref.default_latency_mode},
    )
    return ArtifactReadResponse(
        target=target,
        artifact_kind="roll_table",
        title=ref.title,
        file_state_token=file_state_token_for_text(Path(ref.source_path), text),
        payload=ArtifactReadPayload(content_type="text/markdown", text=text),
        provenance=ArtifactReadProvenance(
            source_path=ref.source_path,
            source_role="known_roll_table",
            notes="Resolved from live_packet known_roll_tables allowlist.",
        ),
        metadata={
            "table_id": ref.table_id,
            "title": ref.title,
            "dice": ref.dice,
            "status": ref.status,
            "default_latency_mode": ref.default_latency_mode,
            "parsed_summary": parsed_summary,
        },
    )


def read_artifact_for_target(
    *,
    target_type: ArtifactTargetType,
    target_id: str,
    packet: dict[str, Any],
    events: list[dict[str, Any]],
    root: Path,
) -> ArtifactReadResponse:
    if target_type == "event":
        return read_event_artifact(target_id=target_id, events=events)
    return read_roll_table_artifact(target_id=target_id, packet=packet, root=root)
