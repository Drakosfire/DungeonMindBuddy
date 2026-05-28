from __future__ import annotations

from pydantic import BaseModel, Field

from .targets import ProjectionTarget


class ProjectionInvalidation(BaseModel):
    projection_key: str = Field(min_length=1)
    target: ProjectionTarget | None = None
    reason: str = Field(min_length=1)
