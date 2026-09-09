"""Surface-neutral complete World-object projection (#697).

One DungeonMind ``get_complete_object`` plus one APP-STATE batch source read.
Campaign/session focus never determines World membership. Filesystem
provenance is not used.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from apps.live_control_server.config import (
    WorldGraphAuthorityConfigurationError,
    require_mounted_dungeonmind_world_graph,
)
from apps.live_control_server.integrations.dungeonmind.world_graph_reads import (
    DirectWorldGraphReadError,
    extract_span_from_revision_bound_text,
    get_complete_object_direct,
)
from apps.live_control_server.models.world_graph_object_projection import (
    WorldGraphObjectProjectionRequest,
    WorldGraphObjectProjectionResult,
    WorldGraphObjectProjectionSourceBinding,
    WorldGraphObjectProjectionTelemetry,
    object_projection_semantic_fingerprint,
)
from apps.live_control_server.services.world_graph_retrieval import (
    WorldGraphRetrievalServiceError,
)
from application_state.errors import ApplicationStateError
from application_state.source.service import get_source_markdown_batch
from graph_memory.projection.world_projection import WorldGraphProjectionNodeView


class WorldGraphObjectProjectionServiceError(WorldGraphRetrievalServiceError):
    """Stable product error for the complete-object read."""


def _map_configuration_error(
    exc: WorldGraphAuthorityConfigurationError,
) -> WorldGraphObjectProjectionServiceError:
    return WorldGraphObjectProjectionServiceError(
        str(exc),
        code=exc.code,
        status_code=400,
    )


def _map_direct_error(exc: DirectWorldGraphReadError) -> WorldGraphObjectProjectionServiceError:
    return WorldGraphObjectProjectionServiceError(
        str(exc),
        code=exc.code,
        status_code=exc.status_code,
    )


def _hydrate_adjacency(
    node: WorldGraphProjectionNodeView,
    *,
    bindings_by_evidence: dict[str, WorldGraphObjectProjectionSourceBinding],
    markdown_by_digest: dict[tuple[str, str], Any],
) -> WorldGraphProjectionNodeView:
    adjacency = []
    for candidate in node.adjacency:
        excerpt = None
        is_full = False
        status_excerpt = None
        for evidence_ref_id in candidate.evidence_ref_ids:
            binding = bindings_by_evidence.get(evidence_ref_id)
            if binding is None:
                continue
            if binding.excerpt:
                excerpt = binding.excerpt
                is_full = True
                status_excerpt = binding
                break
        adjacency.append(
            candidate.model_copy(
                update={
                    "source_excerpt": excerpt,
                    "source_excerpt_is_full_paragraph": is_full,
                    "source_excerpt_highlight_spans": (
                        [] if status_excerpt is None else candidate.source_excerpt_highlight_spans
                    ),
                }
            )
        )
    return node.model_copy(update={"adjacency": adjacency})


def _apply_durable_bindings(
    result: WorldGraphObjectProjectionResult,
    *,
    records: dict[tuple[str, str], Any],
) -> list[WorldGraphObjectProjectionSourceBinding]:
    updated: list[WorldGraphObjectProjectionSourceBinding] = []
    for binding in result.source_bindings:
        digest = (binding.content_sha256 or "").strip().lower()
        if not digest:
            updated.append(binding)
            continue
        record = records.get((binding.source_artifact_id, digest))
        if record is None:
            updated.append(
                binding.model_copy(update={"provenance_status": "source_not_durable"})
            )
            continue
        media = (record.media_type or "").split(";")[0].strip().lower()
        if media not in {"text/markdown", "text/plain"}:
            updated.append(
                binding.model_copy(update={"provenance_status": "unsupported_source_media"})
            )
            continue
        span_id = (binding.source_span_ref_id or "").strip()
        if not span_id:
            updated.append(
                binding.model_copy(update={"provenance_status": "no_source_span"})
            )
            continue
        extracted = extract_span_from_revision_bound_text(
            text=record.markdown,
            span_id=span_id,
            digest=digest,
        )
        if extracted is None or not extracted[0].strip():
            updated.append(
                binding.model_copy(update={"provenance_status": "span_unresolvable"})
            )
            continue
        updated.append(
            binding.model_copy(
                update={
                    "provenance_status": "excerpt_ready",
                    "excerpt": extracted[0],
                }
            )
        )
    return updated


def project_complete_world_object(
    request: WorldGraphObjectProjectionRequest,
    *,
    root: Path | None = None,
    source_batch_fn=get_source_markdown_batch,
) -> WorldGraphObjectProjectionResult:
    """One authority read + one APP-STATE batch join. No filesystem fallback."""
    started = time.perf_counter()
    try:
        require_mounted_dungeonmind_world_graph(world_root=root)
    except WorldGraphAuthorityConfigurationError as exc:
        raise _map_configuration_error(exc) from None

    from apps.live_control_server.integrations.dungeonmind import (
        world_graph_reads as direct,
    )

    world_started = time.perf_counter()
    try:
        authority = get_complete_object_direct(
            direct.direct_services_from_config(request.world_id),
            request,
        )
    except DirectWorldGraphReadError as exc:
        raise _map_direct_error(exc) from None
    world_read_ms = (time.perf_counter() - world_started) * 1000.0

    if not authority.found or authority.node is None or authority.snapshot is None:
        authority.telemetry.world_read_ms = world_read_ms
        authority.telemetry.total_ms = (time.perf_counter() - started) * 1000.0
        return authority

    batch_started = time.perf_counter()
    try:
        records = source_batch_fn(
            bindings=[
                (row.source_artifact_id, row.content_sha256)
                for row in authority.source_bindings
                if row.content_sha256
            ]
        )
    except ApplicationStateError as exc:
        raise WorldGraphObjectProjectionServiceError(
            f"durable source authority is unavailable: {exc}",
            code="source_authority_unavailable",
            status_code=503,
        ) from exc
    source_batch_read_ms = (time.perf_counter() - batch_started) * 1000.0

    hydrate_started = time.perf_counter()
    source_bindings = _apply_durable_bindings(authority, records=records)
    bindings_by_evidence = {row.evidence_ref_id: row for row in source_bindings}
    node = _hydrate_adjacency(
        authority.node,
        bindings_by_evidence=bindings_by_evidence,
        markdown_by_digest=records,
    )
    related_nodes = [
        _hydrate_adjacency(
            related,
            bindings_by_evidence=bindings_by_evidence,
            markdown_by_digest=records,
        )
        for related in authority.related_nodes
    ]
    provenance_hydration_ms = (time.perf_counter() - hydrate_started) * 1000.0

    fingerprint = object_projection_semantic_fingerprint(
        revision_id=authority.snapshot.revision_id,
        node_id=authority.resolved_node_id or request.node_id,
        admissibility=authority.snapshot.admissibility,
        assertions=list(authority.assertions),
        relationships=list(authority.relationships),
        related_node_ids=[item.node_id for item in related_nodes],
        source_bindings=source_bindings,
    )
    hits = sum(1 for row in source_bindings if row.provenance_status == "excerpt_ready")
    misses = sum(
        1
        for row in source_bindings
        if row.provenance_status in {"source_not_durable", "source_binding_unavailable"}
    )
    temporally_qualified = sum(
        1
        for row in (*authority.assertions, *authority.relationships)
        if row.temporal_scope is not None
    )
    serialize_started = time.perf_counter()
    result = authority.model_copy(
        update={
            "node": node,
            "related_nodes": related_nodes,
            "source_bindings": source_bindings,
            "semantic_fingerprint": fingerprint,
            "telemetry": WorldGraphObjectProjectionTelemetry(
                world_read_ms=world_read_ms,
                source_batch_read_ms=source_batch_read_ms,
                provenance_hydration_ms=provenance_hydration_ms,
                relationship_count=len(authority.relationships),
                assertion_count=len(authority.assertions),
                evidence_count=len(source_bindings),
                temporally_qualified_fact_count=temporally_qualified,
                distinct_source_binding_count=len(
                    {
                        (row.source_artifact_id, row.content_sha256)
                        for row in source_bindings
                        if row.content_sha256
                    }
                ),
                durable_source_hit_count=hits,
                durable_source_miss_count=misses,
                excerpt_count=hits,
                completeness=authority.completeness.status,
                truncated_fields=list(authority.completeness.truncated_fields),
            ),
        }
    )
    result.telemetry.serialization_ms = (time.perf_counter() - serialize_started) * 1000.0
    result.telemetry.total_ms = (time.perf_counter() - started) * 1000.0
    return result
