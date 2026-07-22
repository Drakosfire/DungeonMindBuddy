from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

EXTRACTION_RUN_SCHEMA = "dmb_extraction_run_v1"
EXTRACTION_RUN_VERSION = "1.0"

REQUIRED_REVIEWABLE_COMPONENT_KINDS = frozenset(
    {
        "source_artifact",
        "source_span_index",
        "candidate_graph",
    }
)


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


TERMINAL_EXTRACTION_RUN_STATUSES = frozenset(
    {
        ExtractionRunStatus.PROMOTED,
        ExtractionRunStatus.REJECTED,
        ExtractionRunStatus.FAILED,
        ExtractionRunStatus.SUPERSEDED,
    }
)

FROZEN_COMPONENT_STATUSES = frozenset(
    {
        ExtractionRunStatus.REVIEWABLE,
        *TERMINAL_EXTRACTION_RUN_STATUSES,
    }
)

ALLOWED_EXTRACTION_RUN_TRANSITIONS: dict[ExtractionRunStatus, frozenset[ExtractionRunStatus]] = {
    ExtractionRunStatus.DRAFT: frozenset(
        {
            ExtractionRunStatus.PREPARED,
            ExtractionRunStatus.INCOMPLETE,
            ExtractionRunStatus.FAILED,
        }
    ),
    ExtractionRunStatus.PREPARED: frozenset(
        {
            ExtractionRunStatus.EXTRACTED,
            ExtractionRunStatus.INCOMPLETE,
            ExtractionRunStatus.FAILED,
        }
    ),
    ExtractionRunStatus.EXTRACTED: frozenset(
        {
            ExtractionRunStatus.VALIDATED,
            ExtractionRunStatus.INCOMPLETE,
            ExtractionRunStatus.FAILED,
        }
    ),
    ExtractionRunStatus.VALIDATED: frozenset(
        {
            ExtractionRunStatus.REVIEWABLE,
            ExtractionRunStatus.INCOMPLETE,
            ExtractionRunStatus.FAILED,
        }
    ),
    ExtractionRunStatus.REVIEWABLE: frozenset(
        {
            ExtractionRunStatus.PROMOTED,
            ExtractionRunStatus.REJECTED,
            ExtractionRunStatus.FAILED,
        }
    ),
    ExtractionRunStatus.INCOMPLETE: frozenset(
        {
            ExtractionRunStatus.DRAFT,
            ExtractionRunStatus.PREPARED,
            ExtractionRunStatus.EXTRACTED,
            ExtractionRunStatus.VALIDATED,
            ExtractionRunStatus.FAILED,
        }
    ),
    ExtractionRunStatus.PROMOTED: frozenset(),
    ExtractionRunStatus.REJECTED: frozenset(),
    ExtractionRunStatus.FAILED: frozenset(),
    ExtractionRunStatus.SUPERSEDED: frozenset(),
}


class ExtractionRunComponentKind(StrEnum):
    SOURCE_ARTIFACT = "source_artifact"
    SOURCE_SPAN_INDEX = "source_span_index"
    CANDIDATE_GRAPH = "candidate_graph"
    VALIDATION_REPORT = "validation_report"
    PASS_OUTPUTS = "pass_outputs"
    PASS_TELEMETRY = "pass_telemetry"
    CONSOLIDATION_DIAGNOSTICS = "consolidation_diagnostics"
    RAW_MODEL_RESPONSE = "raw_model_response"
    PROVENANCE_INDEX = "provenance_index"


class ExtractionRunComponentRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: ExtractionRunComponentKind
    uri: str
    sha256: str | None = None
    # Caller-claimed existence is advisory only; registry resolution is authoritative.
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
    revision: int = 1
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

    @model_validator(mode="after")
    def _validate_persisted_invariants(self) -> ExtractionRun:
        validate_extraction_run_record(self)
        return self

    def has_required_review_components(self) -> bool:
        """Shape check only: required kinds present with uri + digest claims."""
        for kind in REQUIRED_REVIEWABLE_COMPONENT_KINDS:
            component = self.components.get(kind)
            if component is None:
                return False
            if not component.uri.strip():
                return False
            if not (component.sha256 or "").strip():
                return False
        return True

    def is_reviewable(self) -> bool:
        """True only when status claims reviewable and required component shape is present.

        Path/digest resolvability is enforced by the server registry, not this method.
        """
        if self.status != ExtractionRunStatus.REVIEWABLE:
            return False
        return self.has_required_review_components()


