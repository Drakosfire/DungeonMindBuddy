"""Immutable request for one exact Build-document Recap extraction attempt."""
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


from apps.live_control_server.models.session_evidence import SessionEvidenceRef


class BuildRecapLaunchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: UUID
    document_id: UUID
    expected_revision: int = Field(ge=1, strict=True)
    expected_content_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    managed_world_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    campaign_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    session: int = Field(ge=1, strict=True)
    session_evidence: list[SessionEvidenceRef] = Field(default_factory=list, max_length=3)
