"""Authenticated selected-managed-World native graph explorer routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from apps.live_control_server.models.native_graph_explorer import (
    NativeGraphExplorerGraphRequest,
    NativeGraphExplorerOperationRequest,
    NativeGraphExplorerPrepareRequest,
)
from apps.live_control_server.services.agent_graph_auth import (
    NativeGraphPrincipal,
    native_graph_gm_dependency,
)
from apps.live_control_server.services import native_graph_explorer as service


router = APIRouter(
    prefix="/api/live/native-graph-explorer",
    tags=["native-graph-explorer"],
)


def _call(operation, *args):
    try:
        return operation(*args)
    except service.NativeGraphExplorerError as exc:
        raise HTTPException(
            status_code=exc.status,
            detail={"code": exc.code, "message": str(exc), "error": str(exc)},
        ) from None
    except Exception:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "native_graph_explorer_unavailable",
                "message": "The native Graph explorer could not verify the selected World or operation. The outcome is uncertain; keep the same operation ID and check its status before retrying.",
                "error": "The native Graph explorer could not verify the selected World or operation. The outcome is uncertain; keep the same operation ID and check its status before retrying.",
            },
        ) from None


@router.post("/graph")
def graph(
    body: NativeGraphExplorerGraphRequest,
    principal: Annotated[NativeGraphPrincipal, Depends(native_graph_gm_dependency)],
):
    return _call(service.graph, body, principal)


@router.post("/prepare")
def prepare(
    body: NativeGraphExplorerPrepareRequest,
    principal: Annotated[NativeGraphPrincipal, Depends(native_graph_gm_dependency)],
):
    return _call(service.prepare, body, principal)


@router.post("/confirm")
def confirm(
    body: NativeGraphExplorerOperationRequest,
    principal: Annotated[NativeGraphPrincipal, Depends(native_graph_gm_dependency)],
):
    return _call(service.confirm, body, principal)


@router.post("/operations/read")
def read_operation(
    body: NativeGraphExplorerOperationRequest,
    principal: Annotated[NativeGraphPrincipal, Depends(native_graph_gm_dependency)],
):
    return _call(service.operation, body, principal)
