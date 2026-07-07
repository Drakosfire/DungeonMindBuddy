"""Read-model adapter for layering authored graph overlay into graph review projection."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from apps.live_control_server.models.graph_authoring_overlay import (
    AuthoredGraphAssertion,
    AuthoredGraphLinkExistingAssertion,
    AuthoredGraphObjectAssertion,
    AuthoredGraphObjectRef,
    AuthoredGraphOverlay,
    AuthoredGraphRelationshipAssertion,
    GraphVisibilityPolicy,
)
from apps.live_control_server.services.graph_authoring_overlay_store import (
    GraphAuthoringOverlayStore,
    GraphAuthoringOverlayStoreError,
)
from apps.live_control_server.services.graph_authoring_visibility import (
    GraphAudience,
    filter_authored_overlay_for_audience,
    visibility_policy_from_projection_object,
    visibility_policy_projection_fields,
)
from graph_memory.projection.node_view import (
    GraphProjectionAdjacencyCandidate,
    GraphProjectionNodeView,
)
from graph_memory.projection.recap_projection import RecapGraphProjection

AUTHORED_SOURCE_DOMAIN = "authored_overlay"


class GraphAuthoringOverlayDiagnostic(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    assertion_id: str | None = None
    severity: Literal["info", "warning", "error"] = "warning"


class AuthoredOverlayProjectionSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    loaded: bool
    overlay_path: str | None = None
    assertion_count: int = 0
    projected_node_count: int = 0
    projected_relationship_count: int = 0
    diagnostics: list[GraphAuthoringOverlayDiagnostic] = Field(default_factory=list)


def authored_object_node_id(assertion_id: str) -> str:
    return f"authored:{assertion_id}"


def authored_manual_node_id(label: str, kind: str | None = None) -> str:
    key = f"{label.strip().lower()}|{(kind or '').strip().lower()}"
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]
    return f"authored:manual:{digest}"


def authored_relationship_edge_id(assertion_id: str) -> str:
    return f"authored-rel:{assertion_id}"


def _resolve_store(corpus_root: Path | None) -> GraphAuthoringOverlayStore:
    if corpus_root is None:
        from src.live_play.recap_stage_paths import corpus_root as default_corpus_root

        return GraphAuthoringOverlayStore(default_corpus_root())
    return GraphAuthoringOverlayStore(corpus_root)


def load_authored_overlay_for_review(
    *,
    campaign_id: str,
    campaign_rel: str | None = None,
    corpus_root: Path | None = None,
) -> tuple[AuthoredGraphOverlay | None, AuthoredOverlayProjectionSummary]:
    store = _resolve_store(corpus_root)
    overlay_path = store.overlay_path(campaign_id, campaign_rel=campaign_rel)
    if not overlay_path.is_file():
        return None, AuthoredOverlayProjectionSummary(
            loaded=False,
            overlay_path=str(overlay_path),
            diagnostics=[
                GraphAuthoringOverlayDiagnostic(
                    code="authored_overlay_missing",
                    message="No authored overlay file committed for this campaign yet.",
                    severity="info",
                )
            ],
        )
    try:
        overlay = store.load_overlay(campaign_id, campaign_rel=campaign_rel)
    except (GraphAuthoringOverlayStoreError, ValidationError) as exc:
        return None, AuthoredOverlayProjectionSummary(
            loaded=False,
            overlay_path=str(overlay_path),
            diagnostics=[
                GraphAuthoringOverlayDiagnostic(
                    code="authored_overlay_schema_error",
                    message=str(exc),
                    severity="error",
                )
            ],
        )
    active_assertions = [item for item in overlay.assertions if item.status == "authored"]
    return overlay, AuthoredOverlayProjectionSummary(
        loaded=True,
        overlay_path=str(overlay_path),
        assertion_count=len(active_assertions),
    )


def _local_proposal_node_map(
    assertions: list[AuthoredGraphAssertion],
) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for assertion in assertions:
        if assertion.assertion_kind != "object" or assertion.status != "authored":
            continue
        local_proposal_id = assertion.object_ref.local_proposal_id
        if local_proposal_id:
            mapping[local_proposal_id] = authored_object_node_id(assertion.assertion_id)
    return mapping


def _resolve_object_ref_node_id(
    ref: AuthoredGraphObjectRef,
    *,
    existing_node_ids: set[str],
    local_proposal_nodes: dict[str, str],
    diagnostics: list[GraphAuthoringOverlayDiagnostic],
    assertion_id: str,
    context: str,
) -> str | None:
    if ref.ref_kind == "existing_graph_node":
        if ref.node_id and ref.node_id in existing_node_ids:
            return ref.node_id
        diagnostics.append(
            GraphAuthoringOverlayDiagnostic(
                code="authored_overlay_assertion_unresolved_ref",
                message=f"{context}: existing graph node {ref.node_id!r} was not found in projection.",
                assertion_id=assertion_id,
            )
        )
        return None
    if ref.ref_kind == "local_proposal":
        if ref.local_proposal_id and ref.local_proposal_id in local_proposal_nodes:
            node_id = local_proposal_nodes[ref.local_proposal_id]
            if node_id in existing_node_ids:
                return node_id
        diagnostics.append(
            GraphAuthoringOverlayDiagnostic(
                code="authored_overlay_assertion_unresolved_ref",
                message=f"{context}: local proposal ref {ref.local_proposal_id!r} could not be resolved.",
                assertion_id=assertion_id,
            )
        )
        return None
    if ref.ref_kind == "authored_node":
        if ref.authored_node_id and ref.authored_node_id in existing_node_ids:
            return ref.authored_node_id
        if ref.authored_node_id and ref.authored_node_id.startswith("authored:"):
            return ref.authored_node_id
        diagnostics.append(
            GraphAuthoringOverlayDiagnostic(
                code="authored_overlay_assertion_unresolved_ref",
                message=f"{context}: authored node ref {ref.authored_node_id!r} was not found.",
                assertion_id=assertion_id,
            )
        )
        return None
    if ref.ref_kind == "manual_ref":
        return authored_manual_node_id(ref.label, ref.kind)
    return None


def _authored_node_view(
    *,
    node_id: str,
    label: str,
    kind: str | None,
    role: str | None,
    aliases: list[str],
    summary: str | None,
    assertion_id: str,
    visibility_policy: GraphVisibilityPolicy,
    graph_scope: list[str],
    source_anchor_text: str | None = None,
) -> GraphProjectionNodeView:
    extras: dict[str, Any] = {
        "source": AUTHORED_SOURCE_DOMAIN,
        "authored": True,
        "assertion_id": assertion_id,
        "graph_scope": graph_scope,
        **visibility_policy_projection_fields(visibility_policy),
    }
    if source_anchor_text:
        extras["source_anchor_text"] = source_anchor_text
    return GraphProjectionNodeView(
        node_id=node_id,
        label=label,
        kind=kind or "entity",
        role=role or "authored",
        aliases=list(aliases),
        source_domains=[AUTHORED_SOURCE_DOMAIN],
        evidence_badges=[],
        adjacency=[],
        suggested_expansions=[],
        anchored_to_focus_session=False,
        summary=summary,
        **extras,
    )


def build_authored_projection_node_views(
    overlay: AuthoredGraphOverlay,
    *,
    base_node_views: dict[str, GraphProjectionNodeView] | None = None,
    existing_node_ids: set[str] | None = None,
    diagnostics: list[GraphAuthoringOverlayDiagnostic] | None = None,
) -> dict[str, GraphProjectionNodeView]:
    node_views: dict[str, GraphProjectionNodeView] = {}
    unresolved = diagnostics if diagnostics is not None else []
    known_ids = set(existing_node_ids or ())
    base_views = base_node_views or {}
    active_assertions = [item for item in overlay.assertions if item.status == "authored"]

    for assertion in active_assertions:
        if assertion.assertion_kind != "object":
            continue
        node_id = authored_object_node_id(assertion.assertion_id)
        node_views[node_id] = _authored_node_view(
            node_id=node_id,
            label=assertion.object_ref.label,
            kind=assertion.object_ref.kind,
            role=assertion.object_ref.role,
            aliases=list(assertion.aliases),
            summary=assertion.summary,
            assertion_id=assertion.assertion_id,
            visibility_policy=assertion.visibility,
            graph_scope=list(assertion.graph_scope),
            source_anchor_text=(
                assertion.source_anchor.normalized_selected_text
                if assertion.source_anchor
                else None
            ),
        )
        known_ids.add(node_id)

    for assertion in active_assertions:
        if assertion.assertion_kind != "link_existing":
            continue
        link_assertion: AuthoredGraphLinkExistingAssertion = assertion
        ref = link_assertion.existing_object_ref
        alias_text = (link_assertion.alias_text or link_assertion.normalized_selected_text).strip()
        if ref.ref_kind == "existing_graph_node" and ref.node_id and ref.node_id in known_ids:
            existing = node_views.get(ref.node_id) or base_views.get(ref.node_id)
            if existing is None:
                continue
            updated_aliases = list(existing.aliases)
            if alias_text and alias_text not in updated_aliases:
                updated_aliases.append(alias_text)
            source_domains = list(existing.source_domains)
            if AUTHORED_SOURCE_DOMAIN not in source_domains:
                source_domains.append(AUTHORED_SOURCE_DOMAIN)
            node_views[ref.node_id] = existing.model_copy(
                update={
                    "aliases": updated_aliases,
                    "source_domains": source_domains,
                    "authored": True,
                    "assertion_id": link_assertion.assertion_id,
                    "source_anchor_text": link_assertion.normalized_selected_text,
                    **visibility_policy_projection_fields(link_assertion.visibility),
                }
            )
            continue
        manual_node_id = _resolve_object_ref_node_id(
            ref,
            existing_node_ids=known_ids,
            local_proposal_nodes=_local_proposal_node_map(active_assertions),
            diagnostics=unresolved,
            assertion_id=link_assertion.assertion_id,
            context="link_existing",
        )
        if manual_node_id is None:
            continue
        aliases = [alias_text] if alias_text else []
        if ref.label not in aliases:
            aliases.insert(0, ref.label)
        node_views[manual_node_id] = _authored_node_view(
            node_id=manual_node_id,
            label=ref.label,
            kind=ref.kind,
            role=ref.role,
            aliases=aliases,
            summary=None,
            assertion_id=link_assertion.assertion_id,
            visibility_policy=link_assertion.visibility,
            graph_scope=list(link_assertion.graph_scope),
            source_anchor_text=link_assertion.normalized_selected_text,
        )
        known_ids.add(manual_node_id)

    return node_views


def build_authored_projection_relationship_views(
    overlay: AuthoredGraphOverlay,
    node_views: dict[str, GraphProjectionNodeView],
    *,
    diagnostics: list[GraphAuthoringOverlayDiagnostic] | None = None,
) -> list[GraphProjectionAdjacencyCandidate]:
    unresolved = diagnostics if diagnostics is not None else []
    active_assertions = [item for item in overlay.assertions if item.status == "authored"]
    local_proposal_nodes = _local_proposal_node_map(active_assertions)
    existing_node_ids = set(node_views.keys())
    relationships: list[GraphProjectionAdjacencyCandidate] = []

    for assertion in active_assertions:
        if assertion.assertion_kind != "relationship":
            continue
        rel_assertion: AuthoredGraphRelationshipAssertion = assertion
        source_id = _resolve_object_ref_node_id(
            rel_assertion.source_object_ref,
            existing_node_ids=existing_node_ids,
            local_proposal_nodes=local_proposal_nodes,
            diagnostics=unresolved,
            assertion_id=rel_assertion.assertion_id,
            context="relationship source",
        )
        target_id = _resolve_object_ref_node_id(
            rel_assertion.target_object_ref,
            existing_node_ids=existing_node_ids,
            local_proposal_nodes=local_proposal_nodes,
            diagnostics=unresolved,
            assertion_id=rel_assertion.assertion_id,
            context="relationship target",
        )
        if not source_id or not target_id:
            unresolved.append(
                GraphAuthoringOverlayDiagnostic(
                    code="authored_overlay_relationship_skipped",
                    message=(
                        f"Skipped relationship {rel_assertion.relationship_type} "
                        f"from {rel_assertion.source_object_ref.label} to "
                        f"{rel_assertion.target_object_ref.label} due to unresolved endpoint."
                    ),
                    assertion_id=rel_assertion.assertion_id,
                )
            )
            continue
        if source_id not in node_views or target_id not in node_views:
            unresolved.append(
                GraphAuthoringOverlayDiagnostic(
                    code="authored_overlay_relationship_skipped",
                    message=(
                        f"Skipped relationship {rel_assertion.relationship_type} because "
                        f"endpoint nodes were missing from node views."
                    ),
                    assertion_id=rel_assertion.assertion_id,
                )
            )
            continue
        target_view = node_views[target_id]
        edge_id = authored_relationship_edge_id(rel_assertion.assertion_id)
        predicate = rel_assertion.relationship_type
        edge_label = rel_assertion.relationship_label or (
            f"{node_views[source_id].label} {predicate} {target_view.label}"
        )
        relationships.append(
            GraphProjectionAdjacencyCandidate(
                edge_id=edge_id,
                node_id=target_id,
                label=target_view.label,
                kind=target_view.kind,
                predicate=predicate,
                direction="outgoing",
                anchored_to_focus_session=False,
                source_domains=[AUTHORED_SOURCE_DOMAIN],
                evidence_ref_ids=[],
                edge_label=edge_label,
                session_ids=[rel_assertion.session_id] if rel_assertion.session_id else [],
                source=AUTHORED_SOURCE_DOMAIN,
                authored=True,
                assertion_id=rel_assertion.assertion_id,
                summary=rel_assertion.summary,
                **visibility_policy_projection_fields(rel_assertion.visibility),
            )
        )
    return relationships


def apply_authored_overlay_to_graph_review_projection(
    projection: RecapGraphProjection,
    overlay: AuthoredGraphOverlay | None,
    *,
    summary: AuthoredOverlayProjectionSummary | None = None,
    audience: GraphAudience | None = None,
) -> tuple[RecapGraphProjection, AuthoredOverlayProjectionSummary]:
    if overlay is None:
        return projection, summary or AuthoredOverlayProjectionSummary(loaded=False)

    overlay_for_projection = (
        filter_authored_overlay_for_audience(overlay, audience)
        if audience is not None
        else overlay
    )

    diagnostics: list[GraphAuthoringOverlayDiagnostic] = list(summary.diagnostics if summary else [])
    merged_node_views = dict(projection.node_views)
    authored_nodes = build_authored_projection_node_views(
        overlay_for_projection,
        base_node_views=merged_node_views,
        existing_node_ids=set(merged_node_views.keys()),
        diagnostics=diagnostics,
    )
    for node_id, authored_view in authored_nodes.items():
        if node_id in merged_node_views:
            existing = merged_node_views[node_id]
            merged_aliases = list(existing.aliases)
            for alias in authored_view.aliases:
                if alias not in merged_aliases:
                    merged_aliases.append(alias)
            source_domains = list(existing.source_domains)
            if AUTHORED_SOURCE_DOMAIN not in source_domains:
                source_domains.append(AUTHORED_SOURCE_DOMAIN)
            merged_node_views[node_id] = existing.model_copy(
                update={
                    "aliases": merged_aliases,
                    "source_domains": source_domains,
                    "authored": True,
                    "assertion_id": getattr(authored_view, "assertion_id", None),
                    "source_anchor_text": getattr(authored_view, "source_anchor_text", None),
                    **visibility_policy_projection_fields(
                        visibility_policy_from_projection_object(authored_view)
                    ),
                }
            )
        else:
            merged_node_views[node_id] = authored_view

    relationship_views = build_authored_projection_relationship_views(
        overlay_for_projection,
        merged_node_views,
        diagnostics=diagnostics,
    )
    for relationship in relationship_views:
        source_candidates = [
            assertion
            for assertion in overlay_for_projection.assertions
            if assertion.assertion_kind == "relationship"
            and assertion.status == "authored"
            and authored_relationship_edge_id(assertion.assertion_id) == relationship.edge_id
        ]
        if not source_candidates:
            continue
        rel_assertion = source_candidates[0]
        assert isinstance(rel_assertion, AuthoredGraphRelationshipAssertion)
        source_id = _resolve_object_ref_node_id(
            rel_assertion.source_object_ref,
            existing_node_ids=set(merged_node_views.keys()),
            local_proposal_nodes=_local_proposal_node_map(
                [item for item in overlay_for_projection.assertions if item.status == "authored"]
            ),
            diagnostics=diagnostics,
            assertion_id=rel_assertion.assertion_id,
            context="relationship source",
        )
        if not source_id or source_id not in merged_node_views:
            continue
        source_view = merged_node_views[source_id]
        if any(item.edge_id == relationship.edge_id for item in source_view.adjacency):
            continue
        merged_node_views[source_id] = source_view.model_copy(
            update={"adjacency": [*source_view.adjacency, relationship]}
        )

    active_count = sum(
        1 for item in overlay_for_projection.assertions if item.status == "authored"
    )
    result_summary = AuthoredOverlayProjectionSummary(
        loaded=True,
        overlay_path=summary.overlay_path if summary else None,
        assertion_count=active_count,
        projected_node_count=len(authored_nodes),
        projected_relationship_count=len(relationship_views),
        diagnostics=diagnostics,
    )
    return projection.model_copy(update={"node_views": merged_node_views}), result_summary


def enrich_projection_payload_with_authored_overlay(
    payload: dict[str, Any],
    *,
    campaign_id: str,
    campaign_rel: str | None = None,
    corpus_root: Path | None = None,
) -> dict[str, Any]:
    projection = RecapGraphProjection.model_validate(payload)
    overlay, summary = load_authored_overlay_for_review(
        campaign_id=campaign_id,
        campaign_rel=campaign_rel,
        corpus_root=corpus_root,
    )
    enriched, overlay_summary = apply_authored_overlay_to_graph_review_projection(
        projection,
        overlay,
        summary=summary,
    )
    result = enriched.model_dump(mode="json")
    result["authored_overlay"] = overlay_summary.model_dump(mode="json")
    return result
