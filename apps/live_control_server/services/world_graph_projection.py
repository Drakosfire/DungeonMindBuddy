"""World Graph projection service (PR007A / OPT01)."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

import graph_memory.kernel as kernel
from apps.live_control_server.config import world_graph_root
from apps.live_control_server.services.world_graph_projection_recipes import (
    register_projection_recipe,
)
from graph_memory.projection.world_projection import (
    PROJECTION_ERROR_SCHEMA,
    WorldGraphProjection,
    WorldGraphProjectionDiagnostic,
    WorldGraphProjectionErrorResponse,
    WorldGraphProjectionRequest,
)
from graph_memory.world_projection_cache import (
    get_cached_projection,
    get_or_build_cached_projection,
    make_projection_cache_key,
    projection_cache_enabled,
)

logger = logging.getLogger(__name__)


class WorldGraphProjectionServiceError(ValueError):
    """Stable service error mapped to the projection API envelope."""

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

    def response(self) -> WorldGraphProjectionErrorResponse:
        return WorldGraphProjectionErrorResponse(
            schema=PROJECTION_ERROR_SCHEMA,
            code=self.code,
            message=str(self),
            status_code=self.status_code,
            diagnostics=self.diagnostics,
        )


def _resolved_root(root: Path | None) -> Path:
    return (root if root is not None else world_graph_root()).resolve()


def _direct_read_active(root: Path | None) -> bool:
    """R.3 dispatch predicate: True when this read executes in DungeonMind.

    Mirrors the legacy router's bypass rule: an explicit root differing from
    the configured production World Graph root is a test/tooling override and
    stays on the file-store path. In ``dungeonmind`` authority mode the
    configured production root is not an override.

    The direct-read rollout gate (``DUNGEONMIND_WORLD_GRAPH_DIRECT_READ=1``)
    is a separate opt-in on top of authority mode: the R.3 performance
    witness found the direct path product-breaking on the warm-projection
    surface, so the production switch waits for R.3a read optimization.
    """
    from apps.live_control_server import config
    from graph_memory.world_supergraph import storage

    if config.world_graph_authority_mode() != storage.WORLD_GRAPH_AUTHORITY_DUNGEONMIND:
        return False
    if not config.world_graph_direct_read_enabled():
        return False
    if root is not None and (
        Path(root).resolve() != Path(config.world_graph_root()).resolve()
    ):
        return False
    return True


def _project_world_graph_direct(
    request: WorldGraphProjectionRequest,
) -> WorldGraphProjection:
    """R.3: execute the projection natively in DungeonMind (no Buddy kernel)."""
    from apps.live_control_server import config
    from apps.live_control_server.integrations.dungeonmind import (
        world_graph_reads as direct,
    )

    started = time.perf_counter()
    try:
        services = direct.direct_services_from_config(request.world_id)
        projection = direct.project_world_graph_direct(
            services, request, repo_root=config.repo_root()
        )
    except direct.DirectWorldGraphReadError as exc:
        raise WorldGraphProjectionServiceError(
            str(exc),
            code=exc.code,
            status_code=exc.status_code,
            diagnostics=[
                WorldGraphProjectionDiagnostic(
                    code=str(d.get("code", exc.code)),
                    message=str(d.get("message", str(exc))),
                    severity="error",
                )
                for d in exc.diagnostics
            ]
            or None,
        ) from None
    logger.info(
        "world_graph_projection_direct_observation",
        extra={
            "world_id": request.world_id,
            "campaign_id": request.campaign_id,
            "read_path": "dungeonmind_direct",
            "duration_ms": (time.perf_counter() - started) * 1000.0,
            "nodes_returned": len(projection.nodes),
            "relationships_returned": len(projection.relationships),
            "attributes_returned": len(projection.attributes),
        },
    )
    return projection


def _route_authority_read(
    request: WorldGraphProjectionRequest,
    root: Path | None,
) -> Any:
    """Route the read through the selected World Graph authority.

    Explicit non-production roots (tests) bypass routing. In ``dungeonmind``
    authority mode the read is served from the DungeonMind-hydrated cache root,
    exact revision pins are bridged, and the returned route carries the public
    DungeonMind revision identity for response normalization.
    """
    from apps.live_control_server.integrations.dungeonmind_kernel import (
        world_graph_authority,
    )

    try:
        return world_graph_authority.route_service_read(
            request, root, default_root=world_graph_root()
        )
    except world_graph_authority.WorldGraphAuthorityError as exc:
        raise WorldGraphProjectionServiceError(
            str(exc),
            code=exc.code,
            status_code=world_graph_authority.authority_error_status_code(exc),
            diagnostics=[
                WorldGraphProjectionDiagnostic(
                    code=exc.code,
                    message=str(exc),
                    severity="error",
                )
            ],
        ) from None


def _normalize_authority_identity(
    projection: WorldGraphProjection,
    route: Any,
) -> WorldGraphProjection:
    """Rewrite private hydrated-cache revision ids to public DungeonMind ids.

    The hydrated cache's Buddy content-addressed revision ids are an internal
    implementation detail; product-visible revision/head identity names the
    selected/current DungeonMind revision so a returned id is exactly
    re-pinnable against the authority.
    """
    if route.public_revision_id is None or projection.snapshot is None:
        return projection
    snapshot = projection.snapshot.model_copy(
        update={
            "revision_id": route.public_revision_id,
            "head_revision_id": route.public_head_revision_id,
            "is_head": route.public_revision_id == route.public_head_revision_id,
        }
    )
    return projection.model_copy(update={"snapshot": snapshot})


def _map_kernel_error(
    exc: kernel.WorldGraphProjectionError,
) -> WorldGraphProjectionServiceError:
    return WorldGraphProjectionServiceError(
        str(exc),
        code=exc.code,
        status_code=exc.status_code,
        diagnostics=exc.diagnostics,
    )


def _emit_observation(observation: kernel.ProjectionRequestObservation) -> None:
    logger.info(
        "world_graph_projection_observation",
        extra={
            "world_id": observation.world_id,
            "campaign_id": observation.campaign_id,
            "selected_revision_id": observation.selected_revision_id,
            "head_revision_id": observation.head_revision_id,
            "resident_status": observation.resident_status,
            "selected_resident_generation": observation.selected_resident_generation,
            "head_resident_generation": observation.head_resident_generation,
            "backing_health": observation.backing_health,
            "head_resolution_ms": observation.head_resolution_ms,
            "resident_wait_ms": observation.resident_wait_ms,
            "cold_load_ms": observation.cold_load_ms,
            "projection_cache_status": observation.projection_cache_status,
            "projection_build_ms": observation.projection_build_ms,
            "resident_revision_count": observation.resident_revision_count,
            "graph_payload_reads_this_request": observation.graph_payload_reads_this_request,
            "revision_manifest_reads_this_request": (
                observation.revision_manifest_reads_this_request
            ),
            "contribution_reads_this_request": observation.contribution_reads_this_request,
            "source_index_reads_this_request": observation.source_index_reads_this_request,
            "nodes_returned": observation.nodes_returned,
            "relationships_returned": observation.relationships_returned,
            "attributes_returned": observation.attributes_returned,
        },
    )


def _sync_observation_from_counters(
    observation: kernel.ProjectionRequestObservation,
    counters: kernel.RequestIoCounters,
) -> None:
    observation.resident_status = counters.last_resident_status
    observation.resident_wait_ms = counters.resident_wait_ms
    observation.cold_load_ms = counters.cold_load_ms
    observation.resident_revision_count = (
        kernel.get_world_read_runtime().resident_count()
    )
    observation.graph_payload_reads_this_request = counters.graph_payload_reads
    observation.revision_manifest_reads_this_request = counters.revision_manifest_reads
    observation.contribution_reads_this_request = counters.contribution_reads
    observation.source_index_reads_this_request = counters.source_index_reads


def _register_recipe_best_effort(
    request: WorldGraphProjectionRequest,
    *,
    graph_root: Path,
) -> None:
    try:
        register_projection_recipe(request, root=graph_root)
    except Exception:
        logger.exception("projection recipe registration failed")


def project_world_graph(
    request: WorldGraphProjectionRequest,
    *,
    root: Path | None = None,
) -> WorldGraphProjection:
    if _direct_read_active(root):
        return _project_world_graph_direct(request)
    route = _route_authority_read(request, root)
    graph_root, request = route.graph_root, route.request
    counters = kernel.begin_request_io()
    observation = kernel.ProjectionRequestObservation(
        world_id=request.world_id,
        campaign_id=request.campaign_id,
    )
    try:
        # Request-only policy must win over storage failures.
        request = kernel.validate_projection_request_policy(request)
        observation.world_id = request.world_id
        observation.campaign_id = request.campaign_id

        head_started = time.perf_counter()
        context = kernel.resolve_projection_read_context(graph_root, request)
        observation.head_resolution_ms = (time.perf_counter() - head_started) * 1000.0
        observation.selected_revision_id = context.selected_revision_id
        observation.head_revision_id = context.head_revision_id
        observation.selected_resident_generation = context.selected.generation
        observation.head_resident_generation = context.head.generation
        observation.backing_health = context.selected.backing_health
        _sync_observation_from_counters(observation, counters)

        cache_enabled = projection_cache_enabled()
        cache_key = None
        projection: WorldGraphProjection | None = None
        if cache_enabled:
            cache_key = make_projection_cache_key(
                graph_root,
                request,
                revision_id=context.selected_revision_id,
                head_revision_id=context.head_revision_id,
                selected_resident_generation=context.selected.generation,
                head_resident_generation=context.head.generation,
            )
            cached = get_cached_projection(cache_key)
            if cached is not None:
                observation.projection_cache_status = "hit"
                observation.nodes_returned = len(cached.nodes)
                observation.relationships_returned = len(cached.relationships)
                observation.attributes_returned = len(cached.attributes)
                kernel.set_last_projection_observation(observation)
                _emit_observation(observation)
                _register_recipe_best_effort(request, graph_root=graph_root)
                return _normalize_authority_identity(cached, route)

            def _builder() -> WorldGraphProjection:
                return kernel.project_world_graph_from_context(
                    graph_root,
                    request,
                    context,
                )

            build_started = time.perf_counter()
            projection, cache_status = get_or_build_cached_projection(
                cache_key, _builder
            )
            observation.projection_build_ms = (
                time.perf_counter() - build_started
            ) * 1000.0
            observation.projection_cache_status = cache_status
        else:
            observation.projection_cache_status = "disabled"
            build_started = time.perf_counter()
            projection = kernel.project_world_graph_from_context(
                graph_root,
                request,
                context,
            )
            observation.projection_build_ms = (
                time.perf_counter() - build_started
            ) * 1000.0

        observation.nodes_returned = len(projection.nodes)
        observation.relationships_returned = len(projection.relationships)
        observation.attributes_returned = len(projection.attributes)

        kernel.set_last_projection_observation(observation)
        _emit_observation(observation)
        _register_recipe_best_effort(request, graph_root=graph_root)
        return _normalize_authority_identity(projection, route)
    except kernel.WorldGraphProjectionError as exc:
        _sync_observation_from_counters(observation, counters)
        kernel.set_last_projection_observation(observation)
        _emit_observation(observation)
        raise _map_kernel_error(exc) from None
    except Exception:
        _sync_observation_from_counters(observation, counters)
        kernel.set_last_projection_observation(observation)
        _emit_observation(observation)
        raise WorldGraphProjectionServiceError(
            "World graph projection failed unexpectedly.",
            code="projection_internal_error",
            status_code=500,
            diagnostics=[
                WorldGraphProjectionDiagnostic(
                    code="projection_internal_error",
                    message="World graph projection failed unexpectedly.",
                    severity="error",
                )
            ],
        ) from None
    finally:
        kernel.reset_request_io()


__all__ = [
    "WorldGraphProjectionServiceError",
    "project_world_graph",
]
