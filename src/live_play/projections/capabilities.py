from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from .commands import ProjectionCommandType, ProjectionWriteLane

ProjectionRiskLevel = Literal["low", "medium", "high"]


class ProjectionCapability(BaseModel):
    command_type: ProjectionCommandType
    label: str = Field(min_length=1)
    lane: ProjectionWriteLane
    enabled: bool = True
    required_fields: list[str] = Field(default_factory=list)
    risk_level: ProjectionRiskLevel = "low"
    disabled_reason: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
