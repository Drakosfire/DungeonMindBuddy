"""Graph object authoring prepare/commit API routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from apps.live_control_server.services.graph_object_authoring_commit import (
    commit_graph_object_authoring_write,
)
from apps.live_control_server.services.graph_object_authoring_prepare import (
    GraphObjectAuthoringCommitRequest,
    GraphObjectAuthoringCommitResponse,
    GraphObjectAuthoringError,
    GraphObjectAuthoringPrepareRequest,
    GraphObjectAuthoringPrepareResponse,
    prepare_graph_object_authoring_write,
)

router = APIRouter(prefix="/api/live/graph-authoring", tags=["graph-authoring"])

_STORE_RETIRED = {
    "code": "graph_authoring_store_retired",
    "message": (
        "Graph authoring merge-reconciliation file materialization is retired. "
        "Use Graph Review prepare/commit on DungeonMind World Graph authority."
    ),
}


@router.post("/prepare", response_model=GraphObjectAuthoringPrepareResponse)
def post_graph_object_authoring_prepare(
    request: GraphObjectAuthoringPrepareRequest,
) -> dict[str, Any]:
    try:
        response = prepare_graph_object_authoring_write(request)
    except GraphObjectAuthoringError as exc:
        raise HTTPException(
            status_code=exc.status_code, detail={"code": exc.code, "message": str(exc)}
        ) from exc
    return response.model_dump(mode="json", by_alias=False)


@router.post("/commit", response_model=GraphObjectAuthoringCommitResponse)
def post_graph_object_authoring_commit(
    request: GraphObjectAuthoringCommitRequest,
) -> dict[str, Any]:
    try:
        response = commit_graph_object_authoring_write(request)
    except GraphObjectAuthoringError as exc:
        raise HTTPException(
            status_code=exc.status_code, detail={"code": exc.code, "message": str(exc)}
        ) from exc
    return response.model_dump(mode="json", by_alias=False)


@router.post("/merge-reconciliation/prepare")
def post_graph_merge_reconciliation_prepare(
    _body: dict[str, Any] | None = None,
) -> JSONResponse:
    return JSONResponse(status_code=410, content={"detail": _STORE_RETIRED})


@router.post("/merge-reconciliation/apply")
def post_graph_merge_reconciliation_apply(
    _body: dict[str, Any] | None = None,
) -> JSONResponse:
    return JSONResponse(status_code=410, content={"detail": _STORE_RETIRED})
