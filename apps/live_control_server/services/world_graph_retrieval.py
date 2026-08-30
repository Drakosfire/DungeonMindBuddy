"""World Graph retrieval + source-anchor admission service (PR010A / CUTOVER D.3A)."""

from __future__ import annotations

from pathlib import Path

from apps.live_control_server.config import (
    WorldGraphAuthorityConfigurationError,
    repo_root as default_repo_root,
    require_mounted_dungeonmind_world_graph,
)
from graph_memory.retrieval.models import (
    RETRIEVAL_ERROR_SCHEMA,
    WorldGraphEvidenceRequest,
    WorldGraphNeighborhoodRequest,
    WorldGraphObjectRequest,
    WorldGraphRetrievalDiagnostic,
    WorldGraphRetrievalErrorResponse,
    WorldGraphSearchRequest,
    WorldGraphSourceAnchorReadRequest,
    WorldGraphSourceAnchorReadResult,
    WorldGraphRetrievalResult,
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


def _map_configuration_error(
    exc: WorldGraphAuthorityConfigurationError,
) -> WorldGraphRetrievalServiceError:
    return WorldGraphRetrievalServiceError(
        str(exc),
        code=exc.code,
        status_code=400,
        diagnostics=[
            WorldGraphRetrievalDiagnostic(
                code=exc.code,
                message=str(exc),
                severity="error",
            )
        ],
    )


def _map_direct_error(exc) -> WorldGraphRetrievalServiceError:
    return WorldGraphRetrievalServiceError(
        str(exc),
        code=exc.code,
        status_code=exc.status_code,
        diagnostics=[
            WorldGraphRetrievalDiagnostic(
                code=str(d.get("code", exc.code)),
                message=str(d.get("message", str(exc))),
                severity="error",
            )
            for d in exc.diagnostics
        ]
        or None,
    )


def _require_mounted_native_read(root: Path | None) -> None:
    """Fail closed for retired modes and alternate world_root (no Kernel escape)."""
    try:
        require_mounted_dungeonmind_world_graph(world_root=root)
    except WorldGraphAuthorityConfigurationError as exc:
        raise _map_configuration_error(exc) from None


def _resolved_repo_root(*, root: Path | None, repo_root: Path | None) -> Path:
    """Resolve the registry/file root for worldbuilding SourceSpan reads."""
    if repo_root is not None:
        return Path(repo_root).resolve()
    if root is not None:
        candidate = Path(root).resolve()
        if (candidate / "out" / "registries").exists() or (
            candidate / "corpus"
        ).exists():
            return candidate
    return default_repo_root().resolve()


def search_campaign_graph(
    request: WorldGraphSearchRequest,
    *,
    root: Path | None = None,
) -> WorldGraphRetrievalResult:
    _require_mounted_native_read(root)
    from apps.live_control_server.integrations.dungeonmind import (
        world_graph_reads as direct,
    )

    try:
        return direct.search_world_graph_direct(
            direct.direct_services_from_config(request.world_id), request
        )
    except direct.DirectWorldGraphReadError as exc:
        raise _map_direct_error(exc) from None


def get_campaign_object(
    request: WorldGraphObjectRequest,
    *,
    root: Path | None = None,
) -> WorldGraphRetrievalResult:
    _require_mounted_native_read(root)
    from apps.live_control_server.integrations.dungeonmind import (
        world_graph_reads as direct,
    )

    try:
        return direct.get_object_direct(
            direct.direct_services_from_config(request.world_id), request
        )
    except direct.DirectWorldGraphReadError as exc:
        raise _map_direct_error(exc) from None


def get_object_neighborhood(
    request: WorldGraphNeighborhoodRequest,
    *,
    root: Path | None = None,
) -> WorldGraphRetrievalResult:
    _require_mounted_native_read(root)
    from apps.live_control_server.integrations.dungeonmind import (
        world_graph_reads as direct,
    )

    try:
        return direct.get_neighborhood_direct(
            direct.direct_services_from_config(request.world_id), request
        )
    except direct.DirectWorldGraphReadError as exc:
        raise _map_direct_error(exc) from None


def get_object_evidence(
    request: WorldGraphEvidenceRequest,
    *,
    root: Path | None = None,
) -> WorldGraphRetrievalResult:
    _require_mounted_native_read(root)
    from apps.live_control_server.integrations.dungeonmind import (
        world_graph_reads as direct,
    )

    try:
        return direct.get_evidence_direct(
            direct.direct_services_from_config(request.world_id), request
        )
    except direct.DirectWorldGraphReadError as exc:
        raise _map_direct_error(exc) from None


def read_source_anchor(
    request: WorldGraphSourceAnchorReadRequest,
    *,
    root: Path | None = None,
    repo_root: Path | None = None,
) -> WorldGraphSourceAnchorReadResult:
    _require_mounted_native_read(root)
    from apps.live_control_server.integrations.dungeonmind import (
        world_graph_reads as direct,
    )

    try:
        return direct.read_source_anchor_direct(
            direct.direct_services_from_config(request.world_id),
            request,
            repo_root=_resolved_repo_root(root=root, repo_root=repo_root),
        )
    except direct.DirectWorldGraphReadError as exc:
        raise _map_direct_error(exc) from None


__all__ = [
    "WorldGraphRetrievalServiceError",
    "get_campaign_object",
    "get_object_evidence",
    "get_object_neighborhood",
    "read_source_anchor",
    "search_campaign_graph",
]