def validate_extraction_run_record(run: ExtractionRun) -> None:
    """Fail-closed invariants for persisted ExtractionRun records."""
    if not run.run_id.strip():
        raise ValueError("run_id is required")
    if not run.source_artifact_id.strip():
        raise ValueError("source_artifact_id is required")
    if run.revision < 1:
        raise ValueError("revision must be >= 1")
    if run.source_domain == "worldbuilding" and run.session_id is not None:
        raise ValueError("worldbuilding extraction runs must not fabricate session_id")
    if run.source_domain == "recap" and (not run.campaign_id or not run.session_id):
        raise ValueError("recap extraction runs require campaign_id and session_id")
    seen_kinds: set[ExtractionRunComponentKind] = set()
    for key, component in run.components.items():
        if key != component.kind.value:
            raise ValueError(
                f"component key must equal kind: {key!r} != {component.kind.value!r}"
            )
        if component.kind in seen_kinds:
            raise ValueError(f"duplicate component kind: {component.kind.value}")
        seen_kinds.add(component.kind)
    if run.status == ExtractionRunStatus.REVIEWABLE and not run.has_required_review_components():
        raise ValueError("incomplete ExtractionRun cannot be reviewable")
    if run.status == ExtractionRunStatus.PROMOTED and not run.has_required_review_components():
        raise ValueError("promoted ExtractionRun requires the complete review bundle")
    if run.status == ExtractionRunStatus.SUPERSEDED and not run.superseded_by_run_id:
        raise ValueError("superseded runs require superseded_by_run_id")
    if run.superseded_by_run_id and run.superseded_by_run_id == run.run_id:
        raise ValueError("superseded_by_run_id must not self-reference")
    if run.supersedes_run_id and run.supersedes_run_id == run.run_id:
        raise ValueError("supersedes_run_id must not self-reference")


def validate_extraction_run_lineage(runs: list[ExtractionRun]) -> None:
    """Validate reciprocal supersession and acyclic lineage across a registry document."""
    by_id: dict[str, ExtractionRun] = {}
    for run in runs:
        if run.run_id in by_id:
            raise ValueError(f"duplicate extraction run id: {run.run_id}")
        by_id[run.run_id] = run

    for run in runs:
        if run.superseded_by_run_id:
            successor = by_id.get(run.superseded_by_run_id)
            if successor is None:
                raise ValueError(
                    f"superseded_by_run_id missing successor: {run.superseded_by_run_id}"
                )
            if successor.supersedes_run_id != run.run_id:
                raise ValueError(
                    f"non-reciprocal supersession: {run.run_id} superseded_by "
                    f"{run.superseded_by_run_id}"
                )
        if run.supersedes_run_id:
            predecessor = by_id.get(run.supersedes_run_id)
            if predecessor is None:
                raise ValueError(
                    f"supersedes_run_id missing predecessor: {run.supersedes_run_id}"
                )
            if predecessor.superseded_by_run_id != run.run_id:
                raise ValueError(
                    f"non-reciprocal supersession: {run.run_id} supersedes "
                    f"{run.supersedes_run_id}"
                )

    for run in runs:
        seen: set[str] = set()
        current_id: str | None = run.run_id
        while current_id is not None:
            if current_id in seen:
                raise ValueError(f"supersession lineage cycle involving {current_id}")
            seen.add(current_id)
            current = by_id.get(current_id)
            if current is None:
                break
            current_id = current.supersedes_run_id


def assert_run_not_reviewable_when_incomplete(run: ExtractionRun) -> None:
    if run.status == ExtractionRunStatus.REVIEWABLE and not run.is_reviewable():
        raise ValueError("incomplete ExtractionRun cannot be reviewable")


def assert_allowed_extraction_run_transition(
    current: ExtractionRunStatus,
    target: ExtractionRunStatus,
) -> None:
    if current == target:
        raise ValueError(f"extraction run status is already {current.value}")
    allowed = ALLOWED_EXTRACTION_RUN_TRANSITIONS.get(current, frozenset())
    if target not in allowed:
        raise ValueError(
            f"invalid extraction run transition: {current.value} -> {target.value}"
        )


def normalize_content_digest(value: str | None) -> str:
    if value is None:
        return ""
    digest = value.strip()
    if digest.startswith("sha256:"):
        digest = digest[len("sha256:") :]
    return digest.lower()
