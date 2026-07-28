"""World Graph projection service (PR007A)."""

from __future__ import annotations

import os
from pathlib import Path

import graph_memory.kernel as kernel
from apps.live_control_server.config import world_graph_root
from graph_memory.projection.world_projection import (
    PROJECTION_ERROR_SCHEMA,
    WorldGraphProjection,
    WorldGraphProjectionDiagnostic,
    WorldGraphProjectionErrorResponse,
    WorldGraphProjectionRequest,
)
from graph_memory.world_projection_cache import (
    get_cached_projection,
    make_projection_cache_key,
    put_cached_projection,
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


def _map_kernel_error(exc: kernel.WorldGraphProjectionError) -> WorldGraphProjectionServiceError:
    return WorldGraphProjectionServiceError(
        str(exc),
        code=exc.code,
        status_code=exc.status_code,
        diagnostics=exc.diagnostics,
    )


def _service_cache_enabled() -> bool:
    """Process cache for live UI warm loads.

    Default on for the live server. Cache keys fingerprint the contribution
    ledger plus integrity-checked head/revision payloads so warm hits cannot
    hide projection_integrity_error failures.
    """
    raw = (os.environ.get("DMB_WORLD_GRAPH_PROJECTION_CACHE") or "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def project_world_graph(
    request: WorldGraphProjectionRequest,
    *,
    root: Path | None = None,
) -> WorldGraphProjection:
    graph_root = _resolved_root(root)
    try:
        cache_key = None
        if _service_cache_enabled() and not request.query_text:
            try:
                head = kernel.open_world_graph_head(graph_root, request.world_id)
                revision_id = request.revision_pin or head.head_revision_id
                cache_key = make_projection_cache_key(
                    graph_root,
                    request,
                    revision_id=revision_id,
                    head_revision_id=head.head_revision_id,
                )
                cached = get_cached_projection(cache_key)
                if cached is not None:
                    return cached
            except Exception:
                cache_key = None

        projection = kernel.project_world_graph(graph_root, request)
        if cache_key is not None and projection.snapshot.revision_id == cache_key.revision_id:
            put_cached_projection(cache_key, projection)
        return projection
    except kernel.WorldGraphProjectionError as exc:
        raise _map_kernel_error(exc) from None
    except Exception:
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


__all__ = [
    "WorldGraphProjectionServiceError",
    "project_world_graph",
]
