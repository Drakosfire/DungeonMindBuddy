"""Authenticated World Trash inventory and reversible lifecycle endpoints."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field

from apps.live_control_server.config import (
    ManagedWorldDataRootError,
    managed_world_data_root,
    repo_root,
)
from apps.live_control_server.services.agent_graph_auth import enforce_native_graph_gm
from apps.live_control_server.services.workspace_document_registry import (
    WorkspaceDocumentRegistryError,
)
from apps.live_control_server.services.workspace_lifecycle import (
    list_world_workspace_trash,
    set_world_document_trash,
    set_world_session_trash,
)
from apps.live_control_server.services.world_container_registry import (
    WorldContainerRegistryError,
    get_world_container,
)

router = APIRouter(prefix="/api/live/world-workspace", tags=["workspace-lifecycle"])


class DocumentLifecycleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    expected_revision: int = Field(ge=1)


class SessionLifecycleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    expected_revision: int = Field(ge=1)
    expected_content_revision: int = Field(ge=0)


def _root():
    try:
        return managed_world_data_root(repo_root())
    except ManagedWorldDataRootError as exc:
        raise HTTPException(
            status_code=503, detail="Managed World storage is unavailable."
        ) from exc


def _raise(exc: Exception) -> None:
    if isinstance(exc, WorkspaceDocumentRegistryError):
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    if isinstance(exc, WorldContainerRegistryError):
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    raise HTTPException(
        status_code=503, detail="Workspace lifecycle is unavailable."
    ) from exc


@router.get("/trash")
def get_world_trash(request: Request, world_id: str = Query(min_length=1)) -> dict:
    enforce_native_graph_gm(request)
    try:
        return list_world_workspace_trash(_root(), world_id=world_id)
    except Exception as exc:
        _raise(exc)


@router.post("/documents/{document_id}/{action}")
def mutate_world_document_trash(
    document_id: str,
    action: Literal["trash", "restore"],
    payload: DocumentLifecycleRequest,
    request: Request,
    world_id: str = Query(min_length=1),
) -> dict:
    enforce_native_graph_gm(request)
    try:
        return set_world_document_trash(
            _root(),
            world_id=world_id,
            document_id=document_id,
            expected_revision=payload.expected_revision,
            restore=action == "restore",
        )
    except Exception as exc:
        _raise(exc)


@router.post("/sessions/{run_id}/{action}")
def mutate_world_session_trash(
    run_id: UUID,
    action: Literal["trash", "restore"],
    payload: SessionLifecycleRequest,
    request: Request,
    world_id: str = Query(min_length=1),
) -> dict:
    enforce_native_graph_gm(request)
    try:
        root = _root()
        world = get_world_container(root, world_id)
        if world.world_id != world_id:
            raise WorkspaceDocumentRegistryError(
                "World identity mismatch", status_code=404
            )
        return set_world_session_trash(
            world_id=world_id,
            run_id=str(run_id),
            expected_revision=payload.expected_revision,
            expected_content_revision=payload.expected_content_revision,
            restore=action == "restore",
        )
    except Exception as exc:
        _raise(exc)
