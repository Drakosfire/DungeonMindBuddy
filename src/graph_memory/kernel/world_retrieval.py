"""Kernel World Graph retrieval + source-anchor admission (PR010A).

Every operation loads or derives from exactly one immutable World Graph
revision through the existing PR007A projection integrity path
(``_load_revision_context`` + ``build_projection_payload``), then performs
deterministic, graph-only search/lookup/traversal/evidence/anchor logic on
top of that already-integrity-verified projection and store. There is no
manifest discovery, corpus-index, repository search, arbitrary-path, vector,
or LLM fallback dependency anywhere in this module.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel

from graph_memory.evidence.assertion_support import DurableAssertionSupport
from graph_memory.kernel.contributions import (
    compute_contribution_source_payload_sha256,
    contribution_source_payload,
)
from graph_memory.kernel.world_graph import load_world_graph_revision
from graph_memory.kernel.world_initialization import (
    compute_initialization_attestation_digest,
    read_initialization_receipt,
)
from graph_memory.kernel.world_projection import (
    WorldGraphProjectionError,
    _active_supports_for_graph_object,
    _endpoint_relative_direction,
    _load_revision_context,
    _load_validated_contribution,
    _parse_support,
    build_projection_payload,
    resolve_projection_admissibility,
)
from graph_memory.union_supergraph.model import (
    UnionSupergraphStore,
)
from graph_memory.world_supergraph.storage import load_world_graph_revision_manifest
from graph_memory.projection.world_projection import (
    PROJECTION_REQUEST_SCHEMA,
    WorldGraphProjection,
    WorldGraphProjectionAttributeView,
    WorldGraphProjectionDiagnostic,
    WorldGraphProjectionFocus,
    WorldGraphProjectionNodeView,
    WorldGraphProjectionRelationshipView,
    WorldGraphProjectionRequest,
    rank_search_node_matches,
)
from graph_memory.retrieval.models import (
    RetrievalOperation,
    RetrievalOutcome,
    WorldGraphEvidenceRequest,
    WorldGraphNeighborhoodRequest,
    WorldGraphObjectRequest,
    WorldGraphRetrievalAttribute,
    WorldGraphRetrievalCoverage,
    WorldGraphRetrievalDiagnostic,
    WorldGraphRetrievalNode,
    WorldGraphRetrievalRelationship,
    WorldGraphRetrievalRequestContext,
    WorldGraphRetrievalResult,
    WorldGraphRetrievalSnapshot,
    WorldGraphRetrievalTrustBoundary,
    WorldGraphSearchRequest,
    WorldGraphSourceAnchor,
    WorldGraphSourceAnchorReadRequest,
    WorldGraphSourceAnchorReadResult,
    compute_source_anchor_id,
)
from graph_memory.retrieval.source_reader import (
    SourceReadError,
    SourceReadOutcome,
    parse_graph_data_uri,
    parse_heading_locator,
    parse_json_pointer_locator,
    parse_repo_uri,
    read_graph_data_json_pointer_anchor,
    read_repo_heading_anchor,
)
from graph_memory.union_supergraph.projection_identity import (
    build_union_projection_identity_context,
)

_ModelT = TypeVar("_ModelT", bound=BaseModel)

_UNAVAILABLE_PROJECTION_CODES = frozenset({"world_graph_unavailable", "revision_not_found"})
_SOURCE_READ_UNAVAILABLE_CODES = frozenset({"source_unavailable"})
_SEED_MATCH_SCORE = 1_000_000
_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")

# Mirrors ``graph_memory.projection.world_projection._SEARCH_STOPWORDS`` so the
# relationship/related-node ranking extension does not score noise words
# ("in", "the", "is", ...) as substring matches against short attribute text.
_STOPWORDS = frozenset({
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

_TRUST_CAN = [
    "Every returned node, relationship, attribute, and source anchor is admitted by one "
    "explicit World Graph revision plus the requested world/campaign/focus/admissibility context.",
    "Source anchors are exact-matched and revalidated against that context before any content "
    "is returned; no anchor from another revision or context resolves.",
    "Anchor derivation is deterministic: the same admissible input always produces the same "
    "anchor id and the same ordering.",
]
_TRUST_CANNOT = [
    "Source artifact prose is not independently fact-checked beyond digest/anchor verification.",
    "Quality or completeness of graph extraction is not audited by this contract.",
    "An omitted source is not proof that a fact is absent from the underlying prose.",
]


class WorldGraphRetrievalError(Exception):
    """Stable retrieval failure with an API-safe code and diagnostics."""

    def __init__(
        self,
        message: str,
        *,
        code: str,
        status_code: int,
        diagnostics: list[WorldGraphRetrievalDiagnostic] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code
        self.diagnostics = list(diagnostics or [])


@dataclass(frozen=True)
class _AnchorDerivation:
    anchor: WorldGraphSourceAnchor
    locator: str | None
    source_artifact_uri: str
    contribution_id: str | None


def _default_repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _trust_boundary() -> WorldGraphRetrievalTrustBoundary:
    return WorldGraphRetrievalTrustBoundary(can_trust=list(_TRUST_CAN), cannot_trust=list(_TRUST_CANNOT))


def _revalidate(model_cls: type[_ModelT], request: _ModelT) -> _ModelT:
    try:
        return model_cls.model_validate(request.model_dump(mode="json", by_alias=True))
    except Exception as exc:
        raise WorldGraphRetrievalError(
            f"{model_cls.__name__} is invalid.",
            code="invalid_request",
            status_code=422,
            diagnostics=[
                WorldGraphRetrievalDiagnostic(
                    code="invalid_request", message=str(exc), severity="error"
                )
            ],
        ) from exc


_CONTEXT_FIELD_NAMES = frozenset(
    {"schema_", "world_id", "campaign_id", "focus", "admissibility", "revision_pin"}
)


def _request_summary(request: WorldGraphRetrievalRequestContext) -> dict[str, Any]:
    return request.model_dump(mode="json", by_alias=True, exclude=_CONTEXT_FIELD_NAMES)


def _convert_projection_diagnostic(
    diagnostic: WorldGraphProjectionDiagnostic,
) -> WorldGraphRetrievalDiagnostic:
    return WorldGraphRetrievalDiagnostic(
        code=diagnostic.code, message=diagnostic.message, severity=diagnostic.severity
    )


def _map_projection_error(exc: WorldGraphProjectionError) -> WorldGraphRetrievalError:
    return WorldGraphRetrievalError(
        str(exc),
        code=exc.code,
        status_code=exc.status_code,
        diagnostics=[_convert_projection_diagnostic(d) for d in exc.diagnostics],
    )


def _load_projection_and_store(
    root: Path,
    *,
    world_id: str,
    campaign_id: str,
    focus: WorldGraphProjectionFocus,
    admissibility: str,
    revision_pin: str | None,
    scope_mode: str = "campaign",
) -> tuple[WorldGraphProjection, UnionSupergraphStore] | None:
    """Load one revision-pinned projection + its store through the PR007A path.

    Returns ``None`` when the request is well-formed but the world/head/
    revision cannot be opened (retrieval outcome ``unavailable``). Raises
    ``WorldGraphRetrievalError`` for invalid-request or integrity failures.
    """
    proj_request = WorldGraphProjectionRequest(
        schema=PROJECTION_REQUEST_SCHEMA,
        world_id=world_id,
        campaign_id=campaign_id,
        focus=focus,
        admissibility=admissibility,
        revision_pin=revision_pin,
        scope_mode=scope_mode,  # type: ignore[arg-type]
    )
    try:
        resolve_projection_admissibility(admissibility)
        revision_id, head_revision_id, store = _load_revision_context(root, proj_request)
        projection = build_projection_payload(
            request=proj_request,
            revision_id=revision_id,
            head_revision_id=head_revision_id,
            store=store,
            root=root,
            world_id=world_id,
        )
    except WorldGraphProjectionError as exc:
        if exc.code in _UNAVAILABLE_PROJECTION_CODES:
            return None
        raise _map_projection_error(exc) from exc
    return projection, store


def _snapshot_from_projection(projection: WorldGraphProjection) -> WorldGraphRetrievalSnapshot:
    snapshot = projection.snapshot
    return WorldGraphRetrievalSnapshot(
        world_id=snapshot.world_id,
        campaign_id=snapshot.campaign_id,
        revision_id=snapshot.revision_id,
        head_revision_id=snapshot.head_revision_id,
        is_head=snapshot.is_head,
        focus=snapshot.focus,
        admissibility=snapshot.admissibility,
        scope_mode=getattr(snapshot, "scope_mode", "campaign") or "campaign",
    )


def _unavailable_result(
    operation: RetrievalOperation,
    request: WorldGraphRetrievalRequestContext,
    *,
    requested_node_id: str | None = None,
) -> WorldGraphRetrievalResult:
    return WorldGraphRetrievalResult(
        operation=operation,
        outcome="unavailable",
        snapshot=None,
        request_summary=_request_summary(request),
        requested_node_id=requested_node_id,
        trust_boundary=_trust_boundary(),
        diagnostics=[
            WorldGraphRetrievalDiagnostic(
                code="world_graph_unavailable",
                message="The requested world graph or revision could not be opened.",
                severity="warning",
            )
        ],
    )


def _convert_node(node: WorldGraphProjectionNodeView) -> WorldGraphRetrievalNode:
    return WorldGraphRetrievalNode(
        node_id=node.node_id,
        label=node.label,
        kind=node.kind,
        role=node.role,
        aliases=list(node.aliases),
        source_domains=list(node.source_domains),
        summary=node.summary,
        anchored_to_focus_session=node.anchored_to_focus_session,
        evidence_ref_ids=list(node.evidence_ref_ids),
        source_artifact_ids=list(node.source_artifact_ids),
    )


def _convert_relationship(
    relationship: WorldGraphProjectionRelationshipView,
    *,
    direction_from_node_id: str | None = None,
) -> WorldGraphRetrievalRelationship:
    direction = (
        _endpoint_relative_direction(relationship, direction_from_node_id)
        if direction_from_node_id is not None
        else relationship.direction
    )
    return WorldGraphRetrievalRelationship(
        edge_id=relationship.edge_id,
        source_node_id=relationship.source_node_id,
        target_node_id=relationship.target_node_id,
        predicate=relationship.predicate,
        label=relationship.label,
        direction=direction,
        direction_from_node_id=direction_from_node_id,
        session_ids=list(relationship.session_ids),
        source_domains=list(relationship.source_domains),
        visibility=relationship.visibility,
        campaign_scope=relationship.campaign_scope,
        epistemic_kind=relationship.epistemic_kind,
        evidence_ref_ids=list(relationship.evidence_ref_ids),
        source_artifact_ids=list(relationship.source_artifact_ids),
        active_contribution_ids=list(relationship.active_contribution_ids),
    )


def _convert_attribute(attribute: WorldGraphProjectionAttributeView) -> WorldGraphRetrievalAttribute:
    return WorldGraphRetrievalAttribute(
        assertion_id=attribute.assertion_id,
        subject_node_id=attribute.subject_node_id,
        predicate=attribute.predicate,
        label=attribute.label,
        value=dict(attribute.value),
        text_value=attribute.text_value,
        epistemic_kind=attribute.epistemic_kind,
        visibility=attribute.visibility,
        campaign_scope=attribute.campaign_scope,
        temporal_scope=(
            dict(attribute.temporal_scope) if attribute.temporal_scope is not None else None
        ),
        support_state=attribute.support_state,
        active_contribution_ids=list(attribute.active_contribution_ids),
        evidence_ref_ids=list(attribute.evidence_ref_ids),
        source_artifact_ids=list(attribute.source_artifact_ids),
    )


def _casefold(value: str | None) -> str:
    return (value or "").casefold()


def _tokenize(text: str) -> list[str]:
    return [
        token
        for token in _TOKEN_PATTERN.findall(_casefold(text))
        if len(token) > 1 and token not in _STOPWORDS
    ]


def _token_in_text(token: str, text: str) -> bool:
    if not text:
        return False
    if token in text:
        return True
    if token.endswith("s") and len(token) > 3 and token[:-1] in text:
        return True
    if not token.endswith("s") and f"{token}s" in text:
        return True
    return False


def _extend_scores_with_relationships(
    nodes: list[WorldGraphProjectionNodeView],
    relationships: list[WorldGraphProjectionRelationshipView],
    query_text: str,
    scores: dict[str, int],
    match_reasons: dict[str, list[str]],
) -> None:
    """Boost node scores from relationship predicate/label and related-node text.

    A query may only match through the *other* endpoint's display text (e.g.
    searching "North Gate" should also surface a threat node connected to a
    "North Gate" node by a relevant relationship), so both endpoints of every
    relationship are considered independently.
    """
    query_cf = _casefold(query_text)
    tokens = _tokenize(query_text)
    if not query_cf and not tokens:
        return
    label_by_id = {node.node_id: node.label for node in nodes}
    for relationship in relationships:
        source_label = label_by_id.get(relationship.source_node_id, "")
        target_label = label_by_id.get(relationship.target_node_id, "")
        for endpoint_id, related_label in (
            (relationship.source_node_id, target_label),
            (relationship.target_node_id, source_label),
        ):
            if endpoint_id not in label_by_id:
                continue
            blob = " ".join(
                filter(None, [relationship.predicate, relationship.label, related_label])
            ).casefold()
            score = 0
            reasons: list[str] = []
            if query_cf and query_cf in blob:
                score = max(score, 160)
                reasons.append("relationship_or_related_node_phrase")
            for token in tokens:
                if _token_in_text(token, blob):
                    score += 45
                    reasons.append(f"token:{token}:relationship_or_related_node")
            if score:
                scores[endpoint_id] = max(scores.get(endpoint_id, 0), score)
                match_reasons.setdefault(endpoint_id, []).extend(reasons)


def _rank_search_matches(
    nodes: list[WorldGraphProjectionNodeView],
    attributes: list[WorldGraphProjectionAttributeView],
    relationships: list[WorldGraphProjectionRelationshipView],
    query_text: str,
    seed_node_ids: list[str],
) -> tuple[list[tuple[WorldGraphProjectionNodeView, int]], dict[str, list[str]], list[str]]:
    ranked, match_reasons = rank_search_node_matches(nodes, attributes, query_text)
    scores = {node.node_id: score for node, score in ranked}
    _extend_scores_with_relationships(nodes, relationships, query_text, scores, match_reasons)

    node_by_id = {node.node_id: node for node in nodes}
    missing_seed_ids = sorted({seed_id for seed_id in seed_node_ids if seed_id not in node_by_id})
    for seed_id in seed_node_ids:
        if seed_id in node_by_id:
            scores[seed_id] = max(scores.get(seed_id, 0), _SEED_MATCH_SCORE)
            match_reasons.setdefault(seed_id, []).append("exact_seed")

    for node_id, reasons in match_reasons.items():
        match_reasons[node_id] = sorted(set(reasons))

    ranked_final = sorted(
        (
            (node_by_id[node_id], score)
            for node_id, score in scores.items()
            if node_id in node_by_id
        ),
        key=lambda item: (-item[1], item[0].node_id),
    )
    return ranked_final, match_reasons, missing_seed_ids


def _truncated_fields(**flags: bool) -> list[str]:
    return sorted(name for name, flag in flags.items() if flag)


def _determine_outcome(
    *,
    truncated: bool,
    partial: bool,
    has_content: bool,
    denied: bool = False,
) -> RetrievalOutcome:
    if denied:
        return "denied"
    if truncated:
        return "truncated"
    if partial and has_content:
        return "partial"
    if has_content:
        return "enough"
    return "empty"


def _outcome_diagnostics(coverage: WorldGraphRetrievalCoverage) -> list[WorldGraphRetrievalDiagnostic]:
    diagnostics: list[WorldGraphRetrievalDiagnostic] = []
    if coverage.missing_seed_node_ids:
        diagnostics.append(
            WorldGraphRetrievalDiagnostic(
                code="missing_seed_node_ids",
                message=(
                    "Seed node ids not found in this revision: "
                    f"{', '.join(coverage.missing_seed_node_ids)}."
                ),
                severity="warning",
            )
        )
    if coverage.truncated_fields:
        diagnostics.append(
            WorldGraphRetrievalDiagnostic(
                code="result_truncated",
                message=f"Result truncated for: {', '.join(coverage.truncated_fields)}.",
                severity="warning",
            )
        )
    if coverage.missing_evidence_ref_ids:
        diagnostics.append(
            WorldGraphRetrievalDiagnostic(
                code="missing_evidence_ref_ids",
                message=(
                    "Selected graph data is missing admitted evidence refs: "
                    f"{', '.join(coverage.missing_evidence_ref_ids)}."
                ),
                severity="warning",
            )
        )
    if coverage.unreadable_anchor_ids:
        diagnostics.append(
            WorldGraphRetrievalDiagnostic(
                code="unreadable_source_anchors",
                message=f"{len(coverage.unreadable_anchor_ids)} source anchor(s) are not readable.",
                severity="warning",
            )
        )
    return diagnostics


def _selection_anchor_gaps(
    *,
    source_anchors: list[WorldGraphSourceAnchor],
    selected_graph_object_ids: set[str],
    selected_assertion_ids: set[str],
    nodes: list[WorldGraphProjectionNodeView] | list[WorldGraphRetrievalNode] | None = None,
    relationships: (
        list[WorldGraphProjectionRelationshipView] | list[WorldGraphRetrievalRelationship] | None
    ) = None,
    attributes: (
        list[WorldGraphProjectionAttributeView] | list[WorldGraphRetrievalAttribute] | None
    ) = None,
) -> tuple[list[str], list[str], list[WorldGraphRetrievalDiagnostic]]:
    """Identify selected objects/assertions that have no admitted source anchors.

    Returns ``(missing_evidence_ref_ids, gap_ids, extra_diagnostics)``. A gap
    with no evidence refs still counts as partial via ``gap_ids``.
    """
    covered: set[str] = set()
    for anchor in source_anchors:
        covered.update(anchor.supporting_graph_object_ids)
        covered.update(anchor.supporting_assertion_ids)

    selected = set(selected_graph_object_ids) | set(selected_assertion_ids)
    gap_ids = sorted(selected - covered)

    missing_refs: list[str] = []
    node_by_id = {item.node_id: item for item in nodes or []}
    relationship_by_id = {item.edge_id: item for item in relationships or []}
    attribute_by_id = {item.assertion_id: item for item in attributes or []}
    for gap_id in gap_ids:
        if gap_id in node_by_id:
            missing_refs.extend(list(node_by_id[gap_id].evidence_ref_ids or []))
        elif gap_id in relationship_by_id:
            missing_refs.extend(list(relationship_by_id[gap_id].evidence_ref_ids or []))
        elif gap_id in attribute_by_id:
            missing_refs.extend(list(attribute_by_id[gap_id].evidence_ref_ids or []))

    extra: list[WorldGraphRetrievalDiagnostic] = []
    if gap_ids and not missing_refs:
        extra.append(
            WorldGraphRetrievalDiagnostic(
                code="missing_source_anchors",
                message=(
                    "Selected graph object(s) lack admitted source anchors: "
                    f"{', '.join(gap_ids)}."
                ),
                severity="warning",
            )
        )
    return sorted(set(missing_refs)), gap_ids, extra


def _raise_source_integrity_error(message: str) -> None:
    raise WorldGraphRetrievalError(
        message,
        code="source_integrity_error",
        status_code=409,
        diagnostics=[
            WorldGraphRetrievalDiagnostic(
                code="source_integrity_error",
                message=message,
                severity="error",
            )
        ],
    )


def _revision_is_ancestor(
    root: Path,
    world_id: str,
    *,
    ancestor_revision_id: str,
    descendant_revision_id: str,
) -> bool:
    if ancestor_revision_id == descendant_revision_id:
        return True
    seen: set[str] = set()
    current: str | None = descendant_revision_id
    while current is not None:
        if current in seen:
            return False
        seen.add(current)
        if current == ancestor_revision_id:
            return True
        try:
            revision = load_world_graph_revision_manifest(root, world_id, current)
        except Exception:
            return False
        current = revision.parent_revision_id
    return False


def _validate_initialization_receipt_for_graph_data(
    *,
    root: Path,
    world_id: str,
    campaign_id: str,
    store: UnionSupergraphStore,
    revision_id: str,
) -> None:
    """Defensively cross-check a receipt against immutable revision-bound digests."""
    try:
        receipt = read_initialization_receipt(root, world_id)
    except Exception:
        _raise_source_integrity_error(
            "Initialization receipt is unreadable or corrupt."
        )
    if receipt is None:
        return

    if receipt.world_id != world_id or receipt.campaign_id != campaign_id:
        _raise_source_integrity_error(
            "Initialization receipt world or campaign binding mismatch."
        )
    if not receipt.plan_binding_verified:
        _raise_source_integrity_error(
            "Initialization receipt plan binding is not verified."
        )
    if not receipt.world_integrity_ok:
        _raise_source_integrity_error(
            "Initialization receipt world integrity is not confirmed."
        )
    if not receipt.contribution_integrity_ok:
        _raise_source_integrity_error(
            "Initialization receipt contribution integrity is not confirmed."
        )

    if store.initialization_plan_digest is None:
        _raise_source_integrity_error(
            "Revision-bound initialization plan digest is missing."
        )
    if receipt.plan_digest != store.initialization_plan_digest:
        _raise_source_integrity_error(
            "Initialization receipt plan digest disagrees with revision state."
        )

    if store.initialization_attestation_digest is None:
        _raise_source_integrity_error(
            "Revision-bound initialization attestation digest is missing."
        )
    attestation_digest = compute_initialization_attestation_digest(
        receipt.approval_attestation
    )
    if attestation_digest != store.initialization_attestation_digest:
        _raise_source_integrity_error(
            "Initialization receipt attestation digest disagrees with revision state."
        )

    # Initialization authority binds contribution IDs (plus plan/attestation
    # digests above). Per-contribution full payload digests live on the receipt
    # / plan for init-time verification; revision-bound graph-data reads use
    # lifecycle-neutral ``contribution_source_payload_sha256`` instead.
    expected_contribution_ids = list(store.initialization_contribution_ids)
    actual_contribution_ids = [
        item.contribution_id for item in receipt.ordered_contributions
    ]
    if (
        not expected_contribution_ids
        or actual_contribution_ids != expected_contribution_ids
    ):
        _raise_source_integrity_error(
            "Initialization receipt contribution list disagrees with revision state."
        )

    try:
        initial_head_store = load_world_graph_revision(
            root, world_id, receipt.initial_head_revision_id
        )
    except Exception:
        _raise_source_integrity_error(
            "Initialization receipt initial head cannot be loaded."
        )
    if len(initial_head_store.nodes) != receipt.node_count:
        _raise_source_integrity_error(
            "Initialization receipt node count disagrees with initial head."
        )
    if len(initial_head_store.edges) != receipt.edge_count:
        _raise_source_integrity_error(
            "Initialization receipt edge count disagrees with initial head."
        )
    if len(initial_head_store.evidence) != receipt.evidence_count:
        _raise_source_integrity_error(
            "Initialization receipt evidence count disagrees with initial head."
        )
    if len(initial_head_store.source_artifacts) != receipt.source_artifact_count:
        _raise_source_integrity_error(
            "Initialization receipt source-artifact count disagrees with initial head."
        )
    if len(initial_head_store.assertion_support) != receipt.assertion_support_count:
        _raise_source_integrity_error(
            "Initialization receipt assertion-support count disagrees with "
            "initial head."
        )

    if not _revision_is_ancestor(
        root,
        world_id,
        ancestor_revision_id=receipt.baseline_revision_id,
        descendant_revision_id=revision_id,
    ):
        _raise_source_integrity_error(
            "Selected revision is not a descendant of the initialization baseline."
        )
    if not _revision_is_ancestor(
        root,
        world_id,
        ancestor_revision_id=receipt.initial_head_revision_id,
        descendant_revision_id=revision_id,
    ):
        _raise_source_integrity_error(
            "Selected revision is not a descendant of the initialization initial head."
        )


def _graph_data_contribution_digest_authority(
    store: UnionSupergraphStore,
    contribution_id: str | None,
) -> str | None:
    if not contribution_id:
        return None
    digest = store.contribution_source_payload_sha256.get(contribution_id)
    if isinstance(digest, str) and re.fullmatch(r"[0-9a-fA-F]{64}", digest):
        return digest.lower()
    return None


def _verify_graph_data_contribution_digest(
    *,
    store: UnionSupergraphStore,
    contribution_id: str,
    contribution: Any,
) -> None:
    expected = _graph_data_contribution_digest_authority(store, contribution_id)
    if expected is None:
        _raise_source_integrity_error(
            "No revision-bound contribution source digest is available for this "
            "graph-data:// source."
        )
    actual = compute_contribution_source_payload_sha256(contribution)
    if actual != expected:
        _raise_source_integrity_error(
            "graph-data:// contribution content does not match the admitted digest."
        )


def _admitted_source_content_sha256(source_artifact: Any) -> str | None:
    raw = getattr(source_artifact, "content_sha256", None)
    if raw is None:
        extra = getattr(source_artifact, "model_extra", None) or {}
        raw = extra.get("content_sha256")
    if isinstance(raw, str) and re.fullmatch(r"[0-9a-fA-F]{64}", raw):
        return raw.lower()
    return None


def _classify_locator(
    uri: str,
    locator: str | None,
    *,
    store: UnionSupergraphStore | None = None,
    contribution_id: str | None = None,
    admitted_content_sha256: str | None = None,
    source_domain: str | None = None,
    source_span_ref_id: str | None = None,
    session_id: str | None = None,
) -> tuple[str, bool]:
    cleaned_span = str(source_span_ref_id or "").strip() or None
    domain = str(source_domain or "")
    # Worldbuilding SourceSpan identity is an admitted provenance shape.
    # Prefer explicit S; never treat arbitrary contribution/... locators as spans.
    if domain == "worldbuilding" and cleaned_span:
        if session_id is None and locator is not None:
            cleaned_locator = str(locator).strip()
            if cleaned_locator and cleaned_locator != cleaned_span:
                # Locator disagrees with explicit S — do not invent span authority.
                return "unsupported", False
        # Same spirit as heading: require a revision-bound admitted digest.
        if admitted_content_sha256 is None:
            return "source_span", False
        return "source_span", True
    if locator is None:
        return "unsupported", False
    if parse_repo_uri(uri) is not None and parse_heading_locator(locator) is not None:
        # Forward-only: repo:// reads require a revision-bound admitted digest.
        if admitted_content_sha256 is None:
            return "heading", False
        return "heading", True
    if parse_graph_data_uri(uri) is not None and parse_json_pointer_locator(locator) is not None:
        if store is None or _graph_data_contribution_digest_authority(
            store, contribution_id
        ) is None:
            return "json_pointer", False
        return "json_pointer", True
    return "unsupported", False


def _display_label(
    locator: str | None,
    *,
    locator_kind: str | None = None,
    source_span_ref_id: str | None = None,
) -> str | None:
    if locator_kind == "source_span":
        span = str(source_span_ref_id or "").strip()
        if not span:
            return "source span"
        if len(span) <= 20:
            return f"source span ({span})"
        return f"source span (…{span[-12:]})"
    if locator is None:
        return None
    heading_text = parse_heading_locator(locator)
    if heading_text:
        return heading_text
    pointer = parse_json_pointer_locator(locator)
    if pointer:
        return pointer
    return None


def _projection_admitted_anchor_derivations(
    *,
    store: UnionSupergraphStore,
    projection: WorldGraphProjection,
) -> list[_AnchorDerivation]:
    graph_object_ids = (
        {node.node_id for node in projection.nodes}
        | {relationship.edge_id for relationship in projection.relationships}
    )
    assertion_ids = {attribute.assertion_id for attribute in projection.attributes}

    supports: list[DurableAssertionSupport] = []
    seen_assertion_ids: set[str] = set()
    for graph_object_id in sorted(graph_object_ids):
        for support in _active_supports_for_graph_object(store, graph_object_id):
            if support.assertion_id in seen_assertion_ids:
                continue
            seen_assertion_ids.add(support.assertion_id)
            supports.append(support)
    if assertion_ids:
        for raw_support in store.assertion_support.values():
            support = _parse_support(raw_support)
            if support.assertion_id not in assertion_ids:
                continue
            if support.support_state != "supported" or not support.active_contribution_ids:
                continue
            if support.assertion_id in seen_assertion_ids:
                continue
            seen_assertion_ids.add(support.assertion_id)
            supports.append(support)

    return _anchor_derivations_for_supports(
        store=store, projection=projection, supports=supports
    )


def _anchor_derivations_for_supports(
    *,
    store: UnionSupergraphStore,
    projection: WorldGraphProjection,
    supports: list[DurableAssertionSupport],
) -> list[_AnchorDerivation]:
    snapshot = projection.snapshot
    derivations: dict[str, _AnchorDerivation] = {}

    for support in supports:
        for contribution_id in support.active_contribution_ids:
            evidence_ref_ids = support.per_contribution_evidence_ref_ids.get(contribution_id, [])
            for evidence_ref_id in evidence_ref_ids:
                evidence = store.evidence.get(evidence_ref_id)
                if evidence is None:
                    continue
                source_artifact = store.source_artifacts.get(evidence.source_artifact_id)
                if source_artifact is None:
                    continue
                locator = evidence.locator
                source_span_ref_id = (
                    str(evidence.source_span_ref_id).strip()
                    if evidence.source_span_ref_id
                    else None
                ) or None
                # Prefer explicit S for stable identity when present (sessionless
                # worldbuilding already used S as locator after #567).
                locator_identity = source_span_ref_id or locator or ""
                anchor_id = compute_source_anchor_id(
                    world_id=snapshot.world_id,
                    campaign_id=snapshot.campaign_id,
                    focus=snapshot.focus,
                    admissibility=snapshot.admissibility,
                    revision_id=snapshot.revision_id,
                    evidence_ref_id=evidence_ref_id,
                    source_artifact_id=evidence.source_artifact_id,
                    locator_identity=locator_identity,
                )
                locator_kind, readable = _classify_locator(
                    source_artifact.uri,
                    locator,
                    store=store,
                    contribution_id=contribution_id,
                    admitted_content_sha256=_admitted_source_content_sha256(
                        source_artifact
                    ),
                    source_domain=str(evidence.source_domain),
                    source_span_ref_id=source_span_ref_id,
                    session_id=evidence.session_id,
                )
                existing = derivations.get(anchor_id)
                if existing is not None:
                    merged_object_ids = set(existing.anchor.supporting_graph_object_ids)
                    if support.graph_object_id:
                        merged_object_ids.add(support.graph_object_id)
                    merged_assertion_ids = set(existing.anchor.supporting_assertion_ids)
                    merged_assertion_ids.add(support.assertion_id)
                    derivations[anchor_id] = _AnchorDerivation(
                        anchor=existing.anchor.model_copy(
                            update={
                                "supporting_graph_object_ids": sorted(merged_object_ids),
                                "supporting_assertion_ids": sorted(merged_assertion_ids),
                            }
                        ),
                        locator=existing.locator,
                        source_artifact_uri=existing.source_artifact_uri,
                        contribution_id=existing.contribution_id,
                    )
                    continue
                anchor = WorldGraphSourceAnchor(
                    anchor_id=anchor_id,
                    revision_id=snapshot.revision_id,
                    evidence_ref_id=evidence_ref_id,
                    source_artifact_id=evidence.source_artifact_id,
                    source_domain=str(evidence.source_domain),
                    session_id=evidence.session_id,
                    source_span_ref_id=source_span_ref_id,
                    supporting_graph_object_ids=(
                        [support.graph_object_id] if support.graph_object_id else []
                    ),
                    supporting_assertion_ids=[support.assertion_id],
                    readable=readable,
                    locator_kind=locator_kind,  # type: ignore[arg-type]
                    display_label=_display_label(
                        locator,
                        locator_kind=locator_kind,
                        source_span_ref_id=source_span_ref_id,
                    ),
                )
                derivations[anchor_id] = _AnchorDerivation(
                    anchor=anchor,
                    locator=locator,
                    source_artifact_uri=source_artifact.uri,
                    contribution_id=contribution_id,
                )
    return sorted(derivations.values(), key=lambda item: item.anchor.anchor_id)


def _source_anchors_for_targets(
    *,
    store: UnionSupergraphStore,
    projection: WorldGraphProjection,
    graph_object_ids: set[str],
    assertion_ids: set[str],
    max_source_anchors: int,
) -> tuple[list[WorldGraphSourceAnchor], bool, list[str], list[WorldGraphSourceAnchor]]:
    supports: list[DurableAssertionSupport] = []
    seen_assertion_ids: set[str] = set()
    for graph_object_id in sorted(graph_object_ids):
        for support in _active_supports_for_graph_object(store, graph_object_id):
            if support.assertion_id in seen_assertion_ids:
                continue
            seen_assertion_ids.add(support.assertion_id)
            supports.append(support)
    if assertion_ids:
        for raw_support in store.assertion_support.values():
            support = _parse_support(raw_support)
            if support.assertion_id not in assertion_ids:
                continue
            if support.support_state != "supported" or not support.active_contribution_ids:
                continue
            if support.assertion_id in seen_assertion_ids:
                continue
            seen_assertion_ids.add(support.assertion_id)
            supports.append(support)

    derivations = _anchor_derivations_for_supports(
        store=store, projection=projection, supports=supports
    )
    anchors = [item.anchor for item in derivations]
    truncated = len(anchors) > max_source_anchors
    bounded = anchors[:max_source_anchors]
    unreadable_ids = [anchor.anchor_id for anchor in bounded if not anchor.readable]
    return bounded, truncated, unreadable_ids, anchors


def search_campaign_graph(
    root: Path, request: WorldGraphSearchRequest
) -> WorldGraphRetrievalResult:
    request = _revalidate(WorldGraphSearchRequest, request)
    loaded = _load_projection_and_store(
        root,
        world_id=request.world_id,
        campaign_id=request.campaign_id,
        focus=request.focus.to_projection_focus(),
        admissibility=request.admissibility,
        revision_pin=request.revision_pin,
        scope_mode=request.scope_mode,
    )
    if loaded is None:
        return _unavailable_result("search", request)
    projection, store = loaded

    ranked, match_reasons, missing_seed_ids = _rank_search_matches(
        projection.nodes,
        projection.attributes,
        projection.relationships,
        request.query_text,
        request.seed_node_ids,
    )

    node_cap = request.bounds.max_nodes
    node_truncated = len(ranked) > node_cap
    selected_nodes = [node for node, _score in ranked[:node_cap]]
    selected_node_ids = {node.node_id for node in selected_nodes}
    matched_node_ids = [node.node_id for node in selected_nodes]

    rel_cap = request.bounds.max_relationships
    candidate_relationships = [
        relationship
        for relationship in projection.relationships
        if relationship.source_node_id in selected_node_ids
        or relationship.target_node_id in selected_node_ids
    ]
    relationship_truncated = len(candidate_relationships) > rel_cap
    selected_relationships = candidate_relationships[:rel_cap]

    attr_cap = request.bounds.max_attributes
    candidate_attributes = [
        attribute
        for attribute in projection.attributes
        if attribute.subject_node_id in selected_node_ids
    ]
    attribute_truncated = len(candidate_attributes) > attr_cap
    selected_attributes = candidate_attributes[:attr_cap]

    selected_edge_ids = {r.edge_id for r in selected_relationships}
    selected_assertion_ids = {a.assertion_id for a in selected_attributes}
    source_anchors, anchor_truncated, unreadable_ids, admitted_source_anchors = (
        _source_anchors_for_targets(
        store=store,
        projection=projection,
        graph_object_ids=selected_node_ids | selected_edge_ids,
        assertion_ids=selected_assertion_ids,
        max_source_anchors=request.bounds.max_source_anchors,
        )
    )
    missing_evidence_ref_ids, gap_ids, gap_diagnostics = _selection_anchor_gaps(
        source_anchors=admitted_source_anchors,
        selected_graph_object_ids=selected_node_ids | selected_edge_ids,
        selected_assertion_ids=selected_assertion_ids,
        nodes=selected_nodes,
        relationships=selected_relationships,
        attributes=selected_attributes,
    )

    coverage = WorldGraphRetrievalCoverage(
        requested_seed_node_ids=list(request.seed_node_ids),
        missing_seed_node_ids=missing_seed_ids,
        missing_evidence_ref_ids=missing_evidence_ref_ids,
        unreadable_anchor_ids=unreadable_ids,
        truncated_fields=_truncated_fields(
            nodes=node_truncated,
            relationships=relationship_truncated,
            attributes=attribute_truncated,
            source_anchors=anchor_truncated,
        ),
    )
    outcome = _determine_outcome(
        truncated=bool(coverage.truncated_fields),
        partial=(
            bool(missing_seed_ids)
            or bool(unreadable_ids)
            or bool(gap_ids)
        ),
        has_content=bool(selected_nodes),
    )

    return WorldGraphRetrievalResult(
        operation="search",
        outcome=outcome,
        snapshot=_snapshot_from_projection(projection),
        request_summary=_request_summary(request),
        matched_node_ids=matched_node_ids,
        match_reasons={
            node_id: match_reasons[node_id]
            for node_id in matched_node_ids
            if node_id in match_reasons
        },
        nodes=[_convert_node(node) for node in selected_nodes],
        relationships=[_convert_relationship(r) for r in selected_relationships],
        attributes=[_convert_attribute(a) for a in selected_attributes],
        source_anchors=source_anchors,
        coverage=coverage,
        trust_boundary=_trust_boundary(),
        diagnostics=_outcome_diagnostics(coverage) + gap_diagnostics,
    )


def get_campaign_object(
    root: Path, request: WorldGraphObjectRequest
) -> WorldGraphRetrievalResult:
    request = _revalidate(WorldGraphObjectRequest, request)
    loaded = _load_projection_and_store(
        root,
        world_id=request.world_id,
        campaign_id=request.campaign_id,
        focus=request.focus.to_projection_focus(),
        admissibility=request.admissibility,
        revision_pin=request.revision_pin,
        scope_mode=request.scope_mode,
    )
    if loaded is None:
        return _unavailable_result("object", request, requested_node_id=request.node_id)
    projection, store = loaded

    identity_context = build_union_projection_identity_context(store)
    resolved_node_id = request.node_id
    diagnostics: list[WorldGraphRetrievalDiagnostic] = []
    survivor_id = identity_context.merged_away_to_survivor.get(request.node_id)
    if survivor_id is not None:
        resolved_node_id = survivor_id
        diagnostics.append(
            WorldGraphRetrievalDiagnostic(
                code="active_identity_redirect",
                message=(
                    f"Requested node id {request.node_id!r} has an active identity redirect "
                    f"to {survivor_id!r}."
                ),
                severity="info",
            )
        )

    node_view = next(
        (node for node in projection.nodes if node.node_id == resolved_node_id), None
    )
    if node_view is None:
        return WorldGraphRetrievalResult(
            operation="object",
            outcome="empty",
            snapshot=_snapshot_from_projection(projection),
            request_summary=_request_summary(request),
            requested_node_id=request.node_id,
            resolved_node_id=None,
            trust_boundary=_trust_boundary(),
            diagnostics=diagnostics,
        )

    rel_cap = request.bounds.max_relationships
    candidate_relationships = [
        relationship
        for relationship in projection.relationships
        if resolved_node_id in (relationship.source_node_id, relationship.target_node_id)
    ]
    relationship_truncated = len(candidate_relationships) > rel_cap
    selected_relationships = candidate_relationships[:rel_cap]

    attr_cap = request.bounds.max_attributes
    candidate_attributes = [
        attribute
        for attribute in projection.attributes
        if attribute.subject_node_id == resolved_node_id
    ]
    attribute_truncated = len(candidate_attributes) > attr_cap
    selected_attributes = candidate_attributes[:attr_cap]

    selected_edge_ids = {r.edge_id for r in selected_relationships}
    selected_assertion_ids = {a.assertion_id for a in selected_attributes}
    source_anchors, anchor_truncated, unreadable_ids, admitted_source_anchors = (
        _source_anchors_for_targets(
        store=store,
        projection=projection,
        graph_object_ids={resolved_node_id} | selected_edge_ids,
        assertion_ids=selected_assertion_ids,
        max_source_anchors=request.bounds.max_source_anchors,
        )
    )
    missing_evidence_ref_ids, gap_ids, gap_diagnostics = _selection_anchor_gaps(
        source_anchors=admitted_source_anchors,
        selected_graph_object_ids={resolved_node_id} | selected_edge_ids,
        selected_assertion_ids=selected_assertion_ids,
        nodes=[node_view],
        relationships=selected_relationships,
        attributes=selected_attributes,
    )

    coverage = WorldGraphRetrievalCoverage(
        missing_evidence_ref_ids=missing_evidence_ref_ids,
        unreadable_anchor_ids=unreadable_ids,
        truncated_fields=_truncated_fields(
            relationships=relationship_truncated,
            attributes=attribute_truncated,
            source_anchors=anchor_truncated,
        ),
    )
    diagnostics = diagnostics + _outcome_diagnostics(coverage) + gap_diagnostics
    outcome = _determine_outcome(
        truncated=bool(coverage.truncated_fields),
        partial=bool(unreadable_ids) or bool(gap_ids),
        has_content=True,
    )

    return WorldGraphRetrievalResult(
        operation="object",
        outcome=outcome,
        snapshot=_snapshot_from_projection(projection),
        request_summary=_request_summary(request),
        matched_node_ids=[resolved_node_id],
        requested_node_id=request.node_id,
        resolved_node_id=resolved_node_id,
        nodes=[_convert_node(node_view)],
        relationships=[_convert_relationship(r) for r in selected_relationships],
        attributes=[_convert_attribute(a) for a in selected_attributes],
        source_anchors=source_anchors,
        coverage=coverage,
        trust_boundary=_trust_boundary(),
        diagnostics=diagnostics,
    )


def get_object_neighborhood(
    root: Path, request: WorldGraphNeighborhoodRequest
) -> WorldGraphRetrievalResult:
    request = _revalidate(WorldGraphNeighborhoodRequest, request)
    loaded = _load_projection_and_store(
        root,
        world_id=request.world_id,
        campaign_id=request.campaign_id,
        focus=request.focus.to_projection_focus(),
        admissibility=request.admissibility,
        revision_pin=request.revision_pin,
        scope_mode=request.scope_mode,
    )
    if loaded is None:
        return _unavailable_result("neighborhood", request)
    projection, store = loaded

    node_by_id = {node.node_id: node for node in projection.nodes}
    missing_seed_ids = sorted(
        {seed_id for seed_id in request.seed_node_ids if seed_id not in node_by_id}
    )
    present_seed_ids = list(
        dict.fromkeys(seed_id for seed_id in request.seed_node_ids if seed_id in node_by_id)
    )

    node_cap = request.bounds.max_nodes
    seed_truncated = len(present_seed_ids) > node_cap
    if seed_truncated:
        present_seed_ids = present_seed_ids[:node_cap]

    adjacency: dict[str, list[WorldGraphProjectionRelationshipView]] = {}
    for relationship in projection.relationships:
        adjacency.setdefault(relationship.source_node_id, []).append(relationship)
        adjacency.setdefault(relationship.target_node_id, []).append(relationship)

    node_depth: dict[str, int] = {seed_id: 0 for seed_id in present_seed_ids}
    edge_discoverer: dict[str, str] = {}
    visited_node_ids: set[str] = set(present_seed_ids)
    visited_edge_ids: set[str] = set()
    frontier = list(present_seed_ids)
    for depth in range(1, request.max_depth + 1):
        next_frontier: list[str] = []
        for node_id in sorted(frontier):
            for relationship in sorted(
                adjacency.get(node_id, []), key=lambda item: item.edge_id
            ):
                if relationship.edge_id not in edge_discoverer:
                    edge_discoverer[relationship.edge_id] = node_id
                visited_edge_ids.add(relationship.edge_id)
                other_id = (
                    relationship.target_node_id
                    if relationship.source_node_id == node_id
                    else relationship.source_node_id
                )
                if other_id not in visited_node_ids:
                    visited_node_ids.add(other_id)
                    node_depth[other_id] = depth
                    next_frontier.append(other_id)
        frontier = next_frontier

    others_ordered = sorted(
        (node_id for node_id in visited_node_ids if node_id not in set(present_seed_ids)),
        key=lambda node_id: (node_depth.get(node_id, request.max_depth + 1), node_id),
    )
    remaining_capacity = max(node_cap - len(present_seed_ids), 0)
    selected_ids = present_seed_ids + others_ordered[:remaining_capacity]
    node_truncated = seed_truncated or (
        len(present_seed_ids) + len(others_ordered) > len(selected_ids)
    )
    selected_node_id_set = set(selected_ids)

    rel_cap = request.bounds.max_relationships
    candidate_relationships = sorted(
        (
            relationship
            for relationship in projection.relationships
            if relationship.edge_id in visited_edge_ids
            and relationship.source_node_id in selected_node_id_set
            and relationship.target_node_id in selected_node_id_set
        ),
        key=lambda item: item.edge_id,
    )
    relationship_truncated = len(candidate_relationships) > rel_cap
    selected_relationships = candidate_relationships[:rel_cap]

    attr_cap = request.bounds.max_attributes
    candidate_attributes = [
        attribute
        for attribute in projection.attributes
        if attribute.subject_node_id in selected_node_id_set
    ]
    attribute_truncated = len(candidate_attributes) > attr_cap
    selected_attributes = candidate_attributes[:attr_cap]

    selected_edge_ids = {r.edge_id for r in selected_relationships}
    selected_assertion_ids = {a.assertion_id for a in selected_attributes}
    source_anchors, anchor_truncated, unreadable_ids, admitted_source_anchors = (
        _source_anchors_for_targets(
        store=store,
        projection=projection,
        graph_object_ids=selected_node_id_set | selected_edge_ids,
        assertion_ids=selected_assertion_ids,
        max_source_anchors=request.bounds.max_source_anchors,
        )
    )

    nodes_out = [_convert_node(node_by_id[node_id]) for node_id in selected_ids]
    missing_evidence_ref_ids, gap_ids, gap_diagnostics = _selection_anchor_gaps(
        source_anchors=admitted_source_anchors,
        selected_graph_object_ids=selected_node_id_set | selected_edge_ids,
        selected_assertion_ids=selected_assertion_ids,
        nodes=[node_by_id[node_id] for node_id in selected_ids],
        relationships=selected_relationships,
        attributes=selected_attributes,
    )
    coverage = WorldGraphRetrievalCoverage(
        requested_seed_node_ids=list(request.seed_node_ids),
        missing_seed_node_ids=missing_seed_ids,
        missing_evidence_ref_ids=missing_evidence_ref_ids,
        unreadable_anchor_ids=unreadable_ids,
        truncated_fields=_truncated_fields(
            nodes=node_truncated,
            relationships=relationship_truncated,
            attributes=attribute_truncated,
            source_anchors=anchor_truncated,
        ),
    )
    outcome = _determine_outcome(
        truncated=bool(coverage.truncated_fields),
        partial=bool(missing_seed_ids) or bool(unreadable_ids) or bool(gap_ids),
        has_content=bool(nodes_out),
    )

    return WorldGraphRetrievalResult(
        operation="neighborhood",
        outcome=outcome,
        snapshot=_snapshot_from_projection(projection),
        request_summary=_request_summary(request),
        matched_node_ids=selected_ids,
        nodes=nodes_out,
        relationships=[
            _convert_relationship(
                relationship,
                direction_from_node_id=edge_discoverer[relationship.edge_id],
            )
            for relationship in selected_relationships
        ],
        attributes=[_convert_attribute(a) for a in selected_attributes],
        source_anchors=source_anchors,
        coverage=coverage,
        trust_boundary=_trust_boundary(),
        diagnostics=_outcome_diagnostics(coverage) + gap_diagnostics,
    )


def get_object_evidence(
    root: Path, request: WorldGraphEvidenceRequest
) -> WorldGraphRetrievalResult:
    request = _revalidate(WorldGraphEvidenceRequest, request)
    loaded = _load_projection_and_store(
        root,
        world_id=request.world_id,
        campaign_id=request.campaign_id,
        focus=request.focus.to_projection_focus(),
        admissibility=request.admissibility,
        revision_pin=request.revision_pin,
        scope_mode=request.scope_mode,
    )
    if loaded is None:
        return _unavailable_result("evidence", request)
    projection, store = loaded

    target = request.target
    nodes_out: list[WorldGraphRetrievalNode] = []
    relationships_out: list[WorldGraphRetrievalRelationship] = []
    attributes_out: list[WorldGraphRetrievalAttribute] = []
    graph_object_ids: set[str] = set()
    assertion_ids: set[str] = set()
    found = False

    if target.kind == "node":
        node_view = next(
            (node for node in projection.nodes if node.node_id == target.id), None
        )
        if node_view is not None:
            found = True
            nodes_out = [_convert_node(node_view)]
            graph_object_ids = {target.id}
    elif target.kind == "relationship":
        relationship_view = next(
            (r for r in projection.relationships if r.edge_id == target.id), None
        )
        if relationship_view is not None:
            found = True
            relationships_out = [_convert_relationship(relationship_view)]
            graph_object_ids = {target.id}
    else:
        attribute_view = next(
            (a for a in projection.attributes if a.assertion_id == target.id), None
        )
        if attribute_view is not None:
            found = True
            attributes_out = [_convert_attribute(attribute_view)]
            assertion_ids = {target.id}

    if not found:
        return WorldGraphRetrievalResult(
            operation="evidence",
            outcome="empty",
            snapshot=_snapshot_from_projection(projection),
            request_summary=_request_summary(request),
            trust_boundary=_trust_boundary(),
        )

    source_anchors, anchor_truncated, unreadable_ids, admitted_source_anchors = (
        _source_anchors_for_targets(
        store=store,
        projection=projection,
        graph_object_ids=graph_object_ids,
        assertion_ids=assertion_ids,
        max_source_anchors=request.bounds.max_source_anchors,
        )
    )
    missing_evidence_ref_ids, gap_ids, gap_diagnostics = _selection_anchor_gaps(
        source_anchors=admitted_source_anchors,
        selected_graph_object_ids=graph_object_ids,
        selected_assertion_ids=assertion_ids,
        nodes=nodes_out,
        relationships=relationships_out,
        attributes=attributes_out,
    )
    coverage = WorldGraphRetrievalCoverage(
        missing_evidence_ref_ids=missing_evidence_ref_ids,
        unreadable_anchor_ids=unreadable_ids,
        truncated_fields=_truncated_fields(source_anchors=anchor_truncated),
    )
    outcome = _determine_outcome(
        truncated=bool(coverage.truncated_fields),
        partial=bool(unreadable_ids) or bool(gap_ids) or not source_anchors,
        has_content=True,
    )

    return WorldGraphRetrievalResult(
        operation="evidence",
        outcome=outcome,
        snapshot=_snapshot_from_projection(projection),
        request_summary=_request_summary(request),
        nodes=nodes_out,
        relationships=relationships_out,
        attributes=attributes_out,
        source_anchors=source_anchors,
        coverage=coverage,
        trust_boundary=_trust_boundary(),
        diagnostics=_outcome_diagnostics(coverage) + gap_diagnostics,
    )


def _handle_source_read(
    read_callable: Callable[[], SourceReadOutcome],
) -> SourceReadOutcome | None:
    try:
        return read_callable()
    except SourceReadError as exc:
        if exc.code in _SOURCE_READ_UNAVAILABLE_CODES:
            return None
        raise WorldGraphRetrievalError(
            str(exc),
            code=exc.code,
            status_code=409,
            diagnostics=[
                WorldGraphRetrievalDiagnostic(code=exc.code, message=str(exc), severity="error")
            ],
        ) from exc


@dataclass(frozen=True)
class AdmittedSourceAnchorMatch:
    """Graph-re-resolved admitted source anchor for a read request.

    Live services may compose registry-backed readers on top of this match
    without duplicating G→evidence→A/S derivation.
    """

    snapshot: WorldGraphRetrievalSnapshot
    derivation: _AnchorDerivation
    store: UnionSupergraphStore
    graph_content_sha256: str | None


def resolve_admitted_anchor_match(
    root: Path,
    request: WorldGraphSourceAnchorReadRequest,
) -> AdmittedSourceAnchorMatch | WorldGraphSourceAnchorReadResult:
    """Re-derive G under the exact request snapshot.

    Returns either an ``AdmittedSourceAnchorMatch`` or an early-exit
    ``WorldGraphSourceAnchorReadResult`` (unavailable world / unknown G).
    """
    request = _revalidate(WorldGraphSourceAnchorReadRequest, request)
    loaded = _load_projection_and_store(
        root,
        world_id=request.world_id,
        campaign_id=request.campaign_id,
        focus=request.focus.to_projection_focus(),
        admissibility=request.admissibility,
        revision_pin=request.revision_pin,
        scope_mode=request.scope_mode,
    )
    if loaded is None:
        return WorldGraphSourceAnchorReadResult(
            outcome="unavailable",
            snapshot=None,
            anchor_id=request.anchor_id,
            trust_boundary=_trust_boundary(),
            diagnostics=[
                WorldGraphRetrievalDiagnostic(
                    code="world_graph_unavailable",
                    message="The requested world graph or revision could not be opened.",
                    severity="warning",
                )
            ],
        )
    projection, store = loaded
    snapshot = _snapshot_from_projection(projection)
    derivations = _projection_admitted_anchor_derivations(store=store, projection=projection)
    match = next(
        (item for item in derivations if item.anchor.anchor_id == request.anchor_id), None
    )
    if match is None:
        return WorldGraphSourceAnchorReadResult(
            outcome="empty",
            snapshot=snapshot,
            anchor_id=request.anchor_id,
            trust_boundary=_trust_boundary(),
            diagnostics=[
                WorldGraphRetrievalDiagnostic(
                    code="unknown_anchor",
                    message=(
                        "No admissible source anchor matches this anchor id in the "
                        "requested context."
                    ),
                    severity="warning",
                )
            ],
        )
    source_artifact = store.source_artifacts.get(match.anchor.source_artifact_id)
    return AdmittedSourceAnchorMatch(
        snapshot=snapshot,
        derivation=match,
        store=store,
        graph_content_sha256=(
            _admitted_source_content_sha256(source_artifact)
            if source_artifact is not None
            else None
        ),
    )


def read_source_anchor(
    root: Path,
    request: WorldGraphSourceAnchorReadRequest,
    *,
    repo_root: Path | None = None,
) -> WorldGraphSourceAnchorReadResult:
    request = _revalidate(WorldGraphSourceAnchorReadRequest, request)
    resolved_repo_root = repo_root if repo_root is not None else _default_repo_root()

    resolved = resolve_admitted_anchor_match(root, request)
    if isinstance(resolved, WorldGraphSourceAnchorReadResult):
        return resolved
    snapshot = resolved.snapshot
    match = resolved.derivation
    store = resolved.store
    anchor = match.anchor

    if not anchor.readable or anchor.locator_kind == "unsupported":
        return WorldGraphSourceAnchorReadResult(
            outcome="partial",
            snapshot=snapshot,
            anchor_id=request.anchor_id,
            evidence_ref_id=anchor.evidence_ref_id,
            source_artifact_id=anchor.source_artifact_id,
            source_domain=anchor.source_domain,
            source_span_ref_id=anchor.source_span_ref_id,
            locator_kind=anchor.locator_kind,
            trust_boundary=_trust_boundary(),
            diagnostics=[
                WorldGraphRetrievalDiagnostic(
                    code="unsupported_locator",
                    message="This source anchor's locator/URI scheme is not supported for reading.",
                    severity="warning",
                )
            ],
        )

    if anchor.locator_kind == "source_span":
        # Registry-backed worldbuilding SourceSpan reads are composed by the
        # live_control retrieval service — Kernel must not open registries.
        return WorldGraphSourceAnchorReadResult(
            outcome="unavailable",
            snapshot=snapshot,
            anchor_id=request.anchor_id,
            evidence_ref_id=anchor.evidence_ref_id,
            source_artifact_id=anchor.source_artifact_id,
            source_domain=anchor.source_domain,
            source_span_ref_id=anchor.source_span_ref_id,
            locator_kind=anchor.locator_kind,
            trust_boundary=_trust_boundary(),
            diagnostics=[
                WorldGraphRetrievalDiagnostic(
                    code="requires_registry_source_span_read",
                    message=(
                        "Worldbuilding source-span anchors require the registry-"
                        "backed live retrieval reader."
                    ),
                    severity="info",
                )
            ],
        )

    source_artifact = store.source_artifacts.get(anchor.source_artifact_id)
    if source_artifact is None:
        raise WorldGraphRetrievalError(
            "Source artifact referenced by an admissible anchor is missing from the "
            "revision store.",
            code="projection_integrity_error",
            status_code=409,
        )

    read_outcome: SourceReadOutcome | None
    if anchor.locator_kind == "heading":
        relative_path = parse_repo_uri(source_artifact.uri)
        heading_text = parse_heading_locator(match.locator or "")
        if relative_path is None or heading_text is None:
            raise WorldGraphRetrievalError(
                "Heading anchor URI/locator no longer matches the expected "
                "repo:// + heading: shape.",
                code="projection_integrity_error",
                status_code=409,
            )
        expected_sha = _admitted_source_content_sha256(source_artifact)
        if expected_sha is None:
            _raise_source_integrity_error(
                "repo:// source artifact is missing a revision-bound content digest."
            )
        read_outcome = _handle_source_read(
            lambda: read_repo_heading_anchor(
                repo_root=resolved_repo_root,
                relative_path=relative_path,
                heading_text=heading_text,
                expected_content_sha256=expected_sha,
                max_chars=request.max_chars,
            )
        )
    elif anchor.locator_kind == "json_pointer":
        json_pointer = parse_json_pointer_locator(match.locator or "")
        if json_pointer is None or match.contribution_id is None:
            raise WorldGraphRetrievalError(
                "JSON-pointer anchor locator/context no longer matches the expected "
                "graph-data:// + jsonptr: shape.",
                code="projection_integrity_error",
                status_code=409,
            )
        try:
            contribution = _load_validated_contribution(
                root, request.world_id, match.contribution_id
            )
        except WorldGraphProjectionError as exc:
            raise _map_projection_error(exc) from exc
        _validate_initialization_receipt_for_graph_data(
            root=root,
            world_id=request.world_id,
            campaign_id=request.campaign_id,
            store=store,
            revision_id=snapshot.revision_id,
        )
        _verify_graph_data_contribution_digest(
            store=store,
            contribution_id=match.contribution_id,
            contribution=contribution,
        )
        # Pointer resolution must use the same lifecycle-neutral payload that
        # the revision-bound digest covers — never the mutable ledger envelope.
        read_outcome = _handle_source_read(
            lambda: read_graph_data_json_pointer_anchor(
                contribution_payload=contribution_source_payload(contribution),
                json_pointer=json_pointer,
                max_chars=request.max_chars,
            )
        )
    else:
        read_outcome = None

    if read_outcome is None:
        return WorldGraphSourceAnchorReadResult(
            outcome="unavailable",
            snapshot=snapshot,
            anchor_id=request.anchor_id,
            evidence_ref_id=anchor.evidence_ref_id,
            source_artifact_id=anchor.source_artifact_id,
            source_domain=anchor.source_domain,
            source_span_ref_id=anchor.source_span_ref_id,
            locator_kind=anchor.locator_kind,
            trust_boundary=_trust_boundary(),
            diagnostics=[
                WorldGraphRetrievalDiagnostic(
                    code="source_unavailable",
                    message="The admitted source could not be opened.",
                    severity="warning",
                )
            ],
        )

    outcome: RetrievalOutcome = "truncated" if read_outcome.truncated else "enough"
    diagnostics: list[WorldGraphRetrievalDiagnostic] = []
    if read_outcome.truncated:
        diagnostics.append(
            WorldGraphRetrievalDiagnostic(
                code="content_truncated",
                message=f"Content truncated to {request.max_chars} characters.",
                severity="warning",
            )
        )

    return WorldGraphSourceAnchorReadResult(
        outcome=outcome,
        snapshot=snapshot,
        anchor_id=request.anchor_id,
        evidence_ref_id=anchor.evidence_ref_id,
        source_artifact_id=anchor.source_artifact_id,
        source_domain=anchor.source_domain,
        source_span_ref_id=anchor.source_span_ref_id,
        locator_kind=anchor.locator_kind,
        media_type=read_outcome.media_type,
        content=read_outcome.content,
        content_sha256=read_outcome.content_sha256,
        line_start=read_outcome.line_start,
        line_end=read_outcome.line_end,
        truncated=read_outcome.truncated,
        trust_boundary=_trust_boundary(),
        diagnostics=diagnostics,
    )


__all__ = [
    "AdmittedSourceAnchorMatch",
    "WorldGraphRetrievalError",
    "get_campaign_object",
    "get_object_evidence",
    "get_object_neighborhood",
    "read_source_anchor",
    "resolve_admitted_anchor_match",
    "search_campaign_graph",
]
