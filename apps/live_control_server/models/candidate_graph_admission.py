"""Stable value models for candidate-graph admission decisions."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from graph_memory.candidate_graph_to_contribution import CandidateGraphMappingError


class CandidateAdmissionDisposition(BaseModel):
    """One explicit decision about an item in the immutable candidate."""

    model_config = ConfigDict(extra="forbid")

    item_id: str
    item_kind: Literal["node", "edge", "beat", "proposed_write"]
    outcome: Literal["rejected", "unresolved"]
    reason: str
    depends_on: list[str] = Field(default_factory=list)


class CandidateIntegrityDiagnostic(BaseModel):
    """Stable fail-closed diagnostic for an incoherent candidate document."""

    model_config = ConfigDict(extra="forbid")

    code: str
    object_id: str | None = None
    field: str | None = None
    message: str


class CandidateAdmissionIntegrityError(CandidateGraphMappingError):
    """Candidate input is incoherent and cannot produce a confirmable plan."""

    def __init__(
        self,
        diagnostics: list[CandidateIntegrityDiagnostic],
        *,
        candidate_digest: str,
    ) -> None:
        self.diagnostics = diagnostics
        self.candidate_digest = candidate_digest
        summary = "; ".join(
            f"{item.code}:{item.object_id or ''}:{item.message}"
            for item in diagnostics[:8]
        )
        super().__init__(f"candidate_invalid ({len(diagnostics)} issues): {summary}")


class CandidateAdmissionBinding(BaseModel):
    """The admission identity sealed into an existing promote proposal effect."""

    model_config = ConfigDict(extra="forbid")

    schema: Literal["dmb_candidate_graph_admission_v1"] = (
        "dmb_candidate_graph_admission_v1"
    )
    candidate_digest: str
    candidate_locator: str | None = None
    candidate_preview_id: str
    source_artifact_id: str
    source_revision_id: str
    world_id: str
    parent_revision_id: str
    dispositions: list[CandidateAdmissionDisposition] = Field(default_factory=list)
    exact_candidate_counts: dict[str, int] = Field(default_factory=dict)

    def as_effect_payload(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
