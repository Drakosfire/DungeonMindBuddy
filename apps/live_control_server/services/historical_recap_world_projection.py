"""Project one durable historical recap onto the current governed World."""

from __future__ import annotations

from pathlib import Path

from apps.live_control_server.models.historical_recap_projection import (
    HistoricalRecapWorldProjectionResponse,
)
from apps.live_control_server.services.graph_run_registry import (
    GraphRunRegistryError,
    get_extraction_run,
)
from apps.live_control_server.services.world_graph_projection import (
    WorldGraphProjectionServiceError,
    project_world_graph,
)
from application_state.errors import ApplicationStateError
from application_state.source import service as source_service
from graph_memory.ingestion.extraction_run import (
    ExtractionRunComponentKind,
    normalize_content_digest,
)
from graph_memory.projection.world_projection import (
    WorldGraphProjectionDiagnostic,
    WorldGraphProjectionRequest,
)
from graph_memory.projection.world_recap_projection import (
    focus_overlay_from_world,
    project_world_markdown_mentions,
    recap_projection_trust_boundary,
)


class HistoricalRecapProjectionError(ValueError):
    """Stable errors for an exact-run historical projection."""

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


def _error(
    message: str,
    *,
    code: str,
    status_code: int,
) -> HistoricalRecapProjectionError:
    return HistoricalRecapProjectionError(
        message,
        code=code,
        status_code=status_code,
        diagnostics=[
            WorldGraphProjectionDiagnostic(
                code=code,
                message=message,
                severity="error",
            )
        ],
    )


def _source_digest(run) -> str:
    component = run.components.get(ExtractionRunComponentKind.SOURCE_ARTIFACT.value)
    if component is None:
        raise _error(
            "exact run does not record a source_artifact component",
            code="source_component_unavailable",
            status_code=422,
        )
    digest = normalize_content_digest(component.sha256)
    if not digest:
        raise _error(
            "exact run source_artifact component has no content digest",
            code="source_digest_unavailable",
            status_code=422,
        )
    return digest


def build_historical_recap_world_projection(
    root: Path,
    run_id: str,
) -> HistoricalRecapWorldProjectionResponse:
    """Return only a complete source + current-World projection.

    The source lookup is APP-STATE-only. ``root`` is passed exclusively to the
    governed DungeonMind adapter; no historical source component URI is opened.
    """

    try:
        run = get_extraction_run(root, run_id)
    except GraphRunRegistryError as exc:
        raise _error(
            str(exc),
            code="exact_run_unavailable",
            status_code=exc.status_code,
        ) from exc
    if run.source_domain != "recap":
        raise _error(
            "historical recap projection is not applicable to this extraction run",
            code="wrong_source_domain",
            status_code=422,
        )
    if not run.campaign_id or not run.session_id:
        raise _error(
            "recap extraction run has incomplete campaign/session identity",
            code="run_scope_unavailable",
            status_code=422,
        )

    digest = _source_digest(run)
    try:
        source = source_service.get_source_markdown(
            source_artifact_id=run.source_artifact_id,
            content_sha256=digest,
        )
    except ApplicationStateError as exc:
        raise _error(
            f"durable source authority is unavailable: {exc}",
            code="source_authority_unavailable",
            status_code=503,
        ) from exc
    if source is None:
        raise _error(
            "exact historical source is not adopted into APP-STATE",
            code="source_content_unavailable",
            status_code=404,
        )
    if (
        source.source_domain != run.source_domain
        or source.campaign_id != run.campaign_id
        or source.session_id != run.session_id
    ):
        raise _error(
            "durable source identity does not match the exact ExtractionRun",
            code="source_binding_mismatch",
            status_code=422,
        )
    if not source.world_id:
        raise _error(
            "durable source has no current World binding",
            code="world_binding_unavailable",
            status_code=409,
        )

    request = WorldGraphProjectionRequest(
        schema="dmb_world_graph_projection_request_v1",
        world_id=source.world_id,
        campaign_id=run.campaign_id,
        focus={
            "kind": "session",
            "campaign_id": run.campaign_id,
            "session_id": run.session_id,
        },
        admissibility="gm",
        scope_mode="campaign",
    )
    try:
        world = project_world_graph(request, root=root)
    except WorldGraphProjectionServiceError as exc:
        raise HistoricalRecapProjectionError(
            str(exc),
            code=exc.code,
            status_code=exc.status_code,
            diagnostics=exc.diagnostics,
        ) from exc

    projected_markdown, mentions, mention_diagnostics = project_world_markdown_mentions(
        source.markdown,
        list(world.nodes),
    )
    snapshot = world.snapshot
    return HistoricalRecapWorldProjectionResponse(
        run_id=run.run_id,
        run_status=run.status.value,
        source_domain=run.source_domain,
        source_artifact_id=run.source_artifact_id,
        source_revision_id=str(source.source_revision_id),
        campaign_id=run.campaign_id,
        session_id=run.session_id,
        world_id=source.world_id,
        source_sha256=f"sha256:{source.content_sha256}",
        graph_id=snapshot.revision_id,
        snapshot=snapshot,
        markdown=projected_markdown,
        focus=focus_overlay_from_world(world, session_id=run.session_id),
        node_views={node.node_id: node for node in world.nodes},
        mentions=mentions,
        source_spans=[],
        diagnostics=mention_diagnostics,
        trust_boundary=recap_projection_trust_boundary(),
    )
