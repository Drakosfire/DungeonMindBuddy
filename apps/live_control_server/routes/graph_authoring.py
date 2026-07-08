"""Graph object authoring prepare/commit API routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from apps.live_control_server.services.graph_merge_reconciliation_materialize import (
    GraphMergeReconciliationApplyRequest,
    GraphMergeReconciliationApplyResponse,
    GraphMergeReconciliationMaterializeError,
    GraphMergeReconciliationPrepareRequest,
    GraphMergeReconciliationPrepareResponse,
    apply_graph_merge_reconciliation_materialization,
    prepare_graph_merge_reconciliation_materialization,
)
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


@router.post("/prepare", response_model=GraphObjectAuthoringPrepareResponse)
def post_graph_object_authoring_prepare(
    request: GraphObjectAuthoringPrepareRequest,
) -> dict[str, Any]:
    try:
        response = prepare_graph_object_authoring_write(request)
    except GraphObjectAuthoringError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": str(exc)}) from exc
    return response.model_dump(mode="json", by_alias=False)


@router.post("/commit", response_model=GraphObjectAuthoringCommitResponse)
def post_graph_object_authoring_commit(
    request: GraphObjectAuthoringCommitRequest,
) -> dict[str, Any]:
    try:
        response = commit_graph_object_authoring_write(request)
    except GraphObjectAuthoringError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": str(exc)}) from exc
    return response.model_dump(mode="json", by_alias=False)


@router.post(
    "/merge-reconciliation/prepare",
    response_model=GraphMergeReconciliationPrepareResponse,
)
def post_graph_merge_reconciliation_prepare(
    request: GraphMergeReconciliationPrepareRequest,
) -> dict[str, Any]:
    try:
        response = prepare_graph_merge_reconciliation_materialization(request)
    except GraphMergeReconciliationMaterializeError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": str(exc)}) from exc
    return response.model_dump(mode="json", by_alias=False)


@router.post(
    "/merge-reconciliation/apply",
    response_model=GraphMergeReconciliationApplyResponse,
)
def post_graph_merge_reconciliation_apply(
    request: GraphMergeReconciliationApplyRequest,
) -> dict[str, Any]:
    try:
        response = apply_graph_merge_reconciliation_materialization(request)
    except GraphMergeReconciliationMaterializeError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": str(exc)}) from exc
    return response.model_dump(mode="json", by_alias=False)
