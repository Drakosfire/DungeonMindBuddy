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


def _outgoing_statblock_bindings(
    projection: WorldGraphProjection,
    threat_node_id: str,
) -> list[tuple[WorldGraphProjectionRelationshipView, ThreatStatblockBindingV1]]:
    found: list[tuple[WorldGraphProjectionRelationshipView, ThreatStatblockBindingV1]] = []
    for rel in projection.relationships:
        if rel.predicate != _USES_STATBLOCK:
            continue
        if rel.source_node_id != threat_node_id:
            continue
        binding = rel.threat_statblock_binding
        if binding is None:
            continue
        found.append((rel, binding))
    # Deterministic presentation order only — never selection authority.
    found.sort(key=lambda item: (item[1].role, item[1].binding_id, item[0].edge_id))
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
    client: ExactRevisionClient,
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
            update={"hydration_status": "unavailable", "message": "mechanics omitted by request"}
        )
    try:
        revision = client.get_exact_revision(binding.statblock_id, binding.revision_id)
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
    if statuses == {"available"}:
        return "hydrated"
    if "integrity_failure" in statuses and not (
        statuses & {"available", "unavailable", "exact_revision_missing"}
    ):
        return "integrity_failure"
    if "available" in statuses and statuses - {"available"}:
        return "partial"
    if statuses <= {"unavailable", "exact_revision_missing"}:
        return "unavailable"
    if "available" in statuses:
        return "partial"
    if "integrity_failure" in statuses:
        return "integrity_failure"
    return "unavailable"


def _collect_threat_hits(
    projection: WorldGraphProjection,
    request: ThreatQueryHydrationRequestV1,
) -> list[tuple[WorldGraphProjectionNodeView, list[str], list[WorldGraphProjectionRelationshipView]]]:
    matched_ids: list[str] = []
    reasons: dict[str, list[str]] = {}
    if projection.query_context is not None:
        matched_ids = list(projection.query_context.matched_node_ids)
        reasons = {
            key: list(value)
            for key, value in (projection.query_context.match_reasons or {}).items()
        }
    nodes_by_id = {node.node_id: node for node in projection.nodes}
    hits: list[
        tuple[WorldGraphProjectionNodeView, list[str], list[WorldGraphProjectionRelationshipView]]
    ] = []
    seen: set[str] = set()

    candidate_ids = matched_ids or [node.node_id for node in projection.nodes]
    predicate_filter = {p.casefold() for p in request.relationship_predicates}

    for node_id in candidate_ids:
        if node_id in seen:
            continue
        node = nodes_by_id.get(node_id)
        if node is None or not _is_threat_node(node):
            continue
        rels = [
            rel
            for rel in projection.relationships
            if _relationship_involves_node(rel, node.node_id)
            and (
                not predicate_filter
                or (rel.predicate or "").casefold() in predicate_filter
            )
        ]
        if request.focus_node_ids:
            focus = set(request.focus_node_ids)
            if node.node_id not in focus and not any(
                rel.source_node_id in focus or rel.target_node_id in focus for rel in rels
            ):
                # Still allow direct query matches without focus adjacency.
                if node.node_id not in matched_ids:
                    continue
        seen.add(node.node_id)
        hits.append((node, list(reasons.get(node.node_id) or []), rels))
        if len(hits) >= request.max_hits:
            break
    return hits


def query_threats_with_hydration(
    request: ThreatQueryHydrationRequestV1,
    *,
    root: Path | None = None,
    client: ExactRevisionClient | None = None,
    project_fn: Callable[..., WorldGraphProjection] | None = None,
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
        scope_mode="campaign",
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

    if projection.snapshot.revision_id != request.revision_pin:
        raise ThreatQueryHydrationError(
            "projection revision_id does not match requested revision_pin",
            result_label="threat_query_hydration_integrity_failure",
            status_code=500,
            diagnostics=["revision_pin_mismatch"],
        )

    statblock_client: ExactRevisionClient = client or build_statblock_v1_client()
    raw_hits = _collect_threat_hits(projection, request)
    response_hits: list[ThreatQueryHydrationHitV1] = []
    diagnostics: list[str] = []

    for threat, match_reasons, relationships in raw_hits:
        binding_pairs = _outgoing_statblock_bindings(projection, threat.node_id)
        hydrated: list[ThreatBindingHydrationV1] = []
        for rel, binding in binding_pairs:
            item = _hydrate_binding(
                threat_node_id=threat.node_id,
                rel=rel,
                binding=binding,
                projection=projection,
                client=statblock_client,
                include_mechanics=request.include_mechanics,
            )
            hydrated.append(item)
            if item.message:
                diagnostics.append(f"{threat.node_id}:{item.binding_id}:{item.hydration_status}")
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
    if not response_hits:
        label: ThreatQueryHydrationResultLabel = "threat_query_hydration_empty"
    elif any(hit.mechanics_disposition in {"partial", "unavailable"} for hit in response_hits) or any(
        b.hydration_status != "available"
        for hit in response_hits
        for b in hit.bindings
        if hit.mechanics_disposition != "no_binding"
    ):
        # partial when at least one hit has mixed/unavailable hydration; ok when all hydrated or no_binding
        if all(
            hit.mechanics_disposition in {"hydrated", "no_binding"} for hit in response_hits
        ):
            label = "threat_query_hydration_ok"
        elif any(hit.mechanics_disposition == "integrity_failure" for hit in response_hits) and all(
            hit.mechanics_disposition in {"integrity_failure", "no_binding"}
            for hit in response_hits
        ):
            label = "threat_query_hydration_ok"
        else:
            label = "threat_query_hydration_partial"
    else:
        label = "threat_query_hydration_ok"

    return ThreatQueryHydrationResponseV1(
        schema=QUERY_RESPONSE_SCHEMA,
        world_id=request.world_id,
        campaign_id=request.campaign_id,
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
