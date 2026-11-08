"""Closed review inputs for one native creature created from a saved World draft."""
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class Closed(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class PrepareNativeThreat(Closed):
    world_id: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,62}$")
    expected_draft_version: int = Field(ge=1, strict=True)


class NativeThreatReview(Closed):
    schema_name: Literal["dmb_native_threat_review_v1"] = Field(
        default="dmb_native_threat_review_v1", alias="schema")
    world_id: str
    draft_id: UUID
    draft_version: int = Field(ge=1)
    label: str = Field(min_length=1)
    body_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    binding: dict[str, Any]
    publication_id: str
    source_evidence_id: str
    source_artifact_id: str
    source_revision_id: str
    prepared_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    principal: str
    expires_at: datetime


class ConfirmNativeThreat(Closed):
    review: NativeThreatReview
    prepared: dict[str, Any]
    token: str = Field(min_length=1)
