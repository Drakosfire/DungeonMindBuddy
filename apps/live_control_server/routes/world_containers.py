"""Managed world-container list/create API for Build new-world creation."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, Response

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
def get_world_containers(request: Request = None) -> WorldContainersListResponse | dict[str, Any]:
    from apps.live_control_server.services import hosted_auth
    from apps.live_control_server.services.hosted_native_graph_access import revalidate_hosted_owner_collection

    if hosted_auth.deployment_environment() == hosted_auth.PRODUCTION_ENVIRONMENT:
        if request is None or not isinstance(getattr(request.state, "hosted_world_collection", None), dict):
            raise HTTPException(status_code=403, detail={"code": "owned_world_access_required"})
        # Recheck current records rather than treating middleware's result as a
        # persistent permission snapshot. No unfiltered local list is exposed.
        return revalidate_hosted_owner_collection(request)
    try:
        records = list_world_containers()
    except WorldContainerRegistryError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return WorldContainersListResponse(
        records=[WorldContainerPublicRecord.from_record(record) for record in records]
    )


@router.get("/world-containers/lookup", response_model=WorldContainerPublicRecord)
def lookup_hosted_world_container(
    request: Request, response: Response, managed_world_id: str, background_tasks: BackgroundTasks
) -> WorldContainerPublicRecord:
    from apps.live_control_server.services.hosted_native_graph_access import read_hosted_world_lookup

    response.headers["Cache-Control"] = "no-store"
    return read_hosted_world_lookup(request, managed_world_id, background_tasks)


@router.post("/world-containers", response_model=WorldContainerPublicRecord)
def post_world_container(
    body: CreateWorldContainerRequest, request: Request = None, response: Response = None,
) -> WorldContainerPublicRecord:
    from apps.live_control_server.services import hosted_auth

    if hosted_auth.deployment_environment() == hosted_auth.PRODUCTION_ENVIRONMENT:
        from application_state.errors import ApplicationStateError
        from application_state.world_catalog.hosted_creation import create_owned_world
        from apps.live_control_server.services.hosted_native_graph_access import _hosted_subject

        if request is None or getattr(request.state, "hosted_world_collection", None) != {"owner_creation": True}:
            raise HTTPException(status_code=403, detail={"code": "owned_world_access_required"})
        subject = _hosted_subject(request)
        hosted_auth.require_hosted_write_origin(request)
        if body.request_key is None:
            raise HTTPException(status_code=422, detail={"code": "creation_key_required"})
        try:
            record = create_owned_world(subject=subject, name=body.name, request_key=body.request_key).record
        except ApplicationStateError as exc:
            raise HTTPException(status_code=exc.status_code, detail={"code": "world_creation_unavailable"}) from exc
        if response is not None:
            response.headers["Cache-Control"] = "no-store"
        return WorldContainerPublicRecord.from_record(record)
    if body.request_key is not None:
        raise HTTPException(status_code=422, detail={"code": "unexpected_creation_key"})
    try:
        record = create_world_container(name=body.name)
    except WorldContainerRegistryError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return WorldContainerPublicRecord.from_record(record)


@router.put(
    "/world-containers/{managed_world_id}/native-graph-binding",
    response_model=WorldContainerPublicRecord,
)
def put_native_graph_binding(
    managed_world_id: str,
    body: BindNativeGraphRequest,
    request: Request,
) -> WorldContainerPublicRecord:
    enforce_native_graph_gm(request)
    try:
        record = bind_native_graph(
            managed_world_id,
            native_world_id=body.native_world_id,
            expected_binding_version=body.expected_binding_version,
        )
    except (WorldGraphBindingError, WorldContainerRegistryError) as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return WorldContainerPublicRecord.from_record(record)


@router.post(
    "/world-containers/{managed_world_id}/native-graph-binding/deactivate",
    response_model=WorldContainerPublicRecord,
)
def post_deactivate_native_graph_binding(
    managed_world_id: str,
    body: DeactivateNativeGraphBindingRequest,
    request: Request,
) -> WorldContainerPublicRecord:
    enforce_native_graph_gm(request)
    try:
        record = deactivate_native_graph_binding(
            managed_world_id,
            expected_binding_version=body.expected_binding_version,
        )
    except (WorldGraphBindingError, WorldContainerRegistryError) as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return WorldContainerPublicRecord.from_record(record)
