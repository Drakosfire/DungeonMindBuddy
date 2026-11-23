"""Immutable identity for one saved Build Worldbuilding extraction attempt."""
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class BuildWorldbuildingLaunchRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    request_id: UUID
    document_id: UUID
    managed_world_id: str = Field(pattern=r'^[A-Za-z0-9][A-Za-z0-9._-]*$')
    expected_revision: int = Field(ge=1, strict=True)
    expected_content_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    profile_id: str
    profile_version: str
