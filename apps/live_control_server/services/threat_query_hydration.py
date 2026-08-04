"""SBW10a: exact Threat query + per-binding immutable mechanics hydration.

Read-only composition over World Graph projection and the server-owned
DungeonMind exact-revision client. No durable writes. No latest/name/corpus
fallback. No first-win binding selection.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable, Protocol

from apps.live_control_server.config import world_graph_root
from apps.live_control_server.integrations.dungeonmind_statblocks.client import (
    build_statblock_v1_client,
    verify_exact_revision_mechanics_integrity,
)
from apps.live_control_server.integrations.dungeonmind_statblocks.errors import (
    StatblockIntegrationError,
)
from apps.live_control_server.integrations.dungeonmind_statblocks.models import (
    ExactRevisionResourceV1,
)
from apps.live_control_server.models.threat_query_hydration import (
    QUERY_RESPONSE_SCHEMA,
    ThreatBindingHydrationV1,
    ThreatQueryHydrationHitV1,
    ThreatQueryHydrationRequestV1,
    ThreatQueryHydrationResponseV1,
    ThreatQueryHydrationResultLabel,
)
from apps.live_control_server.services.world_graph_projection import (
    WorldGraphProjectionServiceError,
    project_world_graph,
)
from graph_memory.projection.world_projection import (
    PROJECTION_REQUEST_SCHEMA,
    WorldGraphProjection,
    WorldGraphProjectionFocus,
    WorldGraphProjectionNodeView,
    WorldGraphProjectionRelationshipView,
    WorldGraphProjectionRequest,
)
from graph_memory.union_supergraph.statblock_binding import (
    PROVIDER,
    ThreatStatblockBindingV1,
    compute_binding_id,
    edge_id_from_binding_id,
    external_statblock_node_id,
)

_USES_STATBLOCK = "uses_statblock"
_THREAT_KINDS = frozenset({"threat", "creature", "npc", "monster"})


class ExactRevisionClient(Protocol):
    def get_exact_revision(
        self, statblock_id: str, revision_id: str
    ) -> ExactRevisionResourceV1: ...


class ThreatQueryHydrationError(Exception):
    """Typed service failure for route mapping."""

    def __init__(
        self,
        message: str,
        *,
        result_label: ThreatQueryHydrationResultLabel,
        status_code: int,
        diagnostics: list[str] | None = None,
    ) -> None:
        super().__init__(message)
        self.result_label = result_label
        self.status_code = status_code
        self.diagnostics = list(diagnostics or [])


def _resolved_root(root: Path | None) -> Path:
    return (root if root is not None else world_graph_root()).resolve()


def _is_threat_node(node: WorldGraphProjectionNodeView) -> bool:
    kind = (node.kind or "").casefold()
    role = (node.role or "").casefold()
    if kind in _THREAT_KINDS or role in _THREAT_KINDS:
        return True
    return kind == "entity" and role in {"threat", "antagonist", "creature"}


def _deterministic_hit_sort_key(hit: ThreatQueryHydrationHitV1) -> tuple[str, str]:
    return ((hit.threat.label or "").casefold(), hit.threat.node_id)


def _relationship_involves_node(
    rel: WorldGraphProjectionRelationshipView, node_id: str
) -> bool:
    return rel.source_node_id == node_id or rel.target_node_id == node_id


def _other_endpoint(rel: WorldGraphProjectionRelationshipView, node_id: str) -> str | None:
    if rel.source_node_id == node_id:
        return rel.target_node_id
    if rel.target_node_id == node_id:
        return rel.source_node_id
    return None


def _predicate_admitted(
    rel: WorldGraphProjectionRelationshipView, predicate_filter: set[str]
) -> bool:
    if not predicate_filter:
        return True
    return (rel.predicate or "").casefold() in predicate_filter


def _resource_endpoint_for_threat(
    rel: WorldGraphProjectionRelationshipView, threat_node_id: str
) -> str | None:
    if rel.source_node_id == threat_node_id:
        return rel.target_node_id
    if rel.target_node_id == threat_node_id:
        return rel.source_node_id
    return None


def _malformed_binding_result(
    *,
    threat_node_id: str,
    rel: WorldGraphProjectionRelationshipView,
    message: str,
    binding: ThreatStatblockBindingV1 | None = None,
) -> ThreatBindingHydrationV1:
    """Integrity-failed edge result without fabricating binding locators.

    When the typed binding payload is absent, ``binding_id`` / statblock /
    revision / digest stay null and only ``relationship_edge_id`` identifies
    the graph edge. An edge ID is never overloaded as a binding ID.
    """
    if binding is not None:
        return ThreatBindingHydrationV1(
            relationship_edge_id=rel.edge_id,
            binding_id=binding.binding_id,
            binding_role=binding.role,
            threat_node_id=threat_node_id,
            resource_node_id=_resource_endpoint_for_threat(rel, threat_node_id),
            provider="dungeonmind",
            statblock_id=binding.statblock_id,
            revision_id=binding.revision_id,
            definition_digest=binding.definition_digest,
            hydration_status="integrity_failure",
            binding=binding,
            revision=None,
            message=message,
        )
    return ThreatBindingHydrationV1(
        relationship_edge_id=rel.edge_id,
        binding_id=None,
        binding_role=None,
        threat_node_id=threat_node_id,
        resource_node_id=_resource_endpoint_for_threat(rel, threat_node_id),
        provider="dungeonmind",
        statblock_id=None,
        revision_id=None,
        definition_digest=None,
        hydration_status="integrity_failure",
        binding=None,
        revision=None,
        message=message,
    )


def _enumerate_statblock_bindings(
    projection: WorldGraphProjection,
    threat_node_id: str,
) -> list[tuple[WorldGraphProjectionRelationshipView, ThreatStatblockBindingV1 | None, str | None]]:
    """Enumerate every uses_statblock edge involving the Threat.

    Valid outgoing bindings return ``(rel, binding, None)``. Malformed edges
    return ``(rel, binding_or_None, integrity_message)``. Never silently drop
    a uses_statblock edge as ordinary no_binding absence.
    """
    found: list[
        tuple[WorldGraphProjectionRelationshipView, ThreatStatblockBindingV1 | None, str | None]
    ] = []
    seen_edge_ids: set[str] = set()
    seen_binding_ids: set[str] = set()

    for rel in projection.relationships:
        if rel.predicate != _USES_STATBLOCK:
            continue
        involves_threat = _relationship_involves_node(rel, threat_node_id)
        if not involves_threat:
            continue

        if rel.edge_id in seen_edge_ids:
            found.append(
                (
                    rel,
                    rel.threat_statblock_binding,
                    "duplicate_binding_edge_identity",
                )
            )
            continue
        seen_edge_ids.add(rel.edge_id)

        if rel.source_node_id != threat_node_id:
            found.append(
                (
                    rel,
                    rel.threat_statblock_binding,
                    "uses_statblock_wrong_endpoint",
                )
            )
            continue

        if (rel.direction or "").casefold() != "outgoing":
            found.append(
                (
                    rel,
                    rel.threat_statblock_binding,
                    "uses_statblock_wrong_direction",
                )
            )
            continue

        binding = rel.threat_statblock_binding
        if binding is None:
            found.append((rel, None, "uses_statblock_binding_missing"))
            continue

        if binding.binding_id in seen_binding_ids:
            found.append((rel, binding, "duplicate_binding_identity"))
            continue
        seen_binding_ids.add(binding.binding_id)

        found.append((rel, binding, None))

    found.sort(
        key=lambda item: (
            (item[1].role if item[1] is not None else ""),
            (item[1].binding_id if item[1] is not None else item[0].edge_id),
            item[0].edge_id,
        )
    )
    return found


def _resource_node_for(
    projection: WorldGraphProjection, resource_node_id: str
) -> WorldGraphProjectionNodeView | None:
    for node in projection.nodes:
        if node.node_id == resource_node_id:
            return node
    return None


def _validate_binding_against_resource(
    *,
    binding: ThreatStatblockBindingV1,
    rel: WorldGraphProjectionRelationshipView,
    threat_node_id: str,
    resource_node: WorldGraphProjectionNodeView | None,
) -> str | None:
    expected_resource_id = external_statblock_node_id(binding.statblock_id)
    if rel.target_node_id != expected_resource_id:
        return "binding_target_resource_mismatch"
    if resource_node is None:
        return "external_resource_node_missing"
    resource = resource_node.external_resource
    if resource is None:
        return "external_resource_missing"
    if resource.provider != PROVIDER or resource.resource_id != binding.statblock_id:
        return "external_resource_identity_mismatch"
    if resource.contract != binding.contract or resource.contract_version != binding.contract_version:
        return "external_resource_contract_mismatch"
    try:
        recomputed = compute_binding_id(
            threat_node_id=threat_node_id,
            provider=binding.provider,
            statblock_id=binding.statblock_id,
            revision_id=binding.revision_id,
            contract=binding.contract,
            contract_version=binding.contract_version,
            definition_digest=binding.definition_digest,
            role=binding.role,
            phase_key=binding.phase_key,
            variant_label=binding.variant_label,
        )
    except Exception as exc:  # noqa: BLE001
        return f"binding_id_recompute_failed:{exc}"
    if recomputed != binding.binding_id:
        return "binding_id_mismatch"
    if rel.edge_id != edge_id_from_binding_id(binding.binding_id):
        return "binding_edge_id_mismatch"
    return None


def _hydrate_binding(
    *,
    threat_node_id: str,
    rel: WorldGraphProjectionRelationshipView,
    binding: ThreatStatblockBindingV1,
    projection: WorldGraphProjection,
    client: ExactRevisionClient | None,
    client_error: str | None,
    include_mechanics: bool,
) -> ThreatBindingHydrationV1:
    resource_node = _resource_node_for(projection, rel.target_node_id)
    disagreement = _validate_binding_against_resource(
        binding=binding,
        rel=rel,
        threat_node_id=threat_node_id,
        resource_node=resource_node,
    )
    base = ThreatBindingHydrationV1(
        relationship_edge_id=rel.edge_id,
        binding_id=binding.binding_id,
        binding_role=binding.role,
        threat_node_id=threat_node_id,
        resource_node_id=rel.target_node_id,
        provider="dungeonmind",
        statblock_id=binding.statblock_id,
        revision_id=binding.revision_id,
        definition_digest=binding.definition_digest,
        hydration_status="integrity_failure" if disagreement else "unavailable",
        binding=binding,
        revision=None,
        message=disagreement,
    )
    if disagreement is not None:
        return base
    if not include_mechanics:
        return base.model_copy(
            update={
                "hydration_status": "not_requested",
                "message": "mechanics omitted by request",
            }
        )
    if client is None:
        return base.model_copy(
            update={
                "hydration_status": "unavailable",
                "message": client_error or "statblock client unavailable",
            }
        )
    try:
        fetched = client.get_exact_revision(binding.statblock_id, binding.revision_id)
        revision = ExactRevisionResourceV1.model_validate(fetched)
        verify_exact_revision_mechanics_integrity(revision)
    except StatblockIntegrationError as exc:
        category = getattr(exc, "category", "") or ""
        if category in {"downstream_not_found", "downstream_expired"}:
            return base.model_copy(
                update={
                    "hydration_status": "exact_revision_missing",
                    "message": str(exc),
                }
            )
        if category in {
            "downstream_unavailable",
            "downstream_timeout",
            "integration_disabled",
            "integration_misconfigured",
            "downstream_authentication_failed",
            "downstream_rate_limited",
        }:
            return base.model_copy(
                update={"hydration_status": "unavailable", "message": str(exc)}
            )
        return base.model_copy(
            update={"hydration_status": "integrity_failure", "message": str(exc)}
        )
    except Exception as exc:  # noqa: BLE001
        return base.model_copy(
            update={"hydration_status": "integrity_failure", "message": str(exc)}
        )

    if revision.statblock_id != binding.statblock_id:
        return base.model_copy(
            update={
                "hydration_status": "integrity_failure",
                "message": "server response statblock_id mismatch",
            }
        )
    if revision.revision_id != binding.revision_id:
        return base.model_copy(
            update={
                "hydration_status": "integrity_failure",
                "message": "server response revision_id mismatch",
            }
        )
    if revision.definition_digest != binding.definition_digest:
        return base.model_copy(
            update={
                "hydration_status": "integrity_failure",
                "message": "definition_digest mismatch",
            }
        )
    return base.model_copy(
        update={
            "hydration_status": "available",
            "revision": revision,
            "message": None,
        }
    )


def _mechanics_disposition(
    bindings: list[ThreatBindingHydrationV1],
) -> str:
    if not bindings:
        return "no_binding"
    statuses = {item.hydration_status for item in bindings}
    effective = statuses - {"not_requested"}
    if not effective:
        return "not_requested"
    if effective == {"available"}:
        return "hydrated"
    if "integrity_failure" in effective and not (
        effective & {"available", "unavailable", "exact_revision_missing"}
    ):
        return "integrity_failure"
    if "available" in effective and effective - {"available"}:
        return "partial"
    if effective <= {"unavailable", "exact_revision_missing"}:
        return "unavailable"
    if "available" in effective:
        return "partial"
    if "integrity_failure" in effective:
        return "integrity_failure"
    return "unavailable"


def _aggregate_result_label(
    hits: list[ThreatQueryHydrationHitV1],
) -> ThreatQueryHydrationResultLabel:
    if not hits:
        return "threat_query_hydration_empty"

    mechanics_bindings = [
        binding
        for hit in hits
        for binding in hit.bindings
        if hit.mechanics_disposition != "no_binding"
    ]
    if not mechanics_bindings:
        return "threat_query_hydration_ok"

    # Intentionally omitted mechanics are not dependency failures.
    statuses = {
        binding.hydration_status
        for binding in mechanics_bindings
        if binding.hydration_status != "not_requested"
    }
    if not statuses:
        return "threat_query_hydration_ok"
    if statuses == {"available"}:
        return "threat_query_hydration_ok"
    if "integrity_failure" in statuses and not (
        statuses & {"available", "unavailable", "exact_revision_missing"}
    ):
        return "threat_query_hydration_integrity_failure"
    return "threat_query_hydration_partial"


def _collect_threat_hits(
    projection: WorldGraphProjection,
    request: ThreatQueryHydrationRequestV1,
) -> list[tuple[WorldGraphProjectionNodeView, list[str], list[WorldGraphProjectionRelationshipView]]]:
    """Derive Threat candidates from direct matches and relationship endpoints.

    Empty ``matched_node_ids`` with an existing query context means zero matches —
    never fall back to every projected Threat. One-hop discovery walks the full
    admitted ``projection.relationships`` using matched and focus IDs as anchors.
    Query context supplies match identity/reasons only — never a relationship
    visibility wall (search relationship caps must not hide Threat edges).
    """
    if projection.query_context is None:
        return []

    matched_ids = list(projection.query_context.matched_node_ids)
    reasons: dict[str, list[str]] = {
        key: list(value)
        for key, value in (projection.query_context.match_reasons or {}).items()
    }
    focus_ids = list(request.focus_node_ids)
    if not matched_ids and not focus_ids:
        return []

    nodes_by_id = {node.node_id: node for node in projection.nodes}
    predicate_filter = {p.casefold() for p in request.relationship_predicates}
    # Full projection edges — not query_context.relationships (SEARCH_MAX capped).
    discovery_rels = list(projection.relationships)

    candidate_reasons: dict[str, list[str]] = {}
    ordered_candidate_ids: list[str] = []
    seen_candidate_ids: set[str] = set()

    def _add_reason(node_id: str, reason: str) -> None:
        bucket = candidate_reasons.setdefault(node_id, [])
        if reason not in bucket:
            bucket.append(reason)

    def _register_candidate(node_id: str) -> None:
        if node_id in seen_candidate_ids:
            return
        node = nodes_by_id.get(node_id)
        if node is None or not _is_threat_node(node):
            return
        seen_candidate_ids.add(node_id)
        ordered_candidate_ids.append(node_id)

    for node_id in matched_ids:
        node = nodes_by_id.get(node_id)
        if node is None or not _is_threat_node(node):
            continue
        for reason in reasons.get(node_id) or ["direct_match"]:
            _add_reason(node_id, reason)
        _register_candidate(node_id)

    for node_id in focus_ids:
        node = nodes_by_id.get(node_id)
        if node is None or not _is_threat_node(node):
            continue
        _add_reason(node_id, f"focus_node:{node_id}")
        _register_candidate(node_id)

    anchors = set(matched_ids) | set(focus_ids)
    for rel in discovery_rels:
        if not _predicate_admitted(rel, predicate_filter):
            continue
        for anchor in (rel.source_node_id, rel.target_node_id):
            if anchor not in anchors:
                continue
            other = _other_endpoint(rel, anchor)
            if other is None:
                continue
            other_node = nodes_by_id.get(other)
            if other_node is None or not _is_threat_node(other_node):
                continue
            _add_reason(
                other,
                f"related_to_match:{anchor}:{rel.predicate}",
            )
            _register_candidate(other)

    hits: list[
        tuple[WorldGraphProjectionNodeView, list[str], list[WorldGraphProjectionRelationshipView]]
    ] = []
    for node_id in ordered_candidate_ids[: request.max_hits]:
        node = nodes_by_id[node_id]
        rels = [
            rel
            for rel in projection.relationships
            if _relationship_involves_node(rel, node.node_id)
            and _predicate_admitted(rel, predicate_filter)
        ]
        hits.append((node, list(candidate_reasons[node_id]), rels))
    return hits


def query_threats_with_hydration(
    request: ThreatQueryHydrationRequestV1,
    *,
    root: Path | None = None,
    client: ExactRevisionClient | None = None,
    project_fn: Callable[..., WorldGraphProjection] | None = None,
    client_factory: Callable[[], ExactRevisionClient] | None = None,
) -> ThreatQueryHydrationResponseV1:
    """Query published Threats in one exact revision and hydrate all bindings."""
    graph_root = _resolved_root(root)
    project = project_fn or project_world_graph
    projection_request = WorldGraphProjectionRequest(
        schema=PROJECTION_REQUEST_SCHEMA,
        world_id=request.world_id,
        campaign_id=request.campaign_id,
        focus=WorldGraphProjectionFocus(kind="none"),
        admissibility="gm",
        revision_pin=request.revision_pin,
        scope_mode=request.scope_mode,
        query_text=request.query_text,
    )
    try:
        projection = project(projection_request, root=graph_root)
    except WorldGraphProjectionServiceError as exc:
        if exc.status_code == 404 or exc.code in {
            "projection_revision_not_found",
            "world_not_found",
        }:
            raise ThreatQueryHydrationError(
                str(exc),
                result_label="threat_query_hydration_not_found",
                status_code=404,
                diagnostics=[exc.code],
            ) from exc
        if exc.status_code == 503 or "unavailable" in exc.code:
            raise ThreatQueryHydrationError(
                str(exc),
                result_label="threat_query_hydration_unavailable",
                status_code=503,
                diagnostics=[exc.code],
            ) from exc
        raise ThreatQueryHydrationError(
            str(exc),
            result_label="threat_query_hydration_integrity_failure",
            status_code=500,
            diagnostics=[exc.code],
        ) from exc

    if (
        projection.snapshot.world_id != request.world_id
        or projection.snapshot.campaign_id != request.campaign_id
        or projection.snapshot.scope_mode != request.scope_mode
        or projection.snapshot.revision_id != request.revision_pin
    ):
        raise ThreatQueryHydrationError(
            "projection scope does not match requested exact graph scope",
            result_label="threat_query_hydration_integrity_failure",
            status_code=500,
            diagnostics=["projection_scope_mismatch"],
        )

    raw_hits = _collect_threat_hits(projection, request)
    response_hits: list[ThreatQueryHydrationHitV1] = []
    diagnostics: list[str] = []

    needs_mechanics_client = False
    pending: list[
        tuple[
            WorldGraphProjectionNodeView,
            list[str],
            list[WorldGraphProjectionRelationshipView],
            list[
                tuple[
                    WorldGraphProjectionRelationshipView,
                    ThreatStatblockBindingV1 | None,
                    str | None,
                ]
            ],
        ]
    ] = []
    for threat, match_reasons, relationships in raw_hits:
        enumerated = _enumerate_statblock_bindings(projection, threat.node_id)
        pending.append((threat, match_reasons, relationships, enumerated))
        if request.include_mechanics and any(
            binding is not None and integrity is None
            for _rel, binding, integrity in enumerated
        ):
            needs_mechanics_client = True

    resolved_client: ExactRevisionClient | None = client
    client_error: str | None = None
    if needs_mechanics_client and resolved_client is None:
        factory = client_factory or build_statblock_v1_client
        try:
            resolved_client = factory()
        except StatblockIntegrationError as exc:
            client_error = str(exc)
            resolved_client = None
        except Exception as exc:  # noqa: BLE001
            client_error = str(exc)
            resolved_client = None

    for threat, match_reasons, relationships, enumerated in pending:
        hydrated: list[ThreatBindingHydrationV1] = []
        for rel, binding, integrity in enumerated:
            if integrity is not None:
                item = _malformed_binding_result(
                    threat_node_id=threat.node_id,
                    rel=rel,
                    message=integrity,
                    binding=binding,
                )
            elif binding is None:
                item = _malformed_binding_result(
                    threat_node_id=threat.node_id,
                    rel=rel,
                    message="uses_statblock_binding_missing",
                )
            else:
                item = _hydrate_binding(
                    threat_node_id=threat.node_id,
                    rel=rel,
                    binding=binding,
                    projection=projection,
                    client=resolved_client,
                    client_error=client_error,
                    include_mechanics=request.include_mechanics,
                )
            hydrated.append(item)
            if item.message:
                locator = item.binding_id or item.relationship_edge_id
                diagnostics.append(
                    f"{threat.node_id}:{locator}:{item.hydration_status}"
                )
        disposition = _mechanics_disposition(hydrated)
        response_hits.append(
            ThreatQueryHydrationHitV1(
                threat=threat,
                match_reasons=match_reasons,
                relationships=relationships,
                bindings=hydrated,
                mechanics_disposition=disposition,  # type: ignore[arg-type]
            )
        )

    response_hits.sort(key=_deterministic_hit_sort_key)
    label = _aggregate_result_label(response_hits)

    return ThreatQueryHydrationResponseV1(
        schema=QUERY_RESPONSE_SCHEMA,
        world_id=request.world_id,
        campaign_id=request.campaign_id,
        scope_mode=request.scope_mode,
        revision_id=projection.snapshot.revision_id,
        query_text=request.query_text,
        result_label=label,
        hits=response_hits,
        diagnostics=diagnostics[:32],
        message=None,
    )


__all__ = [
    "ThreatQueryHydrationError",
    "query_threats_with_hydration",
]
