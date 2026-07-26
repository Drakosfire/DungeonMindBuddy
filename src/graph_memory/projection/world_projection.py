"""Revision-pinned World Graph projection contracts (PR007A)."""

from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

PROJECTION_REQUEST_SCHEMA = "dmb_world_graph_projection_request_v1"
PROJECTION_RESPONSE_SCHEMA = "dmb_world_graph_projection_v1"
PROJECTION_ERROR_SCHEMA = "dmb_world_graph_projection_error_v1"

FocusKind = Literal["none", "session"]
ScopeMode = Literal["campaign", "world"]
AdmissibilityPolicy = str
WorldGraphRelationshipDirection = Literal["outgoing", "incoming", "related"]

_WORLD_GRAPH_DIRECTION_ALIASES: dict[str, WorldGraphRelationshipDirection] = {
    "outbound": "outgoing",
    "outgoing": "outgoing",
    "inbound": "incoming",
    "incoming": "incoming",
    "related": "related",
}


class WorldGraphDirectionError(ValueError):
    """Raised when a raw direction cannot be mapped into the closed World vocabulary."""


def normalize_world_graph_relationship_direction(
    direction: str | None,
) -> WorldGraphRelationshipDirection:
    """Map raw/lower direction values onto the closed World Graph vocabulary.

    Unknown non-empty values fail closed — they are never coerced to ``related``
    and never passed through unchanged.
    """
    if direction is None:
        return "related"
    if not isinstance(direction, str):
        raise WorldGraphDirectionError(
            f"Unsupported World Graph relationship direction: {direction!r}"
        )
    stripped = direction.strip()
    if stripped == "":
        return "related"
    mapped = _WORLD_GRAPH_DIRECTION_ALIASES.get(stripped)
    if mapped is None:
        raise WorldGraphDirectionError(
            f"Unsupported World Graph relationship direction: {direction!r}"
        )
    return mapped

SEARCH_MAX_NODES = 12
SEARCH_MAX_RELATIONSHIPS = 24
SEARCH_MAX_ATTRIBUTES = 32
SEARCH_MAX_EVIDENCE = 32
SEARCH_MAX_SOURCE_ARTIFACTS = 24

_SEARCH_STOPWORDS = frozenset({
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "as", "is", "are", "was", "were", "be",
    "been", "being", "have", "has", "had", "do", "does", "did", "will",
    "would", "could", "should", "may", "might", "must", "shall", "can",
    "what", "which", "who", "whom", "whose", "where", "when", "why", "how",
    "i", "me", "my", "we", "our", "you", "your", "they", "their", "it",
    "its", "this", "that", "these", "those", "am", "about", "into", "through",
    "during", "before", "after", "above", "below", "between", "under", "again",
    "further", "then", "once", "here", "there", "all", "each", "few", "more",
    "most", "other", "some", "such", "no", "nor", "not", "only", "own", "same",
    "so", "than", "too", "very", "just", "also", "now",
})


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
    """Temporal focus for ranking/anchoring — not a visibility wall.

    When ``kind`` is ``session``, ``session_id`` is required. ``campaign_id``
    qualifies the session so ``session-3`` cannot ambiguously match C1 and C2.
    When omitted, callers should treat the request's narrative ``campaign_id``
    as the effective focus campaign (backward-compatible wire).
    """

    kind: FocusKind = "none"
    session_id: str | None = None
    campaign_id: str | None = None

    @model_validator(mode="after")
    def _validate_session_id(self) -> WorldGraphProjectionFocus:
        if self.kind == "session" and not self.session_id:
            raise ValueError("session_id is required when focus.kind is session")
        if self.kind == "none":
            if self.session_id is not None:
                raise ValueError("session_id must be null when focus.kind is none")
            if self.campaign_id is not None:
                raise ValueError("campaign_id must be null when focus.kind is none")
        return self


class WorldGraphProjectionRequest(_ProjectionModel):
    schema_: Literal["dmb_world_graph_projection_request_v1"] = Field(alias="schema")
    world_id: str
    campaign_id: str
    focus: WorldGraphProjectionFocus = Field(default_factory=WorldGraphProjectionFocus)
    admissibility: AdmissibilityPolicy = "gm"
    revision_pin: str | None = None
    query_text: str | None = None
    # campaign: narrative campaign only (+ world-owned null).
    # world: all campaign scopes in the same world (GM cross-campaign lens).
    scope_mode: ScopeMode = "campaign"


class WorldGraphProjectionSnapshot(_ProjectionModel):
    world_id: str
    campaign_id: str
    revision_id: str
    head_revision_id: str
    is_head: bool
    focus: WorldGraphProjectionFocus
    admissibility: AdmissibilityPolicy
    scope_mode: ScopeMode = "campaign"


