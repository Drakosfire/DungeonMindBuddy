from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

EXTRACTION_RUN_SCHEMA = "dmb_extraction_run_v1"
EXTRACTION_RUN_VERSION = "1.0"


class ExtractionRunStatus(StrEnum):
    DRAFT = "draft"
    PREPARED = "prepared"
    EXTRACTED = "extracted"
    VALIDATED = "validated"
    REVIEWABLE = "reviewable"
    PROMOTED = "promoted"
    REJECTED = "rejected"
    INCOMPLETE = "incomplete"
    FAILED = "failed"
    SUPERSEDED = "superseded"


class ExtractionRunComponentKind(StrEnum):
    SOURCE_ARTIFACT = "source_artifact"
    SOURCE_SPAN_INDEX = "source_span_index"
    CANDIDATE_GRAPH = "candidate_graph"
    VALIDATION_REPORT = "validation_report"
    PASS_TELEMETRY = "pass_telemetry"
    PROVENANCE_INDEX = "provenance_index"


class ExtractionRunComponentRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: ExtractionRunComponentKind
    uri: str
    sha256: str | None = None
    exists: bool = False


class ExtractionRunDiagnostics(BaseModel):
    model_config = ConfigDict(extra="allow")

    messages: list[str] = Field(default_factory=list)
    incomplete_components: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class ExtractionRun(BaseModel):
    """Canonical source-domain-neutral exact extraction run."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["dmb_extraction_run_v1"] = EXTRACTION_RUN_SCHEMA
    version: str = EXTRACTION_RUN_VERSION
    run_id: str
    source_artifact_id: str
    source_domain: str
    status: ExtractionRunStatus = ExtractionRunStatus.DRAFT
    campaign_id: str | None = None
    session_id: str | None = None
    profile_id: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    components: dict[str, ExtractionRunComponentRef] = Field(default_factory=dict)
    diagnostics: ExtractionRunDiagnostics = Field(default_factory=ExtractionRunDiagnostics)
    superseded_by_run_id: str | None = None
    supersedes_run_id: str | None = None
    lineage: dict[str, Any] = Field(default_factory=dict)

    def is_reviewable(self) -> bool:
        if self.status != ExtractionRunStatus.REVIEWABLE:
            return False
        required = {
            ExtractionRunComponentKind.SOURCE_ARTIFACT.value,
            ExtractionRunComponentKind.SOURCE_SPAN_INDEX.value,
            ExtractionRunComponentKind.CANDIDATE_GRAPH.value,
        }
        present = {
            component.kind.value
            for component in self.components.values()
            if component.exists
        }
        return required.issubset(present)


def assert_run_not_reviewable_when_incomplete(run: ExtractionRun) -> None:
    if run.status == ExtractionRunStatus.REVIEWABLE and not run.is_reviewable():
        raise ValueError("incomplete ExtractionRun cannot be reviewable")
