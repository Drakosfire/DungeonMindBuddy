"""World Graph projection service (PR007A)."""

from __future__ import annotations

from pathlib import Path

import graph_memory.kernel as kernel
from apps.live_control_server.config import world_graph_root
from graph_memory.kernel.world_projection import WorldGraphProjectionError
from graph_memory.projection.world_projection import (
    PROJECTION_ERROR_SCHEMA,
    WorldGraphProjection,
    WorldGraphProjectionDiagnostic,
    WorldGraphProjectionErrorResponse,
    WorldGraphProjectionRequest,
)


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


def _map_kernel_error(exc: WorldGraphProjectionError) -> WorldGraphProjectionServiceError:
    return WorldGraphProjectionServiceError(
        str(exc),
        code=exc.code,
        status_code=exc.status_code,
        diagnostics=exc.diagnostics,
    )


def project_world_graph(
    request: WorldGraphProjectionRequest,
    *,
    root: Path | None = None,
) -> WorldGraphProjection:
    graph_root = _resolved_root(root)
    try:
        return kernel.project_world_graph(graph_root, request)
    except WorldGraphProjectionError as exc:
        raise _map_kernel_error(exc) from None
    except Exception as exc:
        raise WorldGraphProjectionServiceError(
            "World graph projection failed unexpectedly.",
            code="projection_internal_error",
            status_code=500,
            diagnostics=[
                WorldGraphProjectionDiagnostic(
                    code="projection_internal_error",
                    message=str(exc),
                    severity="error",
                )
            ],
        ) from None


__all__ = [
    "WorldGraphProjectionServiceError",
    "project_world_graph",
]
