"""Read-only Build source-navigation response models."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

SOURCE_NAVIGATION_SCHEMA = "dmb_build_source_navigation_v1"
SourceNavigationStatus = Literal["exact", "stale"]


class _SourceNavigationModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        extra="forbid",
        populate_by_name=True,
        strict=True,
    )


class BuildSourceNavigationResponse(_SourceNavigationModel):
    schema_: Literal["dmb_build_source_navigation_v1"] = Field(
        default=SOURCE_NAVIGATION_SCHEMA,
        alias="schema",
    )
    status: SourceNavigationStatus
    source_artifact_id: str
    source_span_ref_id: str
    document_id: str
    world_id: str
    campaign_id: str
    artifact_document_revision: int
    current_document_revision: int
    artifact_content_sha256: str
    current_content_sha256: str
    start_line: int
    end_line: int
    can_highlight: bool
    message: str
    diagnostics: list[str] = Field(default_factory=list)
