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

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic.alias_generators import to_camel

from graph_memory.projection.world_projection import (
    FocusKind,
    WorldGraphProjectionFocus,
)

RETRIEVAL_SEARCH_REQUEST_SCHEMA = "dmb_world_graph_search_request_v1"
RETRIEVAL_OBJECT_REQUEST_SCHEMA = "dmb_world_graph_object_request_v1"
RETRIEVAL_NEIGHBORHOOD_REQUEST_SCHEMA = "dmb_world_graph_neighborhood_request_v1"
RETRIEVAL_EVIDENCE_REQUEST_SCHEMA = "dmb_world_graph_evidence_request_v1"
RETRIEVAL_SOURCE_ANCHOR_READ_REQUEST_SCHEMA = "dmb_world_graph_source_anchor_read_request_v1"
RETRIEVAL_RESULT_SCHEMA = "dmb_world_graph_retrieval_result_v1"
RETRIEVAL_SOURCE_ANCHOR_READ_SCHEMA = "dmb_world_graph_source_anchor_read_v1"
RECAP_CONTEXT_INDEX_REQUEST_SCHEMA = "dmb_recap_context_index_request_v1"
RECAP_CONTEXT_INDEX_SCHEMA = "dmb_recap_context_index_v1"
RECAP_CONTEXT_READ_REQUEST_SCHEMA = "dmb_recap_context_read_request_v1"
RECAP_CONTEXT_READ_SCHEMA = "dmb_recap_context_read_v1"
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
LocatorKind = Literal["heading", "json_pointer", "source_span", "unsupported"]


class _RetrievalResponseModel(BaseModel):
    """Response/envelope models may be constructed from field names in Kernel code."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        extra="forbid",
        populate_by_name=True,
        strict=True,
    )


class _RetrievalRequestModel(BaseModel):
    """HTTP request models accept camelCase aliases only — no snake_case wire keys."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        extra="forbid",
        populate_by_name=False,
        strict=True,
    )


class WorldGraphRetrievalDiagnostic(_RetrievalResponseModel):
    code: str
    message: str
    severity: Literal["error", "warning", "info"] = "info"


class WorldGraphRetrievalBounds(_RetrievalRequestModel):
    max_nodes: int = Field(default=8, ge=1, le=12)
    max_relationships: int = Field(default=16, ge=1, le=24)
    max_attributes: int = Field(default=24, ge=1, le=32)
    max_source_anchors: int = Field(default=24, ge=1, le=32)


class WorldGraphRetrievalEvidenceBounds(_RetrievalRequestModel):
    max_source_anchors: int = Field(default=24, ge=1, le=32)


class WorldGraphRetrievalFocus(_RetrievalRequestModel):
    """Alias-only focus for retrieval wire requests (not the projection model)."""

    kind: FocusKind = "none"
    session_id: str | None = None
    campaign_id: str | None = None

    @model_validator(mode="after")
    def _validate_session_id(self) -> WorldGraphRetrievalFocus:
        if self.kind == "session" and not self.session_id:
            raise ValueError("sessionId is required when focus.kind is session")
        if self.kind == "none":
            if self.session_id is not None:
                raise ValueError("sessionId must be null when focus.kind is none")
            if self.campaign_id is not None:
                raise ValueError("campaignId must be null when focus.kind is none")
        return self

    def to_projection_focus(self) -> WorldGraphProjectionFocus:
        return WorldGraphProjectionFocus.model_validate(
            self.model_dump(mode="json", by_alias=True)
        )


class WorldGraphRetrievalRequestContext(_RetrievalRequestModel):
    """Common request context shared by every PR010A operation."""

    world_id: str = Field(min_length=1)
    campaign_id: str
    focus: WorldGraphRetrievalFocus = Field(default_factory=WorldGraphRetrievalFocus)
    admissibility: str = "gm"
    revision_pin: str | None = None
    # campaign: narrative campaign only (+ world-owned null).
    # world: all campaign scopes in the same world (GM cross-campaign lens).
    scope_mode: Literal["campaign", "world"] = "campaign"

    @model_validator(mode="after")
    def _require_campaign_for_campaign_scope(self) -> WorldGraphRetrievalRequestContext:
        if self.scope_mode == "campaign" and not self.campaign_id.strip():
            raise ValueError("campaignId is required when scopeMode is campaign")
        return self


