"""World Graph retrieval + source-anchor admission service (PR010A)."""

from __future__ import annotations

from pathlib import Path

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


def _route_authority_read(
    request: WorldGraphRetrievalRequestContext,
    root: Path | None,
) -> tuple[Path, WorldGraphRetrievalRequestContext]:
    """Route the read through the selected World Graph authority.

    Explicit roots (tests) bypass routing. In ``dungeonmind`` authority mode
    the read is served from the DungeonMind-hydrated cache root and legacy
    pre-cutover revision pins are rewritten through the adoption bridge.
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
    graph_root, request = _route_authority_read(request, root)
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
    graph_root, request = _route_authority_read(request, root)
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
    graph_root, request = _route_authority_read(request, root)
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
    graph_root, request = _route_authority_read(request, root)
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
    repo_root: Path | None = None,
) -> WorldGraphSourceAnchorReadResult:
    graph_root, request = _route_authority_read(request, root)
    file_root = _resolved_repo_root(root=root, repo_root=repo_root)
    try:
        resolved = kernel.resolve_admitted_anchor_match(graph_root, request)
        if isinstance(resolved, WorldGraphSourceAnchorReadResult):
            return resolved
        anchor = resolved.derivation.anchor
        if (
            anchor.locator_kind == "source_span"
            and str(anchor.source_domain) == "worldbuilding"
            and (anchor.source_span_ref_id or "").strip()
        ):
            return read_admitted_worldbuilding_span(
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
            )
        return kernel.read_source_anchor(
            graph_root, request, repo_root=file_root
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
