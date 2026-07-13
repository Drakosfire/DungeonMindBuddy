"""World Graph retrieval + source-anchor admission contract (PR010A).

Strict, camelCase, ``extra="forbid"`` request/result/anchor/error schemas for
graph-only retrieval exposed through the Graph Kernel and live-control API.
These models never accept a caller-supplied path, URI, manifest selector, or
run identifier; the only handle a caller may present back to
``read_source_anchor`` is an opaque ``anchorId`` emitted by this contract.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel

from graph_memory.projection.world_projection import WorldGraphProjectionFocus

RETRIEVAL_SEARCH_REQUEST_SCHEMA = "dmb_world_graph_search_request_v1"
RETRIEVAL_OBJECT_REQUEST_SCHEMA = "dmb_world_graph_object_request_v1"
RETRIEVAL_NEIGHBORHOOD_REQUEST_SCHEMA = "dmb_world_graph_neighborhood_request_v1"
RETRIEVAL_EVIDENCE_REQUEST_SCHEMA = "dmb_world_graph_evidence_request_v1"
RETRIEVAL_SOURCE_ANCHOR_READ_REQUEST_SCHEMA = "dmb_world_graph_source_anchor_read_request_v1"
RETRIEVAL_RESULT_SCHEMA = "dmb_world_graph_retrieval_result_v1"
RETRIEVAL_SOURCE_ANCHOR_READ_SCHEMA = "dmb_world_graph_source_anchor_read_v1"
RETRIEVAL_ERROR_SCHEMA = "dmb_world_graph_retrieval_error_v1"

ANCHOR_SCHEMA_VERSION = "v1"
ANCHOR_ID_PREFIX = "source-anchor:v1:"

SOURCE_ANCHOR_READ_MAX_CHARS_DEFAULT = 4000
SOURCE_ANCHOR_READ_MAX_CHARS_HARD_MAX = 12000

RetrievalOutcome = Literal[
    "enough",
    "partial",
    "empty",
    "denied",
    "truncated",
    "unavailable",
]
RetrievalOperation = Literal["search", "object", "neighborhood", "evidence"]
EvidenceTargetKind = Literal["node", "relationship", "attribute"]
LocatorKind = Literal["heading", "json_pointer", "unsupported"]


class _RetrievalModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        extra="forbid",
        populate_by_name=True,
        strict=True,
    )


class WorldGraphRetrievalDiagnostic(_RetrievalModel):
    code: str
    message: str
    severity: Literal["error", "warning", "info"] = "info"


class WorldGraphRetrievalBounds(_RetrievalModel):
    max_nodes: int = Field(default=8, ge=1, le=12)
    max_relationships: int = Field(default=16, ge=1, le=24)
    max_attributes: int = Field(default=24, ge=1, le=32)
    max_source_anchors: int = Field(default=24, ge=1, le=32)


class WorldGraphRetrievalEvidenceBounds(_RetrievalModel):
    max_source_anchors: int = Field(default=24, ge=1, le=32)


class WorldGraphRetrievalRequestContext(_RetrievalModel):
    """Common request context shared by every PR010A operation."""

    world_id: str = Field(min_length=1)
    campaign_id: str = Field(min_length=1)
    focus: WorldGraphProjectionFocus = Field(default_factory=WorldGraphProjectionFocus)
    admissibility: str = "gm"
    revision_pin: str | None = None


def _reject_blank_ids(value: list[str]) -> list[str]:
    for item in value:
        if not item.strip():
            raise ValueError("id entries must be non-empty")
    return value


class WorldGraphSearchRequest(WorldGraphRetrievalRequestContext):
    schema_: Literal[RETRIEVAL_SEARCH_REQUEST_SCHEMA] = Field(
        alias="schema", default=RETRIEVAL_SEARCH_REQUEST_SCHEMA
    )
    query_text: str = Field(min_length=1)
    seed_node_ids: list[str] = Field(default_factory=list)
    bounds: WorldGraphRetrievalBounds = Field(default_factory=WorldGraphRetrievalBounds)

    @field_validator("seed_node_ids")
    @classmethod
    def _validate_seed_node_ids(cls, value: list[str]) -> list[str]:
        return _reject_blank_ids(value)


class WorldGraphObjectRequest(WorldGraphRetrievalRequestContext):
    schema_: Literal[RETRIEVAL_OBJECT_REQUEST_SCHEMA] = Field(
        alias="schema", default=RETRIEVAL_OBJECT_REQUEST_SCHEMA
    )
    node_id: str = Field(min_length=1)
    bounds: WorldGraphRetrievalBounds = Field(default_factory=WorldGraphRetrievalBounds)


class WorldGraphNeighborhoodRequest(WorldGraphRetrievalRequestContext):
    schema_: Literal[RETRIEVAL_NEIGHBORHOOD_REQUEST_SCHEMA] = Field(
        alias="schema", default=RETRIEVAL_NEIGHBORHOOD_REQUEST_SCHEMA
    )
    seed_node_ids: list[str] = Field(min_length=1, max_length=8)
    max_depth: Literal[1, 2] = 1
    bounds: WorldGraphRetrievalBounds = Field(default_factory=WorldGraphRetrievalBounds)

    @field_validator("seed_node_ids")
    @classmethod
    def _validate_seed_node_ids(cls, value: list[str]) -> list[str]:
        return _reject_blank_ids(value)


class WorldGraphEvidenceTarget(_RetrievalModel):
    kind: EvidenceTargetKind
    id: str = Field(min_length=1)


class WorldGraphEvidenceRequest(WorldGraphRetrievalRequestContext):
    schema_: Literal[RETRIEVAL_EVIDENCE_REQUEST_SCHEMA] = Field(
        alias="schema", default=RETRIEVAL_EVIDENCE_REQUEST_SCHEMA
    )
    target: WorldGraphEvidenceTarget
    bounds: WorldGraphRetrievalEvidenceBounds = Field(
        default_factory=WorldGraphRetrievalEvidenceBounds
    )


class WorldGraphSourceAnchorReadRequest(WorldGraphRetrievalRequestContext):
    schema_: Literal[RETRIEVAL_SOURCE_ANCHOR_READ_REQUEST_SCHEMA] = Field(
        alias="schema", default=RETRIEVAL_SOURCE_ANCHOR_READ_REQUEST_SCHEMA
    )
    anchor_id: str = Field(min_length=1)
    max_chars: int = Field(
        default=SOURCE_ANCHOR_READ_MAX_CHARS_DEFAULT,
        ge=1,
        le=SOURCE_ANCHOR_READ_MAX_CHARS_HARD_MAX,
    )


class WorldGraphRetrievalSnapshot(_RetrievalModel):
    world_id: str
    campaign_id: str
    revision_id: str
    head_revision_id: str
    is_head: bool
    focus: WorldGraphProjectionFocus
    admissibility: str


class WorldGraphRetrievalTrustBoundary(_RetrievalModel):
    can_trust: list[str] = Field(default_factory=list)
    cannot_trust: list[str] = Field(default_factory=list)


class WorldGraphRetrievalCoverage(_RetrievalModel):
    requested_seed_node_ids: list[str] = Field(default_factory=list)
    missing_seed_node_ids: list[str] = Field(default_factory=list)
    resolved_redirects: dict[str, str] = Field(default_factory=dict)
    truncated_fields: list[str] = Field(default_factory=list)
    missing_evidence_ref_ids: list[str] = Field(default_factory=list)
    unreadable_anchor_ids: list[str] = Field(default_factory=list)


class WorldGraphRetrievalNode(_RetrievalModel):
    node_id: str
    label: str
    kind: str
    role: str
    aliases: list[str] = Field(default_factory=list)
    source_domains: list[str] = Field(default_factory=list)
    summary: str | None = None
    anchored_to_focus_session: bool = False
    evidence_ref_ids: list[str] = Field(default_factory=list)
    source_artifact_ids: list[str] = Field(default_factory=list)


class WorldGraphRetrievalRelationship(_RetrievalModel):
    edge_id: str
    source_node_id: str
    target_node_id: str
    predicate: str
    label: str
    direction: str | None = None
    direction_from_node_id: str | None = None
    session_ids: list[str] = Field(default_factory=list)
    source_domains: list[str] = Field(default_factory=list)
    visibility: str | None = None
    campaign_scope: str | None = None
    epistemic_kind: str | None = None
    evidence_ref_ids: list[str] = Field(default_factory=list)
    source_artifact_ids: list[str] = Field(default_factory=list)
    active_contribution_ids: list[str] = Field(default_factory=list)


class WorldGraphRetrievalAttribute(_RetrievalModel):
    assertion_id: str
    subject_node_id: str
    predicate: str | None = None
    label: str | None = None
    value: dict[str, Any] = Field(default_factory=dict)
    text_value: str | None = None
    epistemic_kind: str | None = None
    visibility: str | None = None
    campaign_scope: str | None = None
    temporal_scope: dict[str, Any] | None = None
    support_state: str | None = None
    active_contribution_ids: list[str] = Field(default_factory=list)
    evidence_ref_ids: list[str] = Field(default_factory=list)
    source_artifact_ids: list[str] = Field(default_factory=list)


class WorldGraphSourceAnchor(_RetrievalModel):
    anchor_id: str
    revision_id: str
    evidence_ref_id: str
    source_artifact_id: str
    source_domain: str
    session_id: str | None = None
    supporting_graph_object_ids: list[str] = Field(default_factory=list)
    supporting_assertion_ids: list[str] = Field(default_factory=list)
    readable: bool
    locator_kind: LocatorKind
    display_label: str | None = None


class WorldGraphRetrievalResult(_RetrievalModel):
    schema_: Literal[RETRIEVAL_RESULT_SCHEMA] = Field(
        alias="schema", default=RETRIEVAL_RESULT_SCHEMA
    )
    operation: RetrievalOperation
    outcome: RetrievalOutcome
    snapshot: WorldGraphRetrievalSnapshot | None = None
    request_summary: dict[str, Any] = Field(default_factory=dict)
    matched_node_ids: list[str] = Field(default_factory=list)
    match_reasons: dict[str, list[str]] = Field(default_factory=dict)
    requested_node_id: str | None = None
    resolved_node_id: str | None = None
    nodes: list[WorldGraphRetrievalNode] = Field(default_factory=list)
    relationships: list[WorldGraphRetrievalRelationship] = Field(default_factory=list)
    attributes: list[WorldGraphRetrievalAttribute] = Field(default_factory=list)
    source_anchors: list[WorldGraphSourceAnchor] = Field(default_factory=list)
    coverage: WorldGraphRetrievalCoverage = Field(default_factory=WorldGraphRetrievalCoverage)
    trust_boundary: WorldGraphRetrievalTrustBoundary = Field(
        default_factory=WorldGraphRetrievalTrustBoundary
    )
    diagnostics: list[WorldGraphRetrievalDiagnostic] = Field(default_factory=list)


class WorldGraphSourceAnchorReadResult(_RetrievalModel):
    schema_: Literal[RETRIEVAL_SOURCE_ANCHOR_READ_SCHEMA] = Field(
        alias="schema", default=RETRIEVAL_SOURCE_ANCHOR_READ_SCHEMA
    )
    outcome: RetrievalOutcome
    snapshot: WorldGraphRetrievalSnapshot | None = None
    anchor_id: str
    evidence_ref_id: str | None = None
    source_artifact_id: str | None = None
    source_domain: str | None = None
    locator_kind: LocatorKind | None = None
    media_type: str | None = None
    content: str | None = None
    content_sha256: str | None = None
    line_start: int | None = None
    line_end: int | None = None
    truncated: bool = False
    trust_boundary: WorldGraphRetrievalTrustBoundary = Field(
        default_factory=WorldGraphRetrievalTrustBoundary
    )
    diagnostics: list[WorldGraphRetrievalDiagnostic] = Field(default_factory=list)


class WorldGraphRetrievalErrorResponse(_RetrievalModel):
    schema_: Literal[RETRIEVAL_ERROR_SCHEMA] = Field(
        alias="schema", default=RETRIEVAL_ERROR_SCHEMA
    )
    code: str
    message: str
    status_code: int
    diagnostics: list[WorldGraphRetrievalDiagnostic] = Field(default_factory=list)


def compute_source_anchor_id(
    *,
    world_id: str,
    campaign_id: str,
    focus: WorldGraphProjectionFocus,
    admissibility: str,
    revision_id: str,
    evidence_ref_id: str,
    source_artifact_id: str,
    locator_identity: str,
) -> str:
    """Deterministically derive an opaque ``source-anchor:v1:<sha256>`` id.

    The digest is computed over canonical JSON so that the same admissible
    context (world/campaign/focus/admissibility/revision) plus the same
    evidence/source-artifact/locator identity always produces the same
    anchor id, and no other context can forge or reuse it.
    """
    canonical_payload = {
        "schemaVersion": ANCHOR_SCHEMA_VERSION,
        "worldId": world_id,
        "campaignId": campaign_id,
        "focus": focus.model_dump(mode="json", by_alias=True),
        "admissibility": admissibility,
        "revisionId": revision_id,
        "evidenceRefId": evidence_ref_id,
        "sourceArtifactId": source_artifact_id,
        "locatorIdentity": locator_identity,
    }
    canonical_json = json.dumps(canonical_payload, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
    return f"{ANCHOR_ID_PREFIX}{digest}"


__all__ = [
    "ANCHOR_ID_PREFIX",
    "ANCHOR_SCHEMA_VERSION",
    "RETRIEVAL_ERROR_SCHEMA",
    "RETRIEVAL_EVIDENCE_REQUEST_SCHEMA",
    "RETRIEVAL_NEIGHBORHOOD_REQUEST_SCHEMA",
    "RETRIEVAL_OBJECT_REQUEST_SCHEMA",
    "RETRIEVAL_RESULT_SCHEMA",
    "RETRIEVAL_SEARCH_REQUEST_SCHEMA",
    "RETRIEVAL_SOURCE_ANCHOR_READ_REQUEST_SCHEMA",
    "RETRIEVAL_SOURCE_ANCHOR_READ_SCHEMA",
    "SOURCE_ANCHOR_READ_MAX_CHARS_DEFAULT",
    "SOURCE_ANCHOR_READ_MAX_CHARS_HARD_MAX",
    "EvidenceTargetKind",
    "LocatorKind",
    "RetrievalOperation",
    "RetrievalOutcome",
    "WorldGraphEvidenceRequest",
    "WorldGraphEvidenceTarget",
    "WorldGraphNeighborhoodRequest",
    "WorldGraphObjectRequest",
    "WorldGraphRetrievalAttribute",
    "WorldGraphRetrievalBounds",
    "WorldGraphRetrievalCoverage",
    "WorldGraphRetrievalDiagnostic",
    "WorldGraphRetrievalErrorResponse",
    "WorldGraphRetrievalEvidenceBounds",
    "WorldGraphRetrievalNode",
    "WorldGraphRetrievalRelationship",
    "WorldGraphRetrievalRequestContext",
    "WorldGraphRetrievalResult",
    "WorldGraphRetrievalSnapshot",
    "WorldGraphRetrievalTrustBoundary",
    "WorldGraphSearchRequest",
    "WorldGraphSourceAnchor",
    "WorldGraphSourceAnchorReadRequest",
    "WorldGraphSourceAnchorReadResult",
    "compute_source_anchor_id",
]