def _reject_blank_ids(value: list[str]) -> list[str]:
    for item in value:
        if not item.strip():
            raise ValueError("id entries must be non-empty")
    return value


class WorldGraphSearchRequest(WorldGraphRetrievalRequestContext):
    schema_: Literal[RETRIEVAL_SEARCH_REQUEST_SCHEMA] = Field(alias="schema")
    query_text: str = Field(min_length=1)
    seed_node_ids: list[str] = Field(default_factory=list)
    bounds: WorldGraphRetrievalBounds = Field(default_factory=WorldGraphRetrievalBounds)

    @field_validator("seed_node_ids")
    @classmethod
    def _validate_seed_node_ids(cls, value: list[str]) -> list[str]:
        return _reject_blank_ids(value)


class WorldGraphObjectRequest(WorldGraphRetrievalRequestContext):
    schema_: Literal[RETRIEVAL_OBJECT_REQUEST_SCHEMA] = Field(alias="schema")
    node_id: str = Field(min_length=1)
    bounds: WorldGraphRetrievalBounds = Field(default_factory=WorldGraphRetrievalBounds)


class WorldGraphNeighborhoodRequest(WorldGraphRetrievalRequestContext):
    schema_: Literal[RETRIEVAL_NEIGHBORHOOD_REQUEST_SCHEMA] = Field(alias="schema")
    seed_node_ids: list[str] = Field(min_length=1, max_length=8)
    max_depth: Literal[1, 2] = 1
    bounds: WorldGraphRetrievalBounds = Field(default_factory=WorldGraphRetrievalBounds)

    @field_validator("seed_node_ids")
    @classmethod
    def _validate_seed_node_ids(cls, value: list[str]) -> list[str]:
        return _reject_blank_ids(value)


class WorldGraphEvidenceTarget(_RetrievalRequestModel):
    kind: EvidenceTargetKind
    id: str = Field(min_length=1)


class WorldGraphEvidenceRequest(WorldGraphRetrievalRequestContext):
    schema_: Literal[RETRIEVAL_EVIDENCE_REQUEST_SCHEMA] = Field(alias="schema")
    target: WorldGraphEvidenceTarget
    bounds: WorldGraphRetrievalEvidenceBounds = Field(
        default_factory=WorldGraphRetrievalEvidenceBounds
    )


class WorldGraphSourceAnchorReadRequest(WorldGraphRetrievalRequestContext):
    schema_: Literal[RETRIEVAL_SOURCE_ANCHOR_READ_REQUEST_SCHEMA] = Field(alias="schema")
    anchor_id: str = Field(min_length=1)
    max_chars: int = Field(
        default=SOURCE_ANCHOR_READ_MAX_CHARS_DEFAULT,
        ge=1,
        le=SOURCE_ANCHOR_READ_MAX_CHARS_HARD_MAX,
    )


class RecapContextIndexRequest(WorldGraphRetrievalRequestContext):
    schema_: Literal[RECAP_CONTEXT_INDEX_REQUEST_SCHEMA] = Field(alias="schema")
    max_entries: int = Field(default=512, ge=1, le=512)

    @model_validator(mode="after")
    def _require_pin(self) -> RecapContextIndexRequest:
        if not self.revision_pin or self.admissibility != "gm":
            raise ValueError("recap context requires a pinned GM projection")
        return self


class RecapContextReadRequest(WorldGraphRetrievalRequestContext):
    schema_: Literal[RECAP_CONTEXT_READ_REQUEST_SCHEMA] = Field(alias="schema")
    context_anchor_id: str = Field(min_length=1)
    max_chars: int = Field(default=SOURCE_ANCHOR_READ_MAX_CHARS_DEFAULT, ge=1, le=SOURCE_ANCHOR_READ_MAX_CHARS_HARD_MAX)
    continuation: str | None = None

    @field_validator("context_anchor_id")
    @classmethod
    def _context_id_only(cls, value: str) -> str:
        if not value.startswith("dm-context-anchor:v1:"):
            raise ValueError("recap context requires a Core context ID")
        return value

    @model_validator(mode="after")
    def _require_pin(self) -> RecapContextReadRequest:
        if not self.revision_pin or self.admissibility != "gm":
            raise ValueError("recap context requires a pinned GM projection")
        return self


