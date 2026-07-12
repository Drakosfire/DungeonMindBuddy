"""Revision-pinned World Graph projection contracts (PR007A)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

PROJECTION_REQUEST_SCHEMA = "dmb_world_graph_projection_request_v1"
PROJECTION_RESPONSE_SCHEMA = "dmb_world_graph_projection_v1"
PROJECTION_ERROR_SCHEMA = "dmb_world_graph_projection_error_v1"

FocusKind = Literal["none", "session"]
AdmissibilityPolicy = str

SEARCH_MAX_NODES = 12
SEARCH_MAX_RELATIONSHIPS = 24
SEARCH_MAX_ATTRIBUTES = 32
SEARCH_MAX_EVIDENCE = 32
SEARCH_MAX_SOURCE_ARTIFACTS = 24


class _ProjectionModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        extra="forbid",
        populate_by_name=True,
        strict=True,
    )


class WorldGraphProjectionDiagnostic(_ProjectionModel):
    code: str
    message: str
    severity: Literal["error", "warning", "info"] = "info"


class WorldGraphProjectionFocus(_ProjectionModel):
    kind: FocusKind = "none"
    session_id: str | None = None

    @model_validator(mode="after")
    def _validate_session_id(self) -> WorldGraphProjectionFocus:
        if self.kind == "session" and not self.session_id:
            raise ValueError("session_id is required when focus.kind is session")
        if self.kind == "none" and self.session_id is not None:
            raise ValueError("session_id must be null when focus.kind is none")
        return self


class WorldGraphProjectionRequest(_ProjectionModel):
    schema_: Literal["dmb_world_graph_projection_request_v1"] = Field(alias="schema")
    world_id: str
    campaign_id: str
    focus: WorldGraphProjectionFocus = Field(default_factory=WorldGraphProjectionFocus)
    admissibility: AdmissibilityPolicy = "gm"
    revision_pin: str | None = None
    query_text: str | None = None


class WorldGraphProjectionSnapshot(_ProjectionModel):
    world_id: str
    campaign_id: str
    revision_id: str
    head_revision_id: str
    is_head: bool
    focus: WorldGraphProjectionFocus
    admissibility: AdmissibilityPolicy


class WorldGraphProjectionSummary(_ProjectionModel):
    node_count: int
    relationship_count: int
    attribute_count: int
    evidence_count: int
    source_artifact_count: int
    projection_truncated: bool = False


class WorldGraphProjectionNodeView(_ProjectionModel):
    node_id: str
    label: str
    kind: str
    role: str
    aliases: list[str] = Field(default_factory=list)
    source_domains: list[str] = Field(default_factory=list)
    summary: str | None = None
    anchored_to_focus_session: bool = False


class WorldGraphProjectionAttributeView(_ProjectionModel):
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


class WorldGraphProjectionRelationshipView(_ProjectionModel):
    edge_id: str
    source_node_id: str
    target_node_id: str
    predicate: str
    label: str
    direction: str | None = None
    session_ids: list[str] = Field(default_factory=list)
    visibility: str | None = None
    campaign_scope: str | None = None
    epistemic_kind: str | None = None
    evidence_ref_ids: list[str] = Field(default_factory=list)
    source_artifact_ids: list[str] = Field(default_factory=list)
    active_contribution_ids: list[str] = Field(default_factory=list)


class WorldGraphProjectionEvidenceView(_ProjectionModel):
    evidence_ref_id: str
    source_artifact_id: str
    source_domain: str
    session_id: str | None = None
    locator: str | None = None
    source_span_ref_id: str | None = None
    locator_status: Literal["unverified"] = "unverified"


class WorldGraphProjectionSourceArtifactView(_ProjectionModel):
    source_artifact_id: str
    source_domain: str
    uri: str
    campaign_id: str
    session_id: str | None = None


class WorldGraphProjectionTrustBoundary(_ProjectionModel):
    can_trust: list[str] = Field(default_factory=list)
    cannot_trust: list[str] = Field(default_factory=list)


class WorldGraphQueryContext(_ProjectionModel):
    revision_id: str
    query_text: str
    matched_node_ids: list[str] = Field(default_factory=list)
    nodes: list[WorldGraphProjectionNodeView] = Field(default_factory=list)
    relationships: list[WorldGraphProjectionRelationshipView] = Field(default_factory=list)
    attributes: list[WorldGraphProjectionAttributeView] = Field(default_factory=list)
    evidence: list[WorldGraphProjectionEvidenceView] = Field(default_factory=list)
    source_artifacts: list[WorldGraphProjectionSourceArtifactView] = Field(
        default_factory=list
    )
    diagnostics: list[WorldGraphProjectionDiagnostic] = Field(default_factory=list)


class WorldGraphProjection(_ProjectionModel):
    schema_: Literal["dmb_world_graph_projection_v1"] = Field(alias="schema")
    snapshot: WorldGraphProjectionSnapshot
    summary: WorldGraphProjectionSummary
    nodes: list[WorldGraphProjectionNodeView] = Field(default_factory=list)
    relationships: list[WorldGraphProjectionRelationshipView] = Field(
        default_factory=list
    )
    attributes: list[WorldGraphProjectionAttributeView] = Field(default_factory=list)
    evidence: list[WorldGraphProjectionEvidenceView] = Field(default_factory=list)
    source_artifacts: list[WorldGraphProjectionSourceArtifactView] = Field(
        default_factory=list
    )
    trust_boundary: WorldGraphProjectionTrustBoundary
    diagnostics: list[WorldGraphProjectionDiagnostic] = Field(default_factory=list)
    query_context: WorldGraphQueryContext | None = None


class WorldGraphProjectionErrorResponse(_ProjectionModel):
    schema_: Literal["dmb_world_graph_projection_error_v1"] = Field(
        alias="schema",
        default=PROJECTION_ERROR_SCHEMA,
    )
    code: str
    message: str
    status_code: int
    diagnostics: list[WorldGraphProjectionDiagnostic] = Field(default_factory=list)


def derive_attribute_text_value(value: dict[str, Any]) -> str | None:
    """Lossless text extraction from an attribute value dict — never invents prose."""
    if not value:
        return None
    for key in ("text", "text_value", "summary"):
        raw = value.get(key)
        if isinstance(raw, str) and raw.strip():
            return raw.strip()
    if len(value) == 1:
        only_value = next(iter(value.values()))
        if isinstance(only_value, str) and only_value.strip():
            return only_value.strip()
    return None


def _casefold(value: str | None) -> str:
    return (value or "").casefold()


def _node_search_blob(node: WorldGraphProjectionNodeView) -> str:
    parts = [
        node.node_id,
        node.label,
        node.kind,
        node.role,
        node.summary or "",
        *node.aliases,
    ]
    return " ".join(parts).casefold()


def _attribute_search_blob(attribute: WorldGraphProjectionAttributeView) -> str:
    parts = [
        attribute.predicate or "",
        attribute.label or "",
        attribute.text_value or "",
    ]
    return " ".join(parts).casefold()


def _node_match_score(node: WorldGraphProjectionNodeView, query: str) -> int:
    query_cf = _casefold(query)
    if not query_cf:
        return 0
    if _casefold(node.node_id) == query_cf:
        return 1000
    if _casefold(node.label) == query_cf:
        return 900
    for alias in node.aliases:
        if _casefold(alias) == query_cf:
            return 850
    blob = _node_search_blob(node)
    if query_cf in _casefold(node.label):
        return 700
    if any(query_cf in _casefold(alias) for alias in node.aliases):
        return 650
    if query_cf in _casefold(node.kind) or query_cf in _casefold(node.role):
        return 500
    if node.summary and query_cf in _casefold(node.summary):
        return 300
    if query_cf in blob:
        return 200
    return 0


def _attribute_match_score(
    attribute: WorldGraphProjectionAttributeView,
    query: str,
) -> int:
    query_cf = _casefold(query)
    if not query_cf:
        return 0
    if _casefold(attribute.predicate) == query_cf or _casefold(attribute.label) == query_cf:
        return 250
    blob = _attribute_search_blob(attribute)
    if query_cf in blob:
        return 150
    return 0


def rank_search_node_matches(
    nodes: list[WorldGraphProjectionNodeView],
    attributes: list[WorldGraphProjectionAttributeView],
    query_text: str,
) -> list[tuple[WorldGraphProjectionNodeView, int]]:
    scores: dict[str, int] = {}
    node_by_id = {node.node_id: node for node in nodes}
    for node in nodes:
        score = _node_match_score(node, query_text)
        if score:
            scores[node.node_id] = max(scores.get(node.node_id, 0), score)
    for attribute in attributes:
        score = _attribute_match_score(attribute, query_text)
        if score:
            scores[attribute.subject_node_id] = max(
                scores.get(attribute.subject_node_id, 0),
                score,
            )
    ranked = sorted(
        ((node_by_id[node_id], score) for node_id, score in scores.items() if node_id in node_by_id),
        key=lambda item: (-item[1], item[0].node_id),
    )
    return ranked


__all__ = [
    "PROJECTION_ERROR_SCHEMA",
    "PROJECTION_REQUEST_SCHEMA",
    "PROJECTION_RESPONSE_SCHEMA",
    "SEARCH_MAX_ATTRIBUTES",
    "SEARCH_MAX_EVIDENCE",
    "SEARCH_MAX_NODES",
    "SEARCH_MAX_RELATIONSHIPS",
    "SEARCH_MAX_SOURCE_ARTIFACTS",
    "AdmissibilityPolicy",
    "FocusKind",
    "WorldGraphProjection",
    "WorldGraphProjectionAttributeView",
    "WorldGraphProjectionDiagnostic",
    "WorldGraphProjectionErrorResponse",
    "WorldGraphProjectionEvidenceView",
    "WorldGraphProjectionFocus",
    "WorldGraphProjectionNodeView",
    "WorldGraphProjectionRelationshipView",
    "WorldGraphProjectionRequest",
    "WorldGraphProjectionSnapshot",
    "WorldGraphProjectionSourceArtifactView",
    "WorldGraphProjectionSummary",
    "WorldGraphProjectionTrustBoundary",
    "WorldGraphQueryContext",
    "derive_attribute_text_value",
    "rank_search_node_matches",
]
