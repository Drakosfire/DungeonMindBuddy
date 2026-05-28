from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from .invalidation import ProjectionInvalidation
from .targets import ProjectionTarget

ProjectionWriteStatus = Literal["accepted", "rejected", "conflict", "noop"]


class ProjectionConflict(BaseModel):
    conflict_type: str = Field(min_length=1)
    message: str = Field(min_length=1)
    target: ProjectionTarget | None = None
    recoverable: bool = True


class ProjectionWriteResult(BaseModel):
    write_id: str = Field(min_length=1)
    status: ProjectionWriteStatus
    events_appended: list[str] = Field(default_factory=list)
    jobs_queued: list[str] = Field(default_factory=list)
    artifacts_changed: list[ProjectionTarget] = Field(default_factory=list)
    invalidations: list[ProjectionInvalidation] = Field(default_factory=list)
    conflicts: list[ProjectionConflict] = Field(default_factory=list)
    diagnostics: list[str] = Field(default_factory=list)
