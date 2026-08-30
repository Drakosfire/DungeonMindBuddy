"""World Graph → focus-session recap projection service (PR380A / PR #412)."""


from __future__ import annotations


from pathlib import Path
from typing import Any


from apps.live_control_server.services.world_graph_projection import (
    WorldGraphProjectionServiceError,
    project_world_graph,
)
from graph_memory.projection.world_projection import (
    WorldGraphProjectionDiagnostic,
    WorldGraphProjectionRequest,
)
from graph_memory.projection.world_recap_projection import (
    RECAP_PROJECTION_RESPONSE_SCHEMA,
    WorldGraphRecapProjection,
    focus_overlay_from_world,
    project_world_markdown_mentions,
    recap_projection_trust_boundary,
)


def _invalid_request(message: str) -> WorldGraphProjectionServiceError:
    return WorldGraphProjectionServiceError(
        message,
        code="invalid_request",
        status_code=422,
        diagnostics=[
            WorldGraphProjectionDiagnostic(
                code="invalid_request",
                message=message,
                severity="error",
            )
        ],
    )


def validate_recap_projection_request(
    request: WorldGraphProjectionRequest,
) -> tuple[str, str]:
    """Admit only campaign-scoped, session-focused, non-search recap reads."""
    if request.focus.kind != "session" or not request.focus.session_id:
        raise _invalid_request(
            "World graph recap projection requires focus.kind=session and a session_id."
        )
    if request.focus.campaign_id is not None and request.focus.campaign_id != request.campaign_id:
        raise _invalid_request(
            "focus.campaign_id must equal campaign_id for world graph recap projection."
        )
    if request.scope_mode != "campaign":
        raise _invalid_request(
            "World graph recap projection v1 requires scope_mode=campaign."
        )
    if request.query_text is not None:
        raise _invalid_request(
            "World graph recap projection does not accept query_text."
        )
    return request.campaign_id, request.focus.session_id


def _load_corpus_markdown(*, campaign_id: str, session_id: str) -> str:
    """Load corpus-normalized recap markdown without importing Union builders at module load."""
    from apps.live_control_server.services.corpus_normalized_recap import (
        CorpusNormalizedRecapLoadError,
        load_corpus_normalized_recap_markdown,
    )


    try:
        return load_corpus_normalized_recap_markdown(
            campaign_id=campaign_id,
            session_id=session_id,
            on_ambiguous="fail",
        )
    except CorpusNormalizedRecapLoadError as exc:
        raise WorldGraphProjectionServiceError(
            str(exc),
            code=exc.code,
            status_code=exc.status_code,
            diagnostics=[
                WorldGraphProjectionDiagnostic(
                    code=exc.code,
                    message=str(exc),
                    severity="error",
                )
            ],
        ) from None


def build_world_graph_recap_projection(
    request: WorldGraphProjectionRequest,
    *,
    root: Path | None = None,
    corpus_markdown: str | None = None,
) -> WorldGraphRecapProjection:
    """Project one exact World Graph snapshot + canonical recap into a recap payload."""
    campaign_id, session_id = validate_recap_projection_request(request)


    # Exactly one generic projection call; never widen scope or retry world.
    world = project_world_graph(request, root=root)


    markdown = corpus_markdown
    if markdown is None:
        markdown = _load_corpus_markdown(campaign_id=campaign_id, session_id=session_id)
    if not (markdown or "").strip():
        raise WorldGraphProjectionServiceError(
            f"Normalized recap markdown not found for {campaign_id} {session_id}.",
            code="recap_markdown_unavailable",
            status_code=404,
            diagnostics=[
                WorldGraphProjectionDiagnostic(
                    code="recap_markdown_unavailable",
                    message=(
                        f"Normalized recap markdown not found for {campaign_id} {session_id}."
                    ),
                    severity="error",
                )
            ],
        )


    projected_markdown, mentions, mention_diagnostics = project_world_markdown_mentions(
        markdown,
        list(world.nodes),
    )
    node_views = {node.node_id: node for node in world.nodes}
    snapshot = world.snapshot


    return WorldGraphRecapProjection(
        schema=RECAP_PROJECTION_RESPONSE_SCHEMA,
        campaign_id=campaign_id,
        session_id=session_id,
        graph_id=snapshot.revision_id,
        snapshot=snapshot,
        markdown=projected_markdown,
        focus=focus_overlay_from_world(world, session_id=session_id),
        node_views=node_views,
        mentions=mentions,
        source_spans=[],
        diagnostics=list(mention_diagnostics),
        trust_boundary=recap_projection_trust_boundary(),
    )


def build_world_graph_recap_projection_payload(
    request: WorldGraphProjectionRequest,
    *,
    root: Path | None = None,
    corpus_markdown: str | None = None,
) -> dict[str, Any]:
    projection = build_world_graph_recap_projection(
        request,
        root=root,
        corpus_markdown=corpus_markdown,
    )
    return projection.model_dump(mode="json", by_alias=True)


__all__ = [
    "build_world_graph_recap_projection",
    "build_world_graph_recap_projection_payload",
    "validate_recap_projection_request",
]
