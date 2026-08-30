"""World Graph projection service (PR007A / OPT01 / CUTOVER D.3A)."""

from __future__ import annotations

import logging
import time

from apps.live_control_server.config import (
    WorldGraphAuthorityConfigurationError,
    require_mounted_dungeonmind_world_graph,
)
from graph_memory.projection.world_projection import (
    PROJECTION_ERROR_SCHEMA,
    WorldGraphProjection,
    WorldGraphProjectionDiagnostic,
    WorldGraphProjectionErrorResponse,
    WorldGraphProjectionRequest,
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


def _map_configuration_error(
    exc: WorldGraphAuthorityConfigurationError,
) -> WorldGraphProjectionServiceError:
    return WorldGraphProjectionServiceError(
        str(exc),
        code=exc.code,
        status_code=400,
        diagnostics=[
            WorldGraphProjectionDiagnostic(
                code=exc.code,
                message=str(exc),
                severity="error",
            )
        ],
    )


def _require_mounted_native_read(root) -> None:
    """Fail closed for retired modes and alternate world_root (no Kernel escape)."""
    try:
        require_mounted_dungeonmind_world_graph(world_root=root)
    except WorldGraphAuthorityConfigurationError as exc:
        raise _map_configuration_error(exc) from None


def _project_world_graph_direct(
    request: WorldGraphProjectionRequest,
) -> WorldGraphProjection:
    """Execute projection natively in DungeonMind (no Buddy kernel)."""
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


def project_world_graph(
    request: WorldGraphProjectionRequest,
    *,
    root=None,
) -> WorldGraphProjection:
    """Mounted projection is DungeonMind-only; alternate-root/Kernel paths fail closed."""
    _require_mounted_native_read(root)
    return _project_world_graph_direct(request)


__all__ = [
    "WorldGraphProjectionServiceError",
    "project_world_graph",
]
