from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from .targets import ProjectionTarget

ProjectionCommandType = Literal[
    "append_observation",
    "queue_canon_patch",
    "patch_artifact",
    "create_open_loop",
    "update_open_loop",
    "pin_scene_state",
    "update_job_status",
    "record_ruling",
    "request_retrieval_refresh",
    "update_layout",
]

ProjectionWriteLane = Literal[
    "observed_play",
    "canon_patch",
    "prep_note",
    "live_state_pin",
    "job_queue",
    "retrieval_curation",
    "layout_config",
    "rules_ruling",
]

ProjectionRequesterType = Literal["human_ui", "agent", "system"]


class ProjectionCommandRequester(BaseModel):
    requester_type: ProjectionRequesterType
    requester_id: str | None = None


class ProjectionEvidenceRef(BaseModel):
    target: ProjectionTarget
    note: str | None = None


class ProjectionCommand(BaseModel):
    command_type: ProjectionCommandType
    target: ProjectionTarget
    lane: ProjectionWriteLane
    payload: dict[str, Any] = Field(default_factory=dict)
    evidence: list[ProjectionEvidenceRef] = Field(default_factory=list)
    requested_by: ProjectionCommandRequester
    idempotency_key: str | None = None
