"""Graph object authoring prepare/commit API routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from apps.live_control_server.services.graph_document_relationship import DocumentRelationshipRequest, relationship_request
from apps.live_control_server.config import repo_root
from apps.live_control_server.services.source_artifact_registry import SourceArtifactRegistryError
from apps.live_control_server.services.workspace_document_registry import WorkspaceDocumentRegistryError
from apps.live_control_server.services.world_graph_projection import WorldGraphProjectionServiceError

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
    graph_review_supported_object_kinds,
)

router = APIRouter(prefix="/api/live/graph-authoring", tags=["graph-authoring"])

_STORE_RETIRED = {
    "code": "graph_authoring_store_retired",
    "message": (
        "Graph authoring merge-reconciliation file materialization is retired. "
        "Use Graph Review prepare/commit on DungeonMind World Graph authority."
    ),
}


@router.get("/object-kinds")
def get_graph_object_authoring_kinds() -> dict[str, Any]:
    return {"objectKinds": graph_review_supported_object_kinds()}


@router.post("/document-relationship/request")
def post_document_relationship_request(request: DocumentRelationshipRequest) -> dict[str, Any]:
    try:
        return relationship_request(repo_root(), request).model_dump(mode="json", by_alias=True)
    except (GraphObjectAuthoringError, SourceArtifactRegistryError, WorkspaceDocumentRegistryError, WorldGraphProjectionServiceError) as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": getattr(exc,"code","relationship_source_unavailable"), "message": str(exc)}) from exc


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