class WorldGraphRetrievalSnapshot(_RetrievalResponseModel):
    world_id: str
    campaign_id: str
    revision_id: str
    head_revision_id: str
    is_head: bool
    focus: WorldGraphProjectionFocus
    admissibility: str
    scope_mode: Literal["campaign", "world"] = "campaign"


class WorldGraphRetrievalTrustBoundary(_RetrievalResponseModel):
    can_trust: list[str] = Field(default_factory=list)
    cannot_trust: list[str] = Field(default_factory=list)


class WorldGraphRetrievalCoverage(_RetrievalResponseModel):
    requested_seed_node_ids: list[str] = Field(default_factory=list)
    missing_seed_node_ids: list[str] = Field(default_factory=list)
    resolved_redirects: dict[str, str] = Field(default_factory=dict)
    truncated_fields: list[str] = Field(default_factory=list)
    missing_evidence_ref_ids: list[str] = Field(default_factory=list)
    unreadable_anchor_ids: list[str] = Field(default_factory=list)


class WorldGraphRetrievalNode(_RetrievalResponseModel):
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


class WorldGraphRetrievalRelationship(_RetrievalResponseModel):
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


class WorldGraphRetrievalAttribute(_RetrievalResponseModel):
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


class WorldGraphSourceAnchor(_RetrievalResponseModel):
    anchor_id: str
    revision_id: str
    evidence_ref_id: str
    source_artifact_id: str
    source_domain: str
    session_id: str | None = None
    source_span_ref_id: str | None = None
    supporting_graph_object_ids: list[str] = Field(default_factory=list)
    supporting_assertion_ids: list[str] = Field(default_factory=list)
    readable: bool
    locator_kind: LocatorKind
    display_label: str | None = None


class WorldGraphRetrievalResult(_RetrievalResponseModel):
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


class WorldGraphSourceAnchorReadResult(_RetrievalResponseModel):
    schema_: Literal[RETRIEVAL_SOURCE_ANCHOR_READ_SCHEMA] = Field(
        alias="schema", default=RETRIEVAL_SOURCE_ANCHOR_READ_SCHEMA
    )
    outcome: RetrievalOutcome
    snapshot: WorldGraphRetrievalSnapshot | None = None
    anchor_id: str
    evidence_ref_id: str | None = None
    source_artifact_id: str | None = None
    source_domain: str | None = None
    source_span_ref_id: str | None = None
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


class RecapContextDescriptor(_RetrievalResponseModel):
    context_anchor_id: str
    world_id: str
    campaign_id: str | None
    graph_revision_id: str
    source_artifact_id: str
    source_revision_id: str
    source_uri: str
    content_sha256: str
    expected_session_id: str
    expected_heading: str
    selector_schema: Literal["dm_recap_context_section_selector_v1"] = "dm_recap_context_section_selector_v1"
    selector_policy: Literal["markdown-session-recap-v1"] = "markdown-session-recap-v1"


class RecapContextIndexResult(_RetrievalResponseModel):
    schema_: Literal[RECAP_CONTEXT_INDEX_SCHEMA] = Field(alias="schema", default=RECAP_CONTEXT_INDEX_SCHEMA)
    snapshot: WorldGraphRetrievalSnapshot
    status: Literal["complete", "overflow"]
    eligible_count: int
    max_entries: int
    entries: list[RecapContextDescriptor] = Field(default_factory=list)


