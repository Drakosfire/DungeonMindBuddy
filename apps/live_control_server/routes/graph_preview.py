"""Graph preview read API for /plan toolbox projection."""
from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query

from apps.live_control_server.config import repo_root
from apps.live_control_server.services.graph_preview_surface import (
    GraphPreviewRunsResponse,
    GraphPreviewSurfaceResponse,
    build_graph_preview_surface,
    build_latest_graph_preview_surface,
    discover_graph_preview_runs,
    GraphPreviewSurfaceError,
)

router = APIRouter(prefix="/api/live/graph-preview", tags=["graph-preview"])


@router.get("/runs", response_model=GraphPreviewRunsResponse)
def get_graph_preview_runs() -> dict[str, Any]:
    runs = discover_graph_preview_runs(repo_root())
    return GraphPreviewRunsResponse(runs=runs).model_dump(mode="json")


@router.get("/latest", response_model=GraphPreviewSurfaceResponse)
def get_graph_preview_latest(
    run_dir: Annotated[str | None, Query()] = None,
) -> dict[str, Any]:
    try:
        if run_dir:
            response = build_graph_preview_surface(repo_root(), run_dir)
        else:
            response = build_latest_graph_preview_surface(repo_root())
    except GraphPreviewSurfaceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return response.model_dump(mode="json")