class WorldGraphProjectionSummary(_ProjectionModel):
    node_count: int
    relationship_count: int
    attribute_count: int
    evidence_count: int
    source_artifact_count: int
    projection_truncated: bool = False


class WorldGraphProjectionTextHighlightSpan(_ProjectionModel):
    start: int
    end: int


class WorldGraphProjectionEvidenceBadge(_ProjectionModel):
    evidence_ref_id: str
    source_artifact_id: str
    source_domain: str
    evidence_role: str
    is_focus_session_evidence: bool = False
    can_open_source: bool = False
    can_highlight_span: bool = False
    label: str | None = None
    session_id: str | None = None
    source_span_ref_id: str | None = None


class WorldGraphProjectionAdjacencyCandidate(_ProjectionModel):
    edge_id: str
    node_id: str
    label: str
    kind: str
    predicate: str
    direction: WorldGraphRelationshipDirection
    anchored_to_focus_session: bool = False
    source_domains: list[str] = Field(default_factory=list)
    evidence_ref_ids: list[str] = Field(default_factory=list)
    edge_label: str | None = None
    session_ids: list[str] = Field(default_factory=list)
    # Effective campaign tenancy for this edge (null = world-universal).
    # Surfaced so world-lens relationship stamps can qualify sessions (C1 · S2).
    campaign_scope: str | None = None
    related_summary: str | None = None
    source_excerpt: str | None = None
    source_excerpt_is_full_paragraph: bool = False
    source_excerpt_highlight_spans: list[WorldGraphProjectionTextHighlightSpan] = Field(
        default_factory=list
    )


class WorldGraphProjectionSuggestedExpansion(WorldGraphProjectionAdjacencyCandidate):
    rank: int = 1
    rank_reason: str = "connected thread"


class WorldGraphProjectionNodeView(_ProjectionModel):
    node_id: str
    label: str
    kind: str
    role: str
    aliases: list[str] = Field(default_factory=list)
    source_domains: list[str] = Field(default_factory=list)
    summary: str | None = None
    anchored_to_focus_session: bool = False
    # Effective campaign tenancy (null = world-universal). Surfaced so
    # cross-campaign world-scope results remain attributable.
    campaign_scope: str | None = None
    evidence_badges: list[WorldGraphProjectionEvidenceBadge] = Field(default_factory=list)
    adjacency: list[WorldGraphProjectionAdjacencyCandidate] = Field(default_factory=list)
    suggested_expansions: list[WorldGraphProjectionSuggestedExpansion] = Field(
        default_factory=list
    )
    evidence_ref_ids: list[str] = Field(default_factory=list)
    source_artifact_ids: list[str] = Field(default_factory=list)


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
    direction: WorldGraphRelationshipDirection
    session_ids: list[str] = Field(default_factory=list)
    source_domains: list[str] = Field(default_factory=list)
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
    campaign_id: str | None = None
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
    snapshot: WorldGraphProjectionSnapshot
    revision_id: str
    query_text: str
    matched_node_ids: list[str] = Field(default_factory=list)
    match_reasons: dict[str, list[str]] = Field(default_factory=dict)
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


def _tokenize_query(query: str) -> list[str]:
    tokens = re.findall(r"[a-z0-9]+", _casefold(query))
    return [token for token in tokens if token not in _SEARCH_STOPWORDS and len(token) > 1]


def _token_variants(token: str) -> list[str]:
    variants = [token]
    if token.endswith("s") and len(token) > 3:
        variants.append(token[:-1])
    elif not token.endswith("s"):
        variants.append(f"{token}s")
    return variants


def _token_in_text(token: str, text: str) -> bool:
    if not text:
        return False
    for variant in _token_variants(token):
        if variant in text:
            return True
    return False


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


