"""Kernel World Graph projection (PR007A)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from graph_memory.evidence.assertion_support import DurableAssertionSupport
from graph_memory.kernel.contribution_models import GraphContributionAssertion
from graph_memory.kernel.world_graph import (
    WorldGraphNotFoundError,
    load_world_graph_revision,
    open_current_world_graph,
    open_world_graph_head,
)
from graph_memory.projection.recap_projection import build_focus_overlay, build_node_view
from graph_memory.projection.world_projection import (
    PROJECTION_RESPONSE_SCHEMA,
    SEARCH_MAX_ATTRIBUTES,
    SEARCH_MAX_EVIDENCE,
    SEARCH_MAX_NODES,
    SEARCH_MAX_RELATIONSHIPS,
    SEARCH_MAX_SOURCE_ARTIFACTS,
    WorldGraphProjection,
    WorldGraphProjectionAttributeView,
    WorldGraphProjectionDiagnostic,
    WorldGraphProjectionEvidenceView,
    WorldGraphProjectionFocus,
    WorldGraphProjectionNodeView,
    WorldGraphProjectionRelationshipView,
    WorldGraphProjectionRequest,
    WorldGraphProjectionSnapshot,
    WorldGraphProjectionSourceArtifactView,
    WorldGraphProjectionSummary,
    WorldGraphProjectionTrustBoundary,
    WorldGraphQueryContext,
    derive_attribute_text_value,
    rank_search_node_matches,
)
from graph_memory.union_supergraph.model import UnionSupergraphStore
from graph_memory.union_supergraph.projection_identity import (
    build_union_projection_identity_context,
    is_projectable_union_edge,
    projectable_node_ids,
)
from graph_memory.world_supergraph.contribution_store import load_contribution_record
from graph_memory.world_supergraph.storage import load_world_graph_revision_manifest

_TRUST_CANNOT = [
    "Evidence locators and source spans are metadata only; this projection does not verify them.",
    "Source artifact text is not read or opened by this projection.",
    "v0 projection is single-campaign scoped; cross-campaign admissibility is not modeled.",
]
_TRUST_CAN_HEAD = [
    "Revision pin identity matches the requested world graph revision.",
    "Selected revision payload is the immutable store bytes for that revision.",
    "Attribute views are reconstructed from revision-bound assertion support and contributions.",
]


class WorldGraphProjectionError(Exception):
    """Stable projection failure with API-safe code and diagnostics."""

    def __init__(
        self,
        message: str,
        *,
        code: str,
        status_code: int,
        diagnostics: list[WorldGraphProjectionDiagnostic] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code
        self.diagnostics = list(diagnostics or [])


def resolve_projection_admissibility(policy: str) -> str:
    if policy != "gm":
        raise WorldGraphProjectionError(
            f"Unsupported projection admissibility policy: {policy!r}",
            code="unsupported_admissibility",
            status_code=422,
            diagnostics=[
                WorldGraphProjectionDiagnostic(
                    code="unsupported_admissibility",
                    message="Only gm admissibility is supported in PR007A.",
                    severity="error",
                )
            ],
        )
    return "gm"


def _diagnostic(code: str, message: str, *, severity: str = "error") -> WorldGraphProjectionDiagnostic:
    return WorldGraphProjectionDiagnostic(code=code, message=message, severity=severity)


def _parse_support(raw: dict[str, Any]) -> DurableAssertionSupport:
    return DurableAssertionSupport.model_validate(raw)


def _load_revision_context(
    root: Path,
    request: WorldGraphProjectionRequest,
) -> tuple[str, str, UnionSupergraphStore]:
    world_id = request.world_id
    if request.revision_pin:
        try:
            head = open_world_graph_head(root, world_id)
        except WorldGraphNotFoundError as exc:
            raise WorldGraphProjectionError(
                f"World graph unavailable for world_id={world_id!r}",
                code="world_graph_unavailable",
                status_code=404,
                diagnostics=[_diagnostic("world_graph_unavailable", str(exc))],
            ) from exc
        revision_id = request.revision_pin
        try:
            load_world_graph_revision_manifest(root, world_id, revision_id)
            store = load_world_graph_revision(root, world_id, revision_id)
        except (WorldGraphNotFoundError, ValueError) as exc:
            raise WorldGraphProjectionError(
                f"Revision pin not found: {revision_id!r}",
                code="revision_not_found",
                status_code=404,
                diagnostics=[_diagnostic("revision_not_found", str(exc))],
            ) from exc
        return revision_id, head.head_revision_id, store

    try:
        head, _revision, store = open_current_world_graph(root, world_id)
    except WorldGraphNotFoundError as exc:
        raise WorldGraphProjectionError(
            f"World graph unavailable for world_id={world_id!r}",
            code="world_graph_unavailable",
            status_code=404,
            diagnostics=[_diagnostic("world_graph_unavailable", str(exc))],
        ) from exc
    return head.head_revision_id, head.head_revision_id, store


def _assert_campaign_scope(request: WorldGraphProjectionRequest, store: UnionSupergraphStore) -> None:
    if store.campaign_id != request.campaign_id:
        raise WorldGraphProjectionError(
            "Requested campaign_id does not match the selected revision store scope.",
            code="campaign_scope_mismatch",
            status_code=409,
            diagnostics=[
                _diagnostic(
                    "campaign_scope_mismatch",
                    (
                        f"request campaign_id={request.campaign_id!r} "
                        f"store campaign_id={store.campaign_id!r}"
                    ),
                )
            ],
        )


def _resolve_assertion_from_support(
    root: Path,
    world_id: str,
    store: UnionSupergraphStore,
    support: DurableAssertionSupport,
) -> GraphContributionAssertion:
    if not support.active_contribution_ids:
        raise WorldGraphProjectionError(
            f"Assertion support {support.assertion_id!r} has no active contributions.",
            code="projection_integrity_error",
            status_code=409,
            diagnostics=[
                _diagnostic(
                    "missing_active_contributions",
                    f"No active contributions for assertion {support.assertion_id!r}.",
                )
            ],
        )

    assertion: GraphContributionAssertion | None = None
    for contribution_id in support.active_contribution_ids:
        try:
            contribution = load_contribution_record(root, world_id, contribution_id)
        except (FileNotFoundError, OSError, ValueError) as exc:
            raise WorldGraphProjectionError(
                f"Missing contribution record {contribution_id!r}",
                code="projection_integrity_error",
                status_code=409,
                diagnostics=[
                    _diagnostic(
                        "missing_contribution",
                        f"Contribution {contribution_id!r} could not be loaded: {exc}",
                    )
                ],
            ) from exc
        for candidate in contribution.accepted_assertions:
            if candidate.assertion_id == support.assertion_id:
                assertion = candidate
                break

    if assertion is None:
        raise WorldGraphProjectionError(
            f"Assertion {support.assertion_id!r} not found in active contributions.",
            code="projection_integrity_error",
            status_code=409,
            diagnostics=[
                _diagnostic(
                    "missing_assertion",
                    f"Assertion {support.assertion_id!r} missing from contribution payloads.",
                )
            ],
        )

    expected_graph_object_id = support.graph_object_id
    if expected_graph_object_id is not None:
        actual = assertion.subject_node_id or assertion.target_node_id
        if assertion.assertion_kind == "edge":
            value = dict(assertion.value)
            actual = str(value.get("edge_id") or actual or "")
        if actual != expected_graph_object_id:
            raise WorldGraphProjectionError(
                "Assertion graph_object_id does not match contribution payload.",
                code="projection_integrity_error",
                status_code=409,
                diagnostics=[
                    _diagnostic(
                        "graph_object_id_mismatch",
                        (
                            f"support graph_object_id={expected_graph_object_id!r} "
                            f"assertion object={actual!r}"
                        ),
                    )
                ],
            )

    for evidence_ref_id in support.evidence_ref_ids:
        if evidence_ref_id not in store.evidence:
            raise WorldGraphProjectionError(
                f"Unresolved evidence reference {evidence_ref_id!r}",
                code="projection_integrity_error",
                status_code=409,
                diagnostics=[
                    _diagnostic(
                        "unresolved_evidence_ref",
                        f"Evidence {evidence_ref_id!r} missing from revision store.",
                    )
                ],
            )
    for source_artifact_id in support.source_artifact_ids:
        if source_artifact_id not in store.source_artifacts:
            raise WorldGraphProjectionError(
                f"Unresolved source artifact {source_artifact_id!r}",
                code="projection_integrity_error",
                status_code=409,
                diagnostics=[
                    _diagnostic(
                        "unresolved_source_artifact",
                        (
                            f"Source artifact {source_artifact_id!r} "
                            "missing from revision store."
                        ),
                    )
                ],
            )
    return assertion


def _edge_state_field(edge_state: dict[str, Any], key: str) -> str | None:
    value = edge_state.get(key)
    return str(value) if value is not None else None


def _support_for_edge(
    store: UnionSupergraphStore,
    edge_id: str,
) -> DurableAssertionSupport | None:
    for raw in store.assertion_support.values():
        support = _parse_support(raw)
        if support.graph_object_id == edge_id:
            return support
    return None


def _build_attribute_views(
    root: Path,
    world_id: str,
    store: UnionSupergraphStore,
) -> list[WorldGraphProjectionAttributeView]:
    attributes: list[WorldGraphProjectionAttributeView] = []
    for raw_support in store.assertion_support.values():
        support = _parse_support(raw_support)
        if support.assertion_kind != "attribute":
            continue
        assertion = _resolve_assertion_from_support(root, world_id, store, support)
        value = dict(assertion.value)
        attributes.append(
            WorldGraphProjectionAttributeView(
                assertion_id=assertion.assertion_id,
                subject_node_id=assertion.subject_node_id or "",
                predicate=assertion.predicate,
                label=assertion.label,
                value=value,
                text_value=derive_attribute_text_value(value),
                epistemic_kind=assertion.epistemic_kind,
                visibility=assertion.visibility,
                campaign_scope=assertion.campaign_scope,
                temporal_scope=assertion.temporal_scope,
                support_state=support.support_state,
                active_contribution_ids=list(support.active_contribution_ids),
                evidence_ref_ids=list(support.evidence_ref_ids),
                source_artifact_ids=list(support.source_artifact_ids),
            )
        )
    return sorted(attributes, key=lambda item: item.assertion_id)


def _build_relationship_views(
    store: UnionSupergraphStore,
) -> list[WorldGraphProjectionRelationshipView]:
    identity_context = build_union_projection_identity_context(store)
    relationships: list[WorldGraphProjectionRelationshipView] = []
    for edge_id, edge in sorted(store.edges.items()):
        if not is_projectable_union_edge(edge, identity_context):
            continue
        support = _support_for_edge(store, edge_id)
        active_contribution_ids: list[str] = []
        evidence_ref_ids = list(edge.evidence_ref_ids)
        source_artifact_ids: list[str] = []
        if support is not None:
            active_contribution_ids = list(support.active_contribution_ids)
            if support.evidence_ref_ids:
                evidence_ref_ids = list(support.evidence_ref_ids)
            source_artifact_ids = list(support.source_artifact_ids)
        edge_state = edge.state or {}
        relationships.append(
            WorldGraphProjectionRelationshipView(
                edge_id=edge.edge_id,
                source_node_id=edge.source_node_id,
                target_node_id=edge.target_node_id,
                predicate=edge.predicate,
                label=edge.label,
                direction=edge.direction,
                session_ids=list(edge.session_ids),
                visibility=_edge_state_field(edge_state, "visibility"),
                campaign_scope=_edge_state_field(edge_state, "campaign_scope"),
                epistemic_kind=_edge_state_field(edge_state, "epistemic_kind"),
                evidence_ref_ids=evidence_ref_ids,
                source_artifact_ids=source_artifact_ids,
                active_contribution_ids=active_contribution_ids,
            )
        )
    return relationships


def _build_node_views(
    store: UnionSupergraphStore,
    focus: WorldGraphProjectionFocus,
) -> list[WorldGraphProjectionNodeView]:
    identity_context = build_union_projection_identity_context(store)
    focus_session_id = focus.session_id if focus.kind == "session" else None
    nodes: list[WorldGraphProjectionNodeView] = []
    for node_id in sorted(projectable_node_ids(store, identity_context)):
        view = build_node_view(
            store,
            node_id,
            focus_session_id=focus_session_id,
            identity_context=identity_context,
        )
        nodes.append(
            WorldGraphProjectionNodeView(
                node_id=view.node_id,
                label=view.label,
                kind=view.kind,
                role=view.role,
                aliases=list(view.aliases),
                source_domains=list(view.source_domains),
                summary=view.summary,
                anchored_to_focus_session=view.anchored_to_focus_session,
            )
        )
    return nodes


def _build_evidence_views(
    store: UnionSupergraphStore,
) -> list[WorldGraphProjectionEvidenceView]:
    evidence_views: list[WorldGraphProjectionEvidenceView] = []
    for evidence_id in sorted(store.evidence):
        evidence = store.evidence[evidence_id]
        evidence_views.append(
            WorldGraphProjectionEvidenceView(
                evidence_ref_id=evidence.evidence_ref_id,
                source_artifact_id=evidence.source_artifact_id,
                source_domain=str(evidence.source_domain),
                session_id=evidence.session_id,
                locator=evidence.locator,
                source_span_ref_id=evidence.source_span_ref_id,
            )
        )
    return evidence_views


def _build_source_artifact_views(
    store: UnionSupergraphStore,
) -> list[WorldGraphProjectionSourceArtifactView]:
    artifacts: list[WorldGraphProjectionSourceArtifactView] = []
    for artifact_id in sorted(store.source_artifacts):
        artifact = store.source_artifacts[artifact_id]
        artifact_extra = artifact.model_extra or {}
        artifacts.append(
            WorldGraphProjectionSourceArtifactView(
                source_artifact_id=artifact.source_artifact_id,
                source_domain=str(artifact.source_domain),
                uri=artifact.uri,
                campaign_id=artifact.campaign_id,
                session_id=(
                    str(artifact_extra["session_id"])
                    if artifact_extra.get("session_id") is not None
                    else None
                ),
            )
        )
    return artifacts


def build_projection_payload(
    *,
    request: WorldGraphProjectionRequest,
    revision_id: str,
    head_revision_id: str,
    store: UnionSupergraphStore,
    root: Path | None = None,
    world_id: str | None = None,
) -> WorldGraphProjection:
    resolve_projection_admissibility(request.admissibility)
    _assert_campaign_scope(request, store)

    resolved_world_id = world_id or request.world_id
    if root is None:
        raise WorldGraphProjectionError(
            "Internal projection build requires root for contribution reconstruction.",
            code="projection_internal_error",
            status_code=500,
        )

    try:
        nodes = _build_node_views(store, request.focus)
        relationships = _build_relationship_views(store)
        attributes = _build_attribute_views(root, resolved_world_id, store)
        evidence = _build_evidence_views(store)
        source_artifacts = _build_source_artifact_views(store)
    except WorldGraphProjectionError:
        raise
    except Exception as exc:
        raise WorldGraphProjectionError(
            "World graph projection failed while building payload.",
            code="projection_internal_error",
            status_code=500,
            diagnostics=[_diagnostic("projection_internal_error", str(exc))],
        ) from exc

    identity_context = build_union_projection_identity_context(store)
    focus_session_id = request.focus.session_id if request.focus.kind == "session" else None
    overlay = build_focus_overlay(
        store,
        focus_session_id=focus_session_id,
        identity_context=identity_context,
    )
    diagnostics = [
        WorldGraphProjectionDiagnostic(
            code="focus_overlay_built",
            message=(
                f"Focused {len(overlay.focused_node_ids)} nodes for "
                f"focus={request.focus.kind}."
            ),
            severity="info",
        )
    ]

    projection = WorldGraphProjection(
        schema=PROJECTION_RESPONSE_SCHEMA,
        snapshot=WorldGraphProjectionSnapshot(
            world_id=request.world_id,
            campaign_id=request.campaign_id,
            revision_id=revision_id,
            head_revision_id=head_revision_id,
            is_head=revision_id == head_revision_id,
            focus=request.focus,
            admissibility=request.admissibility,
        ),
        summary=WorldGraphProjectionSummary(
            node_count=len(nodes),
            relationship_count=len(relationships),
            attribute_count=len(attributes),
            evidence_count=len(evidence),
            source_artifact_count=len(source_artifacts),
            projection_truncated=False,
        ),
        nodes=nodes,
        relationships=relationships,
        attributes=attributes,
        evidence=evidence,
        source_artifacts=source_artifacts,
        trust_boundary=WorldGraphProjectionTrustBoundary(
            can_trust=list(_TRUST_CAN_HEAD),
            cannot_trust=list(_TRUST_CANNOT),
        ),
        diagnostics=diagnostics,
    )
    if request.query_text:
        projection = projection.model_copy(
            update={
                "query_context": search_world_graph_projection(
                    projection,
                    request.query_text,
                )
            }
        )
    return projection


def project_world_graph(
    root: Path,
    request: WorldGraphProjectionRequest,
) -> WorldGraphProjection:
    try:
        request = WorldGraphProjectionRequest.model_validate(
            request.model_dump(mode="json")
        )
    except Exception as exc:
        raise WorldGraphProjectionError(
            "Projection request is invalid.",
            code="invalid_request",
            status_code=422,
            diagnostics=[_diagnostic("invalid_request", str(exc))],
        ) from exc

    resolve_projection_admissibility(request.admissibility)

    try:
        revision_id, head_revision_id, store = _load_revision_context(root, request)
        return build_projection_payload(
            request=request,
            revision_id=revision_id,
            head_revision_id=head_revision_id,
            store=store,
            root=root,
            world_id=request.world_id,
        )
    except WorldGraphProjectionError:
        raise
    except Exception as exc:
        raise WorldGraphProjectionError(
            "World graph projection failed unexpectedly.",
            code="projection_internal_error",
            status_code=500,
            diagnostics=[_diagnostic("projection_internal_error", str(exc))],
        ) from exc


def search_world_graph_projection(
    projection: WorldGraphProjection,
    query_text: str,
) -> WorldGraphQueryContext:
    query = query_text.strip()
    if not query:
        return WorldGraphQueryContext(
            revision_id=projection.snapshot.revision_id,
            query_text=query_text,
            diagnostics=[
                WorldGraphProjectionDiagnostic(
                    code="empty_query",
                    message="Search query is empty.",
                    severity="warning",
                )
            ],
        )

    ranked_nodes = rank_search_node_matches(projection.nodes, projection.attributes, query)
    matched_node_ids = [node.node_id for node, _score in ranked_nodes]

    node_cap = SEARCH_MAX_NODES
    selected_nodes = [node for node, _score in ranked_nodes[:node_cap]]

    selected_node_ids = {node.node_id for node in selected_nodes}

    selected_relationships = [
        relationship
        for relationship in projection.relationships
        if relationship.source_node_id in selected_node_ids
        or relationship.target_node_id in selected_node_ids
    ]
    relationship_truncated = len(selected_relationships) > SEARCH_MAX_RELATIONSHIPS
    selected_relationships = selected_relationships[:SEARCH_MAX_RELATIONSHIPS]

    selected_attributes = [
        attribute
        for attribute in projection.attributes
        if attribute.subject_node_id in selected_node_ids
    ]
    attribute_truncated = len(selected_attributes) > SEARCH_MAX_ATTRIBUTES
    selected_attributes = selected_attributes[:SEARCH_MAX_ATTRIBUTES]

    evidence_ids = {
        evidence_id
        for attribute in selected_attributes
        for evidence_id in attribute.evidence_ref_ids
    }
    evidence_ids.update(
        evidence_id
        for relationship in selected_relationships
        for evidence_id in relationship.evidence_ref_ids
    )
    selected_evidence = [
        item for item in projection.evidence if item.evidence_ref_id in evidence_ids
    ]
    evidence_truncated = len(selected_evidence) > SEARCH_MAX_EVIDENCE
    selected_evidence = selected_evidence[:SEARCH_MAX_EVIDENCE]

    artifact_ids = {
        artifact_id
        for attribute in selected_attributes
        for artifact_id in attribute.source_artifact_ids
    }
    selected_artifacts = [
        item
        for item in projection.source_artifacts
        if item.source_artifact_id in artifact_ids
    ]
    artifact_truncated = len(selected_artifacts) > SEARCH_MAX_SOURCE_ARTIFACTS
    selected_artifacts = selected_artifacts[:SEARCH_MAX_SOURCE_ARTIFACTS]

    diagnostics: list[WorldGraphProjectionDiagnostic] = []
    if len(ranked_nodes) > node_cap:
        diagnostics.append(
            WorldGraphProjectionDiagnostic(
                code="search_truncated_nodes",
                message=f"Node matches truncated to {node_cap}.",
                severity="warning",
            )
        )
    if relationship_truncated:
        diagnostics.append(
            WorldGraphProjectionDiagnostic(
                code="search_truncated_relationships",
                message=f"Relationship matches truncated to {SEARCH_MAX_RELATIONSHIPS}.",
                severity="warning",
            )
        )
    if attribute_truncated:
        diagnostics.append(
            WorldGraphProjectionDiagnostic(
                code="search_truncated_attributes",
                message=f"Attribute matches truncated to {SEARCH_MAX_ATTRIBUTES}.",
                severity="warning",
            )
        )
    if evidence_truncated:
        diagnostics.append(
            WorldGraphProjectionDiagnostic(
                code="search_truncated_evidence",
                message=f"Evidence matches truncated to {SEARCH_MAX_EVIDENCE}.",
                severity="warning",
            )
        )
    if artifact_truncated:
        diagnostics.append(
            WorldGraphProjectionDiagnostic(
                code="search_truncated_source_artifacts",
                message=(
                    f"Source artifact matches truncated to {SEARCH_MAX_SOURCE_ARTIFACTS}."
                ),
                severity="warning",
            )
        )

    return WorldGraphQueryContext(
        revision_id=projection.snapshot.revision_id,
        query_text=query_text,
        matched_node_ids=matched_node_ids,
        nodes=selected_nodes,
        relationships=selected_relationships,
        attributes=selected_attributes,
        evidence=selected_evidence,
        source_artifacts=selected_artifacts,
        diagnostics=diagnostics,
    )


__all__ = [
    "WorldGraphProjectionError",
    "build_projection_payload",
    "project_world_graph",
    "resolve_projection_admissibility",
    "search_world_graph_projection",
]
