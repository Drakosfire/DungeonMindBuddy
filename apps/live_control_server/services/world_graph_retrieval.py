"""World Graph retrieval + source-anchor admission service (PR010A)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import graph_memory.kernel as kernel
from apps.live_control_server.config import repo_root as default_repo_root
from apps.live_control_server.config import world_graph_root
from apps.live_control_server.services.worldbuilding_source_span_read import (
    read_admitted_worldbuilding_span,
)
from graph_memory.retrieval.models import (
    RETRIEVAL_ERROR_SCHEMA,
    WorldGraphEvidenceRequest,
    WorldGraphNeighborhoodRequest,
    WorldGraphObjectRequest,
    WorldGraphRetrievalDiagnostic,
    WorldGraphRetrievalErrorResponse,
    WorldGraphRetrievalRequestContext,
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


def _map_direct_error(exc: Any) -> WorldGraphRetrievalServiceError:
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


def _route_authority_read(
    request: WorldGraphRetrievalRequestContext,
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
        raise WorldGraphRetrievalServiceError(
            str(exc),
            code=exc.code,
            status_code=world_graph_authority.authority_error_status_code(exc),
            diagnostics=[
                WorldGraphRetrievalDiagnostic(
                    code=exc.code,
                    message=str(exc),
                    severity="error",
                )
            ],
        ) from None


def _normalize_authority_identity(result: Any, route: Any) -> Any:
    """Rewrite private hydrated-cache revision ids to public DungeonMind ids.

    Product-visible revision/head identity names the selected/current
    DungeonMind revision so a returned id is exactly re-pinnable against the
    authority; the hydrated cache's Buddy content-addressed ids stay internal.
    """
    if route.public_revision_id is None:
        return result
    snapshot = getattr(result, "snapshot", None)
    if snapshot is None:
        return result
    return result.model_copy(
        update={
            "snapshot": snapshot.model_copy(
                update={
                    "revision_id": route.public_revision_id,
                    "head_revision_id": route.public_head_revision_id,
                    "is_head": route.public_revision_id
                    == route.public_head_revision_id,
                }
            )
        }
    )


def _resolved_repo_root(*, root: Path | None, repo_root: Path | None) -> Path:
    """Resolve the registry/file root for worldbuilding SourceSpan reads.

    Production Hermes passes the World Graph store root separately from the
    repository root that owns ``out/registries`` and corpus Markdown. Tests that
    pass an explicit ``repo_root`` (or a self-contained ``root`` tree) keep that
    layout.
    """
    if repo_root is not None:
        return Path(repo_root).resolve()
    if root is not None:
        candidate = Path(root).resolve()
        # Self-contained test trees host registries under the same root.
        if (candidate / "out" / "registries").exists() or (
            candidate / "corpus"
        ).exists():
            return candidate
    return default_repo_root().resolve()


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
    if _direct_read_active(root):
        from apps.live_control_server.integrations.dungeonmind import (
            world_graph_reads as direct,
        )

        try:
            return direct.search_world_graph_direct(
                direct.direct_services_from_config(request.world_id), request
            )
        except direct.DirectWorldGraphReadError as exc:
            raise _map_direct_error(exc) from None
    route = _route_authority_read(request, root)
    try:
        return _normalize_authority_identity(
            kernel.search_campaign_graph(route.graph_root, route.request), route
        )
    except kernel.WorldGraphRetrievalError as exc:
        raise _map_kernel_error(exc) from None
    except Exception:
        raise _internal_error() from None


def get_campaign_object(
    request: WorldGraphObjectRequest,
    *,
    root: Path | None = None,
) -> WorldGraphRetrievalResult:
    if _direct_read_active(root):
        from apps.live_control_server.integrations.dungeonmind import (
            world_graph_reads as direct,
        )

        try:
            return direct.get_object_direct(
                direct.direct_services_from_config(request.world_id), request
            )
        except direct.DirectWorldGraphReadError as exc:
            raise _map_direct_error(exc) from None
    route = _route_authority_read(request, root)
    try:
        return _normalize_authority_identity(
            kernel.get_campaign_object(route.graph_root, route.request), route
        )
    except kernel.WorldGraphRetrievalError as exc:
        raise _map_kernel_error(exc) from None
    except Exception:
        raise _internal_error() from None


def get_object_neighborhood(
    request: WorldGraphNeighborhoodRequest,
    *,
    root: Path | None = None,
) -> WorldGraphRetrievalResult:
    if _direct_read_active(root):
        from apps.live_control_server.integrations.dungeonmind import (
            world_graph_reads as direct,
        )

        try:
            return direct.get_neighborhood_direct(
                direct.direct_services_from_config(request.world_id), request
            )
        except direct.DirectWorldGraphReadError as exc:
            raise _map_direct_error(exc) from None
    route = _route_authority_read(request, root)
    try:
        return _normalize_authority_identity(
            kernel.get_object_neighborhood(route.graph_root, route.request), route
        )
    except kernel.WorldGraphRetrievalError as exc:
        raise _map_kernel_error(exc) from None
    except Exception:
        raise _internal_error() from None


def get_object_evidence(
    request: WorldGraphEvidenceRequest,
    *,
    root: Path | None = None,
) -> WorldGraphRetrievalResult:
    if _direct_read_active(root):
        from apps.live_control_server.integrations.dungeonmind import (
            world_graph_reads as direct,
        )

        try:
            return direct.get_evidence_direct(
                direct.direct_services_from_config(request.world_id), request
            )
        except direct.DirectWorldGraphReadError as exc:
            raise _map_direct_error(exc) from None
    route = _route_authority_read(request, root)
    try:
        return _normalize_authority_identity(
            kernel.get_object_evidence(route.graph_root, route.request), route
        )
    except kernel.WorldGraphRetrievalError as exc:
        raise _map_kernel_error(exc) from None
    except Exception:
        raise _internal_error() from None


def read_source_anchor(
    request: WorldGraphSourceAnchorReadRequest,
    *,
    root: Path | None = None,
    repo_root: Path | None = None,
) -> WorldGraphSourceAnchorReadResult:
    if _direct_read_active(root):
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
    route = _route_authority_read(request, root)
    graph_root, request = route.graph_root, route.request
    file_root = _resolved_repo_root(root=root, repo_root=repo_root)
    try:
        resolved = kernel.resolve_admitted_anchor_match(graph_root, request)
        if isinstance(resolved, WorldGraphSourceAnchorReadResult):
            return _normalize_authority_identity(resolved, route)
        anchor = resolved.derivation.anchor
        if (
            anchor.locator_kind == "source_span"
            and str(anchor.source_domain) == "worldbuilding"
            and (anchor.source_span_ref_id or "").strip()
        ):
            return _normalize_authority_identity(
                read_admitted_worldbuilding_span(
                    root=file_root,
                    source_artifact_id=anchor.source_artifact_id,
                    source_span_ref_id=str(anchor.source_span_ref_id),
                    graph_content_sha256=resolved.graph_content_sha256,
                    max_chars=request.max_chars,
                    anchor_id=request.anchor_id,
                    evidence_ref_id=anchor.evidence_ref_id,
                    snapshot=resolved.snapshot,
                    graph_artifact=resolved.store.source_artifacts.get(
                        anchor.source_artifact_id
                    ),
                ),
                route,
            )
        return _normalize_authority_identity(
            kernel.read_source_anchor(graph_root, request, repo_root=file_root),
            route,
        )
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
