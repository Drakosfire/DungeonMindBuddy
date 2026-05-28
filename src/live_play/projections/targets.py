from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

ProjectionTargetType = Literal[
    "event",
    "roll_table",
    "npc",
    "location",
    "runbook_section",
    "job",
    "open_loop",
    "source_packet",
]

ProjectionSourceStatus = Literal[
    "derived",
    "authoritative",
    "live_only",
    "stale",
    "missing",
    "unknown",
]


class ProjectionTarget(BaseModel):
    target_type: ProjectionTargetType
    target_id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    source_status: ProjectionSourceStatus = "derived"
    metadata: dict[str, Any] = Field(default_factory=dict)
