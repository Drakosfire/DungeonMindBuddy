"""World Graph retrieval + source-anchor admission service (PR010A)."""

from __future__ import annotations

from pathlib import Path

import graph_memory.kernel as kernel
from apps.live_control_server.config import world_graph_root
from graph_memory.retrieval.models import (
    RETRIEVAL_ERROR_SCHEMA,
    WorldGraphEvidenceRequest,
    WorldGraphNeighborhoodRequest,
    WorldGraphObjectRequest,
    WorldGraphRetrievalDiagnostic,
    WorldGraphRetrievalErrorResponse,
    WorldGraphRetrievalResult,
    WorldGraphSearchRequest,
    WorldGraphSourceAnchorReadRequest,
    WorldGraphSourceAnchorReadResult,
)


class WorldGraphRetrievalServiceError(ValueError):
    """Stable service error mapped to the retrieval API envelope."""

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

    def response(self) -> WorldGraphRetrievalErrorResponse:
        return WorldGraphRetrievalErrorResponse(
            schema=RETRIEVAL_ERROR_SCHEMA,
            code=self.code,
            message=str(self),
            status_code=self.status_code,
            diagnostics=self.diagnostics,
        )


def _resolved_root(root: Path | None) -> Path:
    return (root if root is not None else world_graph_root()).resolve()


def _map_kernel_error(
    exc: kernel.WorldGraphRetrievalError,
) -> WorldGraphRetrievalServiceError:
    return WorldGraphRetrievalServiceError(
        str(exc),
        code=exc.code,
        status_code=exc.status_code,
        diagnostics=exc.diagnostics,
    )


def _internal_error() -> WorldGraphRetrievalServiceError:
    return WorldGraphRetrievalServiceError(
        "World graph retrieval failed unexpectedly.",
        code="retrieval_internal_error",
        status_code=500,
        diagnostics=[
            WorldGraphRetrievalDiagnostic(
                code="retrieval_internal_error",
                message="World graph retrieval failed unexpectedly.",
                severity="error",
            )
        ],
    )


def search_campaign_graph(
    request: WorldGraphSearchRequest,
    *,
    root: Path | None = None,
) -> WorldGraphRetrievalResult:
    graph_root = _resolved_root(root)
    try:
        return kernel.search_campaign_graph(graph_root, request)
    except kernel.WorldGraphRetrievalError as exc:
        raise _map_kernel_error(exc) from None
    except Exception:
        raise _internal_error() from None


def get_campaign_object(
    request: WorldGraphObjectRequest,
    *,
    root: Path | None = None,
) -> WorldGraphRetrievalResult:
    graph_root = _resolved_root(root)
    try:
        return kernel.get_campaign_object(graph_root, request)
    except kernel.WorldGraphRetrievalError as exc:
        raise _map_kernel_error(exc) from None
    except Exception:
        raise _internal_error() from None


def get_object_neighborhood(
    request: WorldGraphNeighborhoodRequest,
    *,
    root: Path | None = None,
) -> WorldGraphRetrievalResult:
    graph_root = _resolved_root(root)
    try:
        return kernel.get_object_neighborhood(graph_root, request)
    except kernel.WorldGraphRetrievalError as exc:
        raise _map_kernel_error(exc) from None
    except Exception:
        raise _internal_error() from None


def get_object_evidence(
    request: WorldGraphEvidenceRequest,
    *,
    root: Path | None = None,
) -> WorldGraphRetrievalResult:
    graph_root = _resolved_root(root)
    try:
        return kernel.get_object_evidence(graph_root, request)
    except kernel.WorldGraphRetrievalError as exc:
        raise _map_kernel_error(exc) from None
    except Exception:
        raise _internal_error() from None


def read_source_anchor(
    request: WorldGraphSourceAnchorReadRequest,
    *,
    root: Path | None = None,
) -> WorldGraphSourceAnchorReadResult:
    graph_root = _resolved_root(root)
    try:
        return kernel.read_source_anchor(graph_root, request)
    except kernel.WorldGraphRetrievalError as exc:
        raise _map_kernel_error(exc) from None
    except Exception:
        raise _internal_error() from None


__all__ = [
    "WorldGraphRetrievalServiceError",
    "get_campaign_object",
    "get_object_evidence",
    "get_object_neighborhood",
    "read_source_anchor",
    "search_campaign_graph",
]
