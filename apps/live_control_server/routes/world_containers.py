"""Managed world-container list/create API for Build new-world creation."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict

from apps.live_control_server.config import repo_root
from apps.live_control_server.services.world_container_registry import (
    CreateWorldContainerRequest,
    WorldContainerPublicRecord,
    WorldContainerRegistryError,
    WorldContainersListResponse,
    create_world_container,
    list_world_containers,
)
from apps.live_control_server.services.world_space_binding import (
    WorldSpaceBindingError,
    provision_world_space,
)

router = APIRouter(prefix="/api/live", tags=["world-containers"])


class ProvisionWorldSpaceRequest(BaseModel):
    """Empty command shape; clients cannot choose a MIND allocation or space."""

    model_config = ConfigDict(extra="forbid")


@router.get("/world-containers", response_model=WorldContainersListResponse)
def get_world_containers() -> dict[str, Any]:
    records = list_world_containers(repo_root())
    return WorldContainersListResponse(
        records=[WorldContainerPublicRecord.from_record(record) for record in records]
    ).model_dump(mode="json")


@router.post("/world-containers", response_model=WorldContainerPublicRecord)
def post_world_container(body: CreateWorldContainerRequest) -> dict[str, Any]:
    try:
        record = create_world_container(repo_root(), name=body.name)
    except WorldContainerRegistryError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return WorldContainerPublicRecord.from_record(record).model_dump(mode="json")


@router.post(
    "/world-containers/{world_id}/knowledge-space",
    response_model=WorldContainerPublicRecord,
)
def post_world_space_binding(
    world_id: str, body: ProvisionWorldSpaceRequest
) -> dict[str, Any]:
    del body  # The strict empty shape rejects caller-supplied identity fields.
    try:
        record = provision_world_space(repo_root(), world_id)
    except (WorldContainerRegistryError, WorldSpaceBindingError) as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return WorldContainerPublicRecord.from_record(record).model_dump(mode="json")
