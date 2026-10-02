"""Managed world-container list/create API for Build new-world creation."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request

from apps.live_control_server.config import repo_root
from apps.live_control_server.services.agent_graph_auth import enforce_native_graph_gm
from apps.live_control_server.services.world_container_registry import (
    CreateWorldContainerRequest,
    WorldContainerPublicRecord,
    WorldContainerRegistryError,
    WorldContainersListResponse,
    create_world_container,
    list_world_containers,
)
from apps.live_control_server.services.world_graph_binding import (
    BindNativeGraphRequest,
    DeactivateNativeGraphBindingRequest,
    WorldGraphBindingError,
    bind_native_graph,
    deactivate_native_graph_binding,
)

router = APIRouter(prefix="/api/live", tags=["world-containers"])


@router.get("/world-containers", response_model=WorldContainersListResponse)
def get_world_containers() -> dict[str, Any]:
    records = list_world_containers(repo_root())
    response = WorldContainersListResponse(
        records=[WorldContainerPublicRecord.from_record(record) for record in records]
    )
    return response.model_dump(mode="json")


@router.post("/world-containers", response_model=WorldContainerPublicRecord)
def post_world_container(body: CreateWorldContainerRequest) -> dict[str, Any]:
    try:
        record = create_world_container(repo_root(), name=body.name)
    except WorldContainerRegistryError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return WorldContainerPublicRecord.from_record(record).model_dump(mode="json")


@router.put(
    "/world-containers/{managed_world_id}/native-graph-binding",
    response_model=WorldContainerPublicRecord,
)
def put_native_graph_binding(
    managed_world_id: str,
    body: BindNativeGraphRequest,
    request: Request,
) -> dict[str, Any]:
    enforce_native_graph_gm(request)
    try:
        record = bind_native_graph(
            repo_root(),
            managed_world_id,
            native_world_id=body.native_world_id,
            expected_binding_version=body.expected_binding_version,
        )
    except (WorldGraphBindingError, WorldContainerRegistryError) as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return WorldContainerPublicRecord.from_record(record).model_dump(mode="json")


@router.post(
    "/world-containers/{managed_world_id}/native-graph-binding/deactivate",
    response_model=WorldContainerPublicRecord,
)
def post_deactivate_native_graph_binding(
    managed_world_id: str,
    body: DeactivateNativeGraphBindingRequest,
    request: Request,
) -> dict[str, Any]:
    enforce_native_graph_gm(request)
    try:
        record = deactivate_native_graph_binding(
            repo_root(),
            managed_world_id,
            expected_binding_version=body.expected_binding_version,
        )
    except (WorldGraphBindingError, WorldContainerRegistryError) as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return WorldContainerPublicRecord.from_record(record).model_dump(mode="json")