def _score_node_match(
    node: WorldGraphProjectionNodeView,
    query: str,
    tokens: list[str],
) -> tuple[int, list[str]]:
    query_cf = _casefold(query)
    reasons: list[str] = []
    score = 0

    if not query_cf and not tokens:
        return 0, reasons

    if query_cf and _casefold(node.node_id) == query_cf:
        return 1000, ["exact_node_id"]
    if query_cf and _casefold(node.label) == query_cf:
        return 900, ["exact_label"]
    for alias in node.aliases:
        if query_cf and _casefold(alias) == query_cf:
            return 850, ["exact_alias"]

    blob = _node_search_blob(node)
    if query_cf and query_cf in _casefold(node.label):
        score = max(score, 700)
        reasons.append("label_phrase")
    if query_cf and any(query_cf in _casefold(alias) for alias in node.aliases):
        score = max(score, 650)
        reasons.append("alias_phrase")
    if query_cf and (
        query_cf in _casefold(node.kind) or query_cf in _casefold(node.role)
    ):
        score = max(score, 500)
        reasons.append("kind_or_role_phrase")
    if query_cf and node.summary and query_cf in _casefold(node.summary):
        score = max(score, 300)
        reasons.append("summary_phrase")
    if query_cf and query_cf in blob:
        score = max(score, 200)
        reasons.append("node_blob_phrase")

    for token in tokens:
        if _token_in_text(token, _casefold(node.node_id)):
            score += 120
            reasons.append(f"token:{token}:node_id")
        if _token_in_text(token, _casefold(node.label)):
            score += 100
            reasons.append(f"token:{token}:label")
        if any(_token_in_text(token, _casefold(alias)) for alias in node.aliases):
            score += 90
            reasons.append(f"token:{token}:alias")
        if _token_in_text(token, _casefold(node.kind)):
            score += 80
            reasons.append(f"token:{token}:kind")
        if _token_in_text(token, _casefold(node.role)):
            score += 70
            reasons.append(f"token:{token}:role")
        if node.summary and _token_in_text(token, _casefold(node.summary)):
            score += 50
            reasons.append(f"token:{token}:summary")

    return score, sorted(set(reasons))


def _score_attribute_match(
    attribute: WorldGraphProjectionAttributeView,
    query: str,
    tokens: list[str],
) -> tuple[int, list[str]]:
    query_cf = _casefold(query)
    reasons: list[str] = []
    score = 0

    if query_cf and (
        _casefold(attribute.predicate) == query_cf or _casefold(attribute.label) == query_cf
    ):
        return 250, ["exact_attribute_field"]

    blob = _attribute_search_blob(attribute)
    if query_cf and query_cf in blob:
        score = max(score, 150)
        reasons.append("attribute_phrase")

    for token in tokens:
        if _token_in_text(token, blob):
            score += 60
            reasons.append(f"token:{token}:attribute")

    return score, sorted(set(reasons))


def rank_search_node_matches(
    nodes: list[WorldGraphProjectionNodeView],
    attributes: list[WorldGraphProjectionAttributeView],
    query_text: str,
) -> tuple[list[tuple[WorldGraphProjectionNodeView, int]], dict[str, list[str]]]:
    query = query_text.strip()
    tokens = _tokenize_query(query)
    scores: dict[str, int] = {}
    match_reasons: dict[str, list[str]] = {}
    node_by_id = {node.node_id: node for node in nodes}

    for node in nodes:
        score, reasons = _score_node_match(node, query, tokens)
        if score:
            scores[node.node_id] = max(scores.get(node.node_id, 0), score)
            match_reasons.setdefault(node.node_id, []).extend(reasons)

    for attribute in attributes:
        score, reasons = _score_attribute_match(attribute, query, tokens)
        if score:
            node_id = attribute.subject_node_id
            scores[node_id] = max(scores.get(node_id, 0), score)
            match_reasons.setdefault(node_id, []).extend(reasons)

    for node_id, reasons in match_reasons.items():
        match_reasons[node_id] = sorted(set(reasons))

    ranked = sorted(
        (
            (node_by_id[node_id], score)
            for node_id, score in scores.items()
            if node_id in node_by_id
        ),
        key=lambda item: (-item[1], item[0].node_id),
    )
    return ranked, match_reasons


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
    "WorldGraphDirectionError",
    "WorldGraphProjection",
    "WorldGraphProjectionAdjacencyCandidate",
    "WorldGraphProjectionAttributeView",
    "WorldGraphProjectionDiagnostic",
    "WorldGraphProjectionErrorResponse",
    "WorldGraphProjectionEvidenceBadge",
    "WorldGraphProjectionEvidenceView",
    "WorldGraphProjectionFocus",
    "WorldGraphProjectionNodeView",
    "WorldGraphProjectionRelationshipView",
    "WorldGraphProjectionRequest",
    "WorldGraphRelationshipDirection",
    "WorldGraphProjectionSnapshot",
    "WorldGraphProjectionSourceArtifactView",
    "WorldGraphProjectionSuggestedExpansion",
    "WorldGraphProjectionSummary",
    "WorldGraphProjectionTextHighlightSpan",
    "WorldGraphProjectionTrustBoundary",
    "WorldGraphQueryContext",
    "derive_attribute_text_value",
    "normalize_world_graph_relationship_direction",
    "rank_search_node_matches",
]
