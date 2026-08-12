"""Managed world-container list/create API for Build new-world creation."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from apps.live_control_server.config import repo_root
from apps.live_control_server.services.world_container_registry import (
    CreateWorldContainerRequest,
    WorldContainerRecord,
    WorldContainerRegistryError,
    WorldContainersListResponse,
    create_world_container,
    list_world_containers,
)

router = APIRouter(prefix="/api/live", tags=["world-containers"])


@router.get("/world-containers", response_model=WorldContainersListResponse)
def get_world_containers() -> dict[str, Any]:
    records = list_world_containers(repo_root())
    return WorldContainersListResponse(records=records).model_dump(mode="json")


@router.post("/world-containers", response_model=WorldContainerRecord)
def post_world_container(body: CreateWorldContainerRequest) -> dict[str, Any]:
    try:
        record = create_world_container(repo_root(), name=body.name)
    except WorldContainerRegistryError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return record.model_dump(mode="json")