class RecapContextReadResult(_RetrievalResponseModel):
    schema_: Literal[RECAP_CONTEXT_READ_SCHEMA] = Field(alias="schema", default=RECAP_CONTEXT_READ_SCHEMA)
    outcome: Literal["enough", "truncated", "empty", "unavailable"]
    snapshot: WorldGraphRetrievalSnapshot
    context_anchor_id: str
    context: RecapContextDescriptor | None = None
    media_type: str | None = None
    content: str | None = None
    heading_line: int | None = None
    line_start: int | None = None
    line_end: int | None = None
    section_sha256: str | None = None
    offset_chars: int = 0
    truncated: bool = False
    next_continuation: str | None = None
    diagnostics: list[WorldGraphRetrievalDiagnostic] = Field(default_factory=list)


class WorldGraphRetrievalErrorResponse(_RetrievalResponseModel):
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
    "RECAP_CONTEXT_INDEX_REQUEST_SCHEMA",
    "RECAP_CONTEXT_INDEX_SCHEMA",
    "RECAP_CONTEXT_READ_REQUEST_SCHEMA",
    "RECAP_CONTEXT_READ_SCHEMA",
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
    "WorldGraphRetrievalFocus",
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
    "RecapContextIndexRequest",
    "RecapContextReadRequest",
    "RecapContextDescriptor",
    "RecapContextIndexResult",
    "RecapContextReadResult",
    "compute_source_anchor_id",
]


class RecapContextIndexRequestV2(RecapContextIndexRequest):
    schema_: Literal["dmb_recap_context_index_request_v2"] = Field(alias="schema")


class RecapContextReadRequestV2(WorldGraphRetrievalRequestContext):
    schema_: Literal["dmb_recap_context_read_request_v2"] = Field(alias="schema")
    context_anchor_id: str = Field(min_length=1)
    max_chars: int = Field(default=SOURCE_ANCHOR_READ_MAX_CHARS_DEFAULT, ge=1, le=SOURCE_ANCHOR_READ_MAX_CHARS_HARD_MAX)
    continuation: str | None = None

    @field_validator("context_anchor_id")
    @classmethod
    def _known_context_version(cls, value: str) -> str:
        if not value.startswith(("dm-context-anchor:v1:", "dm-context-anchor:v2:")):
            raise ValueError("recap context requires a known Core context ID")
        return value

    @model_validator(mode="after")
    def _require_pin(self):
        if not self.revision_pin or self.admissibility != "gm":
            raise ValueError("recap context requires a pinned GM projection")
        return self


class RecapContextDescriptorV2(_RetrievalResponseModel):
    context_anchor_id: str
    world_id: str
    campaign_id: str | None
    graph_revision_id: str
    source_artifact_id: str
    source_revision_id: str
    source_uri: str
    content_sha256: str
    expected_session_id: str
    canonical_heading: str
    legacy_session_heading: str
    legacy_recap_marker: str
    selector_schema: Literal["dm_recap_context_section_selector_v2"] = "dm_recap_context_section_selector_v2"
    selector_policy: Literal["markdown-session-recap-v2"] = "markdown-session-recap-v2"


class RecapContextIndexResultV2(_RetrievalResponseModel):
    schema_: Literal["dmb_recap_context_index_v2"] = Field(alias="schema", default="dmb_recap_context_index_v2")
    snapshot: WorldGraphRetrievalSnapshot
    status: Literal["complete", "overflow"]
    eligible_count: int
    max_entries: int
    entries: list[RecapContextDescriptorV2] = Field(default_factory=list)


class RecapContextReadResultV2(_RetrievalResponseModel):
    schema_: Literal["dmb_recap_context_read_v2"] = Field(alias="schema", default="dmb_recap_context_read_v2")
    outcome: Literal["enough", "truncated", "empty", "unavailable"]
    snapshot: WorldGraphRetrievalSnapshot
    context_anchor_id: str
    context: RecapContextDescriptorV2 | None = None
    media_type: str | None = None
    content: str | None = None
    selected_form: Literal["canonical_h1", "legacy_h2"] | None = None
    heading_line: int | None = None
    session_heading_line: int | None = None
    recap_marker_line: int | None = None
    line_start: int | None = None
    line_end: int | None = None
    section_sha256: str | None = None
    offset_chars: int = 0
    truncated: bool = False
    next_continuation: str | None = None
    diagnostics: list[WorldGraphRetrievalDiagnostic] = Field(default_factory=list)
