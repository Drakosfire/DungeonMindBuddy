"""Bounded initial owner-only access to the hosted native graph explorer.

Authentication is DMS-owned. APP owns exact World ownership. Existing action
sharing grants are not native GM visibility roles and are deliberately not
promoted by this first hosted capability.
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import HTTPException, Request
from pydantic import TypeAdapter

from apps.live_control_server.models.native_graph_explorer import (
    NativeGraphExplorerGraphRequest,
    NativeGraphExplorerOperationRequest,
    NativeGraphExplorerPrepareRequest,
)
from apps.live_control_server.models.native_graph_inspection import InspectionRead
from apps.live_control_server.services import hosted_auth
from apps.live_control_server.services.agent_graph_auth import (
    NativeGraphPrincipal,
    enforce_native_graph_gm,
)
from apps.live_control_server.services.dms_principal import DmsPrincipal
from apps.live_control_server.services.world_container_registry import (
    WorldContainerPublicRecord,
    WorldContainersListResponse,
    WorldContainerRegistryError,
    get_world_container,
    list_world_containers,
)


EXPLORER_PREFIX = "/api/live/native-graph-explorer"
WORLD_COLLECTION_PATH = "/api/live/world-containers"
INSPECTION_READ_PATH = "/api/live/native-graph-inspection/read"
_REQUESTS = {
    INSPECTION_READ_PATH: TypeAdapter(InspectionRead),
    f"{EXPLORER_PREFIX}/graph": TypeAdapter(NativeGraphExplorerGraphRequest),
    f"{EXPLORER_PREFIX}/prepare": TypeAdapter(NativeGraphExplorerPrepareRequest),
    f"{EXPLORER_PREFIX}/confirm": TypeAdapter(NativeGraphExplorerOperationRequest),
    f"{EXPLORER_PREFIX}/operations/read": TypeAdapter(
        NativeGraphExplorerOperationRequest
    ),
}


@dataclass(frozen=True)
class HostedOwnerGraphPrincipal(NativeGraphPrincipal):
    """A request-scoped owner principal, bound to exactly one managed World."""

    managed_world_id: str
    dms_subject: str


def _denied() -> HTTPException:
    return HTTPException(
        status_code=403, detail={"code": "owned_world_access_required"}
    )


def _unavailable() -> HTTPException:
    return HTTPException(
        status_code=503, detail={"code": "world_authorization_unavailable"}
    )


def _hosted_subject(request: Request) -> str:
    if (
        hosted_auth.deployment_environment() != hosted_auth.PRODUCTION_ENVIRONMENT
        or hosted_auth.auth_mode() != hosted_auth.HOSTED_MODE
    ):
        raise _unavailable()
    principal = getattr(request.state, "dms_principal", None)
    # Only the actual introspection boundary supplies this typed identity.
    if not isinstance(principal, DmsPrincipal) or not principal.subject.strip():
        raise HTTPException(status_code=401, detail={"code": "authentication_required"})
    return principal.subject


def _owned_world(subject: str, managed_world_id: str):
    hosted_auth.authorize_world_access(
        subject, frozenset({managed_world_id}), access=hosted_auth.hosted_world_access()
    )
    try:
        world = get_world_container(managed_world_id)
    except WorldContainerRegistryError as exc:
        if exc.status_code == 404:
            raise _denied() from None
        raise _unavailable() from None
    except Exception:
        raise _unavailable() from None
    if world.world_id != managed_world_id or world.owner_subject != subject:
        raise _denied()
    return world


async def resolve_hosted_explorer_world(request: Request) -> str:
    """Resolve a closed request through server-owned catalog state, never labels."""
    subject = _hosted_subject(request)
    if (
        request.method != "POST"
        or request.url.path not in _REQUESTS
        or request.query_params
    ):
        raise _denied()
    # The hosted middleware already bounds bytes and rejects duplicate keys and
    # conflicting selectors before invoking this exact code-owned resolver.
    body = _REQUESTS[request.url.path].validate_python(await request.json())
    if isinstance(body, InspectionRead):
        if body.scope.scope_mode != "world":
            raise _denied()
        managed_world_id = body.scope.managed_world_id
    else:
        managed_world_id = body.managed_world_id
    world = _owned_world(subject, managed_world_id)
    request.state.hosted_native_graph_world = world.world_id
    return world.world_id


async def native_graph_explorer_dependency(request: Request) -> NativeGraphPrincipal:
    if (
        hosted_auth.deployment_environment() in hosted_auth.LOCAL_ENVIRONMENTS
        and hosted_auth.auth_mode() == hosted_auth.LOCAL_MODE
    ):
        return enforce_native_graph_gm(request)
    subject = _hosted_subject(request)
    hosted_auth.require_hosted_write_origin(request)
    # Require a fresh lookup here as well: middleware admission is not a cached
    # permission grant and a direct/mis-mounted route must fail closed.
    world_id = getattr(request.state, "hosted_native_graph_world", None)
    if not isinstance(world_id, str) or not world_id:
        raise _denied()
    _owned_world(subject, world_id)
    return HostedOwnerGraphPrincipal(
        subject=f"hosted_dms:{subject}",
        dms_subject=subject,
        role="gm",
        auth_method="hosted_owner",
        managed_world_id=world_id,
    )


def require_explorer_access(
    principal: NativeGraphPrincipal, managed_world_id: str
) -> None:
    """Recheck current permission before effects and before disclosing results."""
    if isinstance(principal, HostedOwnerGraphPrincipal):
        if (
            principal.auth_method != "hosted_owner"
            or principal.subject != f"hosted_dms:{principal.dms_subject}"
            or principal.role != "gm"
            or principal.managed_world_id != managed_world_id
            or hosted_auth.deployment_environment()
            != hosted_auth.PRODUCTION_ENVIRONMENT
            or hosted_auth.auth_mode() != hosted_auth.HOSTED_MODE
        ):
            raise _denied()
        _owned_world(principal.dms_subject, managed_world_id)
    elif principal.auth_method == "hosted_owner":
        # The global principal type alone carries no scoped ownership proof.
        raise _denied()


async def hosted_owner_collection(request: Request) -> dict:
    """Authorize the one exact existing-World collection without foreign metadata."""
    _hosted_subject(request)
    if (
        request.method != "GET"
        or request.url.path != WORLD_COLLECTION_PATH
        or request.query_params
        or await request.body()
    ):
        raise _denied()
    return revalidate_hosted_owner_collection(request)


def revalidate_hosted_owner_collection(request: Request) -> dict:
    """Read current owner-filtered metadata after collection request admission."""
    subject = _hosted_subject(request)
    access = hosted_auth.hosted_world_access()
    try:
        records = list_world_containers()
        permitted = [
            WorldContainerPublicRecord.from_record(world)
            for world in records
            if world.owner_subject == subject
            and subject in access.get(world.world_id, ())
        ]
    except Exception:
        raise _unavailable() from None
    return WorldContainersListResponse(records=permitted).model_dump(mode="json")
