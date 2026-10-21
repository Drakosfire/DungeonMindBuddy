"""Exact supplemental session evidence pins shared by Recap launch owners."""
from pydantic import BaseModel, ConfigDict, Field


class SessionEvidenceRef(BaseModel):
    model_config=ConfigDict(extra="forbid",strict=True)
    run_id: str = Field(pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
    review_revision: int = Field(ge=1,strict=True)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


