"""Bounded initial owner-only access to the hosted native graph explorer.

Authentication is DMS-owned. APP owns exact World ownership. Existing action
sharing grants are not native GM visibility roles and are deliberately not
promoted by this first hosted capability.
"""

from __future__ import annotations

from collections.abc import Callable

from dataclasses import dataclass
import logging
import os
from threading import Lock
from time import monotonic
from uuid import UUID

from fastapi import BackgroundTasks, HTTPException, Request
from application_state.errors import ApplicationStateError
from pydantic import TypeAdapter
from starlette.concurrency import run_in_threadpool

from application_state.world_catalog import service as catalog

from apps.live_control_server.models.threat_query_hydration import ThreatQueryHydrationRequestV1
from apps.live_control_server.models.native_graph_explorer import (
    NativeGraphExplorerGraphRequest,
    NativeGraphExplorerOperationRequest,
    NativeGraphExplorerPrepareRequest,
)
from apps.live_control_server.models.native_graph_inspection import InspectionPin, InspectionRead, InspectionScope, NativeCompleteObjectRead, NativeRecapPageRequest, NativeRelatedRecapsRequest
from apps.live_control_server.models.native_source_inspection import NativeSourceRead, PublishedRecapObjectsRead, PublishedRecapRead
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
)


FIRST_WORLD_PREPARE_PATH = "/api/live/extract-promote/worldbuilding/first-world/prepare"
FIRST_WORLD_CONFIRM_PATH = "/api/live/extract-promote/worldbuilding/first-world/confirm"
EXPLORER_PREFIX = "/api/live/native-graph-explorer"
WORLD_COLLECTION_PATH = "/api/live/world-containers"
WORLD_LOOKUP_PATH = f"{WORLD_COLLECTION_PATH}/lookup"
BUILD_PDF_SOURCES_PATH = hosted_auth.BUILD_PDF_SOURCES_PATH
BUILD_PAGE_INVENTORY_PATH = "/api/live/workspace-documents/pages/inventory"
INSPECTION_READ_PATH = "/api/live/native-graph-inspection/read"
COMPLETE_OBJECT_PATH = "/api/live/native-graph-inspection/complete-object"
_REQUESTS = {
    COMPLETE_OBJECT_PATH: TypeAdapter(NativeCompleteObjectRead),
    "/api/live/native-source-inspection/published-recap": TypeAdapter(PublishedRecapRead),
    "/api/live/native-source-inspection/published-recap/objects": TypeAdapter(PublishedRecapObjectsRead),
    "/api/live/native-graph-inspection/authoring-identities": TypeAdapter(InspectionPin | InspectionScope),
    "/api/live/native-graph-inspection/recap-page": TypeAdapter(NativeRecapPageRequest),
    "/api/live/native-graph-inspection/related-recaps": TypeAdapter(NativeRelatedRecapsRequest),
    "/api/live/native-graph-inspection/catalog": TypeAdapter(InspectionPin | InspectionScope),
    "/api/live/native-source-inspection/catalog": TypeAdapter(InspectionScope),
    "/api/live/native-source-inspection/prewarm": TypeAdapter(InspectionScope),
    "/api/live/native-source-inspection/read": TypeAdapter(NativeSourceRead),

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


def _owner_world_candidates(subject: str) -> frozenset[str]:
    """Combine existing static candidates with current owner-created grants."""
    static_ids = frozenset(
        world_id for world_id, subjects in hosted_auth.hosted_world_access().items()
        if subject in subjects
    )
    if os.environ.get("DMB_HOSTED_OWNER_CREATION_CAPABILITY", "") != "1":
        return static_ids
    from application_state.world_catalog.hosted_creation import active_admitted_world_ids

    try:
        return static_ids | active_admitted_world_ids(subject)
    except ApplicationStateError:
        # Existing statically admitted Worlds remain available if the dynamic
        # policy store is unavailable. A user with no static fallback sees an
        # unavailable response rather than a falsely empty list.
        if static_ids:
            return static_ids
        raise _unavailable() from None


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
    if isinstance(body, NativeCompleteObjectRead):
        scope, projection = body.scope, body.request
        if (
            scope is None
            or scope.scope_mode != "world"
            or projection.scope_mode != "world"
            or projection.world_id != scope.managed_world_id
            or projection.revision_pin != scope.revision_id
            or projection.admissibility != "gm"
        ):
            raise _denied()
        managed_world_id = scope.managed_world_id
    elif isinstance(body, NativeRecapPageRequest):
        if body.read.selection.kind != "source" or body.read.scope.scope_mode != "world":
            raise _denied()
        managed_world_id = body.read.scope.managed_world_id
    elif isinstance(body, (InspectionRead, NativeSourceRead, NativeRelatedRecapsRequest)):
        if body.scope.scope_mode != "world":
            raise _denied()
        managed_world_id = body.scope.managed_world_id
    else:
        if isinstance(body, (InspectionPin, InspectionScope)) and body.scope_mode != "world":
            raise _denied()
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


async def resolve_hosted_first_world(request: Request) -> str:
    """Authorize current preparation or signed, owner-scoped native recovery."""
    from apps.live_control_server import config
    from apps.live_control_server.models.extract_promote import (
        FirstWorldGraphConfirmRequest, FirstWorldGraphPrepareRequest,
    )
    from apps.live_control_server.services.promotable_ingest_run import (
        PromotableIngestRunError, resolve_promotable_ingest_run,
    )

    subject = _hosted_subject(request)
    if request.query_params:
        raise _denied()
    body = await request.json()
    from apps.live_control_server.models.native_first_world_publication import (
        NATIVE_CONFIRM_SCHEMA, NATIVE_PREPARE_SCHEMA,
        NativeFirstWorldConfirmRequest, NativeFirstWorldPrepareRequest,
    )
    if request.url.path == FIRST_WORLD_CONFIRM_PATH and isinstance(body, dict) and body.get("schema") == NATIVE_CONFIRM_SCHEMA:
        from apps.live_control_server.services.native_first_world_publication import decode_native_plan

        confirmation = NativeFirstWorldConfirmRequest.model_validate(body)
        plan = await run_in_threadpool(
            decode_native_plan, confirmation.plan, principal_subject=f"hosted_dms:{subject}",
        )
        # A signed retained request owns recovery scope. Today's mutable run or
        # document may no longer exist; current ownership is still mandatory.
        await run_in_threadpool(_owned_world, subject, plan.world_id)
        request.state.hosted_first_world = plan.world_id
        return plan.world_id
    if request.url.path == FIRST_WORLD_PREPARE_PATH:
        payload = (NativeFirstWorldPrepareRequest.model_validate(body)
                   if isinstance(body, dict) and body.get("schema") == NATIVE_PREPARE_SCHEMA
                   else FirstWorldGraphPrepareRequest.model_validate(body))
        run_id = payload.run_id
        claimed_world = None
    elif request.url.path == FIRST_WORLD_CONFIRM_PATH:
        from apps.live_control_server.services.first_world_graph_publication import recover_historical_first_world

        confirmation = FirstWorldGraphConfirmRequest.model_validate(body)
        claimed_world = confirmation.plan.world_id
        await run_in_threadpool(_owned_world, subject, claimed_world)
        # Old browser claims alone are insufficient. The actual Core receipt
        # must match this current reservation before hosted recovery is admitted.
        await run_in_threadpool(recover_historical_first_world, confirmation,
            authorize_world=lambda world: _owned_world(subject, world))
        request.state.hosted_first_world = claimed_world
        return claimed_world
    else:
        raise _denied()

    try:
        run = await run_in_threadpool(resolve_promotable_ingest_run, run_id, root=config.repo_root())
    except PromotableIngestRunError:
        raise _denied() from None
    world_id = run.world_id
    if not world_id or (claimed_world is not None and claimed_world != world_id):
        raise _denied()
    await run_in_threadpool(_owned_world, subject, world_id)
    request.state.hosted_first_world = world_id
    return world_id


def first_world_authorizer(request: Request):
    """Preserve local GM authority and recheck hosted ownership of the resolved run."""
    if hosted_auth.deployment_environment() in hosted_auth.LOCAL_ENVIRONMENTS:
        enforce_native_graph_gm(request)
        return None

    def authorize(world_id: str) -> None:
        if not world_id or getattr(request.state, "hosted_first_world", None) != world_id:
            raise _denied()
        _owned_world(_hosted_subject(request), world_id)

    return authorize


async def resolve_hosted_image_preparation(request: Request) -> str:
    world_id = request.query_params.get("world_id")
    if not world_id or request.query_params.multi_items() != [("world_id", world_id)] or await request.body():
        raise _denied()
    world = await run_in_threadpool(_owned_world, _hosted_subject(request), world_id)
    request.state.hosted_conversation_world = world.world_id
    return world.world_id


async def resolve_hosted_image_history(request: Request) -> str:
    selectors = request.query_params
    world_id = selectors.get("world_id")
    if (not world_id or len(selectors.multi_items()) != 2
        or set(selectors) != {"world_id", "conversation_id"} or await request.body()):
        raise _denied()
    UUID(selectors["conversation_id"])
    world = await run_in_threadpool(_owned_world, _hosted_subject(request), world_id)
    request.state.hosted_conversation_world = world.world_id
    return world.world_id


async def resolve_hosted_image_world(request: Request) -> str:
    world_id = request.query_params.get("world_id")
    if not world_id or request.query_params.multi_items() != [("world_id", world_id)]:
        raise _denied()
    if request.method == "GET" and await request.body():
        raise _denied()
    world = await run_in_threadpool(_owned_world, _hosted_subject(request), world_id)
    request.state.hosted_conversation_world = world.world_id
    return world.world_id


async def resolve_hosted_mechanics_association(request: Request) -> str:
    from application_state.world_mechanics.types import AssociateWorldMechanicsRequest

    body = AssociateWorldMechanicsRequest.model_validate(await request.json())
    world_id = body.target.managed_world_id
    if request.query_params.multi_items() != [("world_id", world_id)]:
        raise _denied()
    world = await run_in_threadpool(_owned_world, _hosted_subject(request), world_id)
    request.state.hosted_conversation_world = world.world_id
    return world.world_id


async def resolve_hosted_native_creature(request: Request) -> str:
    from apps.live_control_server.models.native_threat_creation import ConfirmNativeThreat, PrepareNativeThreat

    draft_id = getattr(request.state, "hosted_route_draft_id", None)
    if not draft_id:
        raise _denied()
    if request.method == "GET":
        world_id = request.query_params.get("world_id")
        if not world_id or request.query_params.multi_items() != [("world_id", world_id)] or await request.body():
            raise _denied()
    else:
        if request.query_params:
            raise _denied()
        if request.url.path.endswith("/confirm"):
            review = ConfirmNativeThreat.model_validate(await request.json()).review
            if str(review.draft_id) != draft_id:
                raise _denied()
            world_id = review.world_id
        else:
            world_id = PrepareNativeThreat.model_validate(await request.json()).world_id
    world = await run_in_threadpool(_owned_world, _hosted_subject(request), world_id)
    request.state.hosted_conversation_world = world.world_id
    return world.world_id


async def resolve_hosted_connected_page(request: Request) -> str:
    if request.method == "GET":
        world_id = request.query_params.get("world_id")
        if request.query_params.multi_items() != [("world_id", world_id)] or await request.body():
            raise _denied()
    else:
        if request.query_params:
            raise _denied()
        body = await request.json()
        world_id = body.get("world_id") if isinstance(body, dict) else None
    if not isinstance(world_id, str) or not world_id:
        raise _denied()
    world = await run_in_threadpool(_owned_world, _hosted_subject(request), world_id)
    request.state.hosted_conversation_world = world.world_id
    return world.world_id


async def resolve_hosted_build_insertion_ack(request: Request) -> str:
    revision = request.query_params.get("expected_revision")
    world_id = getattr(request.state, "hosted_route_world_id", None)
    if (
        not world_id or not revision
        or request.query_params.multi_items() != [("expected_revision", revision)]
        or await request.body()
    ):
        raise _denied()
    world = await run_in_threadpool(_owned_world, _hosted_subject(request), world_id)
    request.state.hosted_conversation_world = world.world_id
    return world.world_id


async def resolve_hosted_conversation_world(request: Request) -> str:
    world_id = getattr(request.state, "hosted_route_world_id", None)
    if not world_id or (request.method == "GET" and await request.body()):
        raise _denied()
    if request.method == "POST" and request.query_params:
        raise _denied()
    world = await run_in_threadpool(_owned_world, _hosted_subject(request), world_id)
    request.state.hosted_conversation_world = world.world_id
    return world.world_id


async def resolve_hosted_chat_turn(request: Request) -> str:
    from apps.live_control_server.models.agent_turn import AgentTurnRequest, AgentTurnWorldOwner

    if request.query_params:
        raise _denied()
    body = AgentTurnRequest.model_validate(await request.json())
    if not isinstance(body.owner_scope, AgentTurnWorldOwner):
        raise _denied()
    world = await run_in_threadpool(_owned_world, _hosted_subject(request), body.owner_scope.world_id)
    request.state.hosted_conversation_world = world.world_id
    return world.world_id


async def resolve_hosted_native_relationship(request: Request) -> str:
    if request.query_params:
        raise _denied()
    body = await request.json()
    if not isinstance(body, dict):
        raise _denied()
    review = body if request.url.path.endswith("/request") else body.get("review")
    world_id = review.get("world_id") if isinstance(review, dict) else None
    if not isinstance(world_id, str) or not world_id:
        raise _denied()
    world = await run_in_threadpool(_owned_world, _hosted_subject(request), world_id)
    request.state.hosted_conversation_world = world.world_id
    return world.world_id


def conversation_graph_principal(
    request: Request, world_id: str, *, authorize_local: Callable[[Request], NativeGraphPrincipal],
) -> NativeGraphPrincipal:
    if hosted_auth.deployment_environment() in hosted_auth.LOCAL_ENVIRONMENTS:
        return authorize_local(request)
    require_conversation_access(request, world_id, authorize_local=authorize_local)
    subject = _hosted_subject(request)
    return HostedOwnerGraphPrincipal(
        subject=f"hosted_dms:{subject}", dms_subject=subject, role="gm",
        auth_method="hosted_owner", managed_world_id=world_id,
    )


def require_conversation_access(
    request: Request, world_id: str, *, authorize_local: Callable[[Request], object],
) -> None:
    if hosted_auth.deployment_environment() in hosted_auth.LOCAL_ENVIRONMENTS:
        authorize_local(request)
        return
    if getattr(request.state, "hosted_conversation_world", None) != world_id:
        raise _denied()
    _owned_world(_hosted_subject(request), world_id)


async def resolve_hosted_build_pdf_world(request: Request) -> str:
    subject = _hosted_subject(request)
    world_id = getattr(request.state, "hosted_route_world_id", None)
    if not world_id:
        raise _denied()
    world = _owned_world(subject, world_id)
    request.state.hosted_build_pdf_world = world.world_id
    return world.world_id


def require_build_pdf_access(request: Request, world_id: str) -> NativeGraphPrincipal:
    if hosted_auth.deployment_environment() in hosted_auth.LOCAL_ENVIRONMENTS:
        return enforce_native_graph_gm(request)
    if getattr(request.state, "hosted_build_pdf_world", None) != world_id:
        raise _denied()
    subject = _hosted_subject(request)
    _owned_world(subject, world_id)
    return HostedOwnerGraphPrincipal(
        subject=f"hosted_dms:{subject}",
        dms_subject=subject,
        role="gm",
        auth_method="hosted_owner",
        managed_world_id=world_id,
    )


async def resolve_hosted_build_page_create(request: Request) -> str:
    from apps.live_control_server.services.workspace_document_registry import CreateWorkspaceDocumentRequest

    subject = _hosted_subject(request)
    create = CreateWorkspaceDocumentRequest.model_validate(await request.json())
    world_id = create.world_id
    if (
        not world_id or create.kind != "worldbuilding_source"
        or create.campaign_id != world_id
        or create.target_session is not None or create.target_relpath is not None
        or create.authority_state not in (None, "draft")
        or create.visibility_state not in (None, "internal")
    ):
        raise _denied()
    await run_in_threadpool(_owned_world, subject, world_id)
    request.state.hosted_build_page_world = world_id
    return world_id


async def resolve_hosted_build_page(request: Request) -> str:
    from apps.live_control_server.services.tiptap_markdown_write import (
        TiptapMarkdownWriteCommitRequest, TiptapMarkdownWritePrepareRequest,
    )
    subject = _hosted_subject(request)
    plan_write_world = None
    if request.method == "GET":
        document_id = getattr(request.state, "hosted_route_document_id", None)
    else:
        model = (
            TiptapMarkdownWritePrepareRequest if request.url.path.endswith("/prepare")
            else TiptapMarkdownWriteCommitRequest
        )
        write = model.model_validate(await request.json())
        plan_write_world = write.world_id
        document_id = write.document_id
    plan_snapshot = request.method == "GET" and request.url.path.endswith("/snapshot") and not request.query_params
    world_id = await _owned_build_page(
        subject, document_id, allow_plan_snapshot=plan_snapshot, plan_write_world=plan_write_world
    )
    if plan_snapshot or plan_write_world is not None:
        request.state.hosted_plan_context_world = world_id
    request.state.hosted_build_page_world = world_id
    return world_id


async def resolve_hosted_play_preparation(request: Request) -> str:
    from application_state.play.session_encounter_types import WorldSessionSourceRequest

    world_id = request.query_params.get("world_id")
    entry_scene_id = request.query_params.get("entry_scene_id")
    selectors = sorted(request.query_params.multi_items())
    expected = [("world_id", world_id)]
    if entry_scene_id:
        expected.insert(0, ("entry_scene_id", entry_scene_id))
    if not world_id or selectors != expected:
        raise _denied()
    source = WorldSessionSourceRequest.model_validate(await request.json())
    owned_world = await _owned_build_page(
        _hosted_subject(request), str(source.playable_artifact_id), plan_write_world=world_id,
    )
    request.state.hosted_plan_context_world = owned_world
    return owned_world


async def resolve_hosted_workspace_lifecycle(request: Request) -> str:
    return await _resolve_hosted_play_world(request)


async def resolve_hosted_play_read(request: Request) -> str:
    if await request.body():
        raise _denied()
    return await _resolve_hosted_play_world(request)


async def resolve_hosted_play_scene_proposal(request: Request) -> str:
    return await _resolve_hosted_play_world(request)


async def resolve_hosted_play_command(request: Request) -> str:
    return await _resolve_hosted_play_world(request)


async def resolve_hosted_play_table_receipts(request: Request) -> str:
    if await request.body():
        raise _denied()
    return await _resolve_hosted_play_world(request, pagination_keys={"before", "limit"})


async def resolve_hosted_play_table_roll(request: Request) -> str:
    return await _resolve_hosted_play_world(request)


async def _resolve_hosted_play_world(
    request: Request, *, pagination_keys: frozenset[str] | set[str] = frozenset()
) -> str:
    world_id = request.query_params.get("world_id")
    selectors = request.query_params.multi_items()
    if (
        not world_id
        or len(selectors) != len(request.query_params)
        or any(key != "world_id" and key not in pagination_keys for key, _ in selectors)
    ):
        raise _denied()
    run_id = getattr(request.state, "hosted_route_run_id", None)
    if run_id is not None:
        try:
            if str(UUID(run_id)) != run_id:
                raise _denied()
        except ValueError:
            raise _denied() from None
    world = await run_in_threadpool(_owned_world, _hosted_subject(request), world_id)
    request.state.hosted_plan_context_world = world.world_id
    return world.world_id


async def resolve_hosted_play_creation(request: Request) -> str:
    from application_state.play.session_encounter_types import WorldSessionCreateRequest

    world_id = request.query_params.get("world_id")
    run_id = getattr(request.state, "hosted_route_run_id", None)
    if not world_id or request.query_params.multi_items() != [("world_id", world_id)] or not run_id:
        raise _denied()
    try:
        if str(UUID(run_id)) != run_id:
            raise _denied()
    except ValueError:
        raise _denied() from None
    subject = _hosted_subject(request)
    if request.method == "GET":
        if await request.body():
            raise _denied()
        world = await run_in_threadpool(_owned_world, subject, world_id)
        world_id = world.world_id
    else:
        source = WorldSessionCreateRequest.model_validate(await request.json())
        world_id = await _owned_build_page(subject, str(source.playable_artifact_id), plan_write_world=world_id)
    request.state.hosted_plan_context_world = world_id
    return world_id


async def resolve_hosted_committed_plan(request: Request) -> str:
    if request.query_params or await request.body():
        raise _denied()
    world_id = await _owned_build_page(
        _hosted_subject(request), getattr(request.state, "hosted_route_document_id", None), plan_only=True
    )
    request.state.hosted_plan_context_world = world_id
    return world_id


async def _owned_build_page(
    subject: str, document_id: str | None, *,
    allow_plan_snapshot: bool = False, plan_write_world: str | None = None, plan_only: bool = False,
) -> str:
    from apps.live_control_server import config
    from apps.live_control_server.services.workspace_document_registry import (
        WorldOwnedPlanRecordV2, WorkspaceDocumentRegistryError, get_workspace_document,
    )

    try:
        if not document_id or str(UUID(document_id)) != document_id:
            raise _denied()
    except ValueError:
        raise _denied() from None
    try:
        record = await run_in_threadpool(get_workspace_document, config.repo_root(), document_id)
    except WorkspaceDocumentRegistryError as exc:
        if exc.status_code == 404:
            raise _denied() from None
        raise _unavailable() from None
    if plan_only or plan_write_world is not None:
        if not isinstance(record, WorldOwnedPlanRecordV2) or (
            plan_write_world is not None and record.world_id != plan_write_world
        ):
            raise _denied()
    elif not record.world_id or not (
        record.kind == "worldbuilding_source" or (allow_plan_snapshot and isinstance(record, WorldOwnedPlanRecordV2))
    ):
        raise _denied()
    await run_in_threadpool(_owned_world, subject, record.world_id)
    return record.world_id


async def resolve_hosted_statblock_inventory(request: Request) -> str:
    world_id = request.query_params.get("world_id")
    selectors = request.query_params.multi_items()
    allowed = {"world_id"}
    if request.url.path.endswith("/threat-drafts"):
        allowed.update({"limit", "offset"})
    if request.url.path.endswith("/saved-statblocks/lookup"):
        if not request.query_params.get("name", "").strip():
            raise _denied()
        allowed.add("name")
    keys = {key for key, _ in selectors}
    if not world_id or len(keys) != len(selectors) or not keys <= allowed or await request.body():
        raise _denied()
    world = await run_in_threadpool(_owned_world, _hosted_subject(request), world_id)
    request.state.hosted_plan_context_world = world.world_id
    return world.world_id


async def resolve_hosted_combat_encounter(request: Request) -> str:
    world_id = request.query_params.get("world_id")
    selectors = request.query_params.multi_items()
    keys = {key for key, _ in selectors}
    allowed = {"world_id"}
    if request.method == "GET" and request.url.path.endswith("/mechanics-adoptions"):
        allowed.update(("before_operation_id", "limit"))
    if not world_id or len(keys) != len(selectors) or not keys <= allowed:
        raise _denied()
    if request.method == "GET" and await request.body():
        raise _denied()
    world = await run_in_threadpool(_owned_world, _hosted_subject(request), world_id)
    request.state.hosted_combat_encounter_world = world.world_id
    return world.world_id


def require_combat_encounter_access(request: Request, world_id: str) -> None:
    if hosted_auth.deployment_environment() in hosted_auth.LOCAL_ENVIRONMENTS:
        enforce_native_graph_gm(request)
        return
    if getattr(request.state, "hosted_combat_encounter_world", None) != world_id:
        raise _denied()
    _owned_world(_hosted_subject(request), world_id)


async def resolve_hosted_statblock_revision_save(request: Request) -> str:
    from apps.live_control_server.models.statblock_saved_revision import SaveMechanicsRevisionRequest

    if request.query_params:
        raise _denied()
    body = SaveMechanicsRevisionRequest.model_validate(await request.json())
    world = await run_in_threadpool(_owned_world, _hosted_subject(request), body.world_id)
    request.state.hosted_build_pdf_world = world.world_id
    return world.world_id


async def resolve_hosted_saved_statblock(request: Request) -> str:
    selectors = request.query_params.multi_items()
    world_id = request.query_params.get("world_id")
    keys = {key for key, _ in selectors}
    allowed = {"world_id", "limit", "offset"} if request.url.path.endswith("/mechanics-revisions") else {"world_id"}
    if request.method == "DELETE":
        allowed = {"world_id", "expected_version"}
        if keys != allowed:
            raise _denied()
    if not world_id or len(keys) != len(selectors) or not keys <= allowed or await request.body():
        raise _denied()
    world = await run_in_threadpool(_owned_world, _hosted_subject(request), world_id)
    # The exact revision may include a portrait from a World-owned PDF review.
    request.state.hosted_build_pdf_world = world.world_id
    return world.world_id


async def resolve_hosted_build_native_source(request: Request) -> str:
    selectors = request.query_params.multi_items()
    if request.method == "POST":
        from apps.live_control_server.routes.workspace_documents import NativeWorldSourceAdmissionRequest

        if selectors:
            raise _denied()
        NativeWorldSourceAdmissionRequest.model_validate(await request.json())
    elif await request.body() or (selectors and (
        len(selectors) != 1 or selectors[0][0] != "expected_revision"
    )):
        raise _denied()
    world_id = await _owned_build_page(
        _hosted_subject(request), getattr(request.state, "hosted_route_document_id", None),
    )
    request.state.hosted_build_page_world = world_id
    return world_id


def require_hosted_build_native_source(request: Request | None, world_id: str) -> None:
    if hosted_auth.deployment_environment() != hosted_auth.PRODUCTION_ENVIRONMENT:
        return
    if request is None or getattr(request.state, "hosted_build_page_world", None) != world_id:
        raise _denied()
    _owned_world(_hosted_subject(request), world_id)


async def resolve_hosted_saved_recap(request: Request) -> str:
    selectors = request.query_params.multi_items()
    keys = {key for key, _ in selectors}
    world_id = request.query_params.get("managed_world_id")
    if request.url.path.endswith("/recap-inspection"):
        valid_keys = keys == {"managed_world_id", "expected_run_revision", "source_revision_id"}
    elif request.url.path.endswith("/usage"):
        valid_keys = keys == {"managed_world_id", "expected_run_revision"}
    elif request.url.path.endswith(("/candidate-projection", "/recap-projection")):
        valid_keys = keys == {"managed_world_id"}
    else:
        valid_keys = keys <= {"managed_world_id", "campaign_id"}
    if not world_id or not valid_keys or len(keys) != len(selectors) or await request.body():
        raise _denied()
    world = await run_in_threadpool(_owned_world, _hosted_subject(request), world_id)
    request.state.hosted_saved_recap_world = world.world_id
    return world.world_id


def require_saved_recap_access(request: Request, world_id: str) -> None:
    if hosted_auth.deployment_environment() in hosted_auth.LOCAL_ENVIRONMENTS:
        enforce_native_graph_gm(request)
        return
    if getattr(request.state, "hosted_saved_recap_world", None) != world_id:
        raise _denied()
    _owned_world(_hosted_subject(request), world_id)


async def resolve_hosted_manual_knowledge(request: Request) -> str:
    from apps.live_control_server.services.graph_object_authoring_prepare import (
        GraphObjectAuthoringCommitRequest, GraphObjectAuthoringPrepareRequest,
    )
    from apps.live_control_server.services.graph_run_registry import GraphRunRegistryError, get_extraction_run
    from apps.live_control_server.services.source_artifact_registry import SourceArtifactRegistryError, get_source_artifact

    if request.query_params:
        raise _denied()
    model = GraphObjectAuthoringCommitRequest if request.url.path.endswith("/commit") else GraphObjectAuthoringPrepareRequest
    body = model.model_validate(await request.json())
    if (
        not body.world_id or body.campaign_id != body.world_id or not body.source_run_id
        or body.document_source is not None or body.recap_artifact_id is not None
        or body.session_id is not None or body.campaign_rel is not None
        or len(body.proposals) != 1 or body.proposals[0].proposal_kind not in {"object", "relationship"}
    ):
        raise _denied()
    subject = _hosted_subject(request)
    _owned_world(subject, body.world_id)
    if isinstance(body, GraphObjectAuthoringCommitRequest):
        from apps.live_control_server.services.graph_object_authoring_prepare import (
            GraphObjectAuthoringError, decode_publication_intent,
        )
        from apps.live_control_server.integrations.dungeonmind.historical_manual_recovery import authorize_original_binding

        try:
            intent = decode_publication_intent(body.confirm_token, allow_expired_recovery=True)
            if (intent.get("campaign_id") != body.campaign_id
                    or intent.get("source_run_id") != body.source_run_id):
                raise _denied()
            await run_in_threadpool(authorize_original_binding, body, intent,
                                    actor=f"hosted_dms:{subject}")
        except GraphObjectAuthoringError as exc:
            if exc.status_code >= 500:
                raise _unavailable() from None
            raise _denied() from None
        request.state.hosted_manual_knowledge_binding = (body, intent)
        request.state.hosted_manual_knowledge_scope = (body.world_id, body.source_run_id)
        return body.world_id
    try:
        run = await run_in_threadpool(get_extraction_run, body.source_run_id)
        artifact = await run_in_threadpool(get_source_artifact, run.source_artifact_id)
    except (GraphRunRegistryError, SourceArtifactRegistryError) as exc:
        if exc.status_code == 404:
            raise _denied() from None
        raise _unavailable() from None
    if (
        run.source_domain != "worldbuilding" or artifact.source_domain != "worldbuilding"
        or artifact.world_id != body.world_id
        or await _owned_build_page(subject, artifact.workspace_document_id) != body.world_id
    ):
        raise _denied()
    request.state.hosted_manual_knowledge_scope = (body.world_id, body.source_run_id)
    return body.world_id


def manual_knowledge_actor(request: Request, *, world_id: str | None, run_id: str | None) -> str | None:
    if hosted_auth.deployment_environment() in hosted_auth.LOCAL_ENVIRONMENTS:
        return None
    if not world_id or not run_id or getattr(request.state, "hosted_manual_knowledge_scope", None) != (world_id, run_id):
        raise _denied()
    subject = _hosted_subject(request)
    _owned_world(subject, world_id)
    binding = getattr(request.state, "hosted_manual_knowledge_binding", None)
    if binding is not None:
        from apps.live_control_server.integrations.dungeonmind.historical_manual_recovery import authorize_original_binding
        from apps.live_control_server.services.graph_object_authoring_prepare import GraphObjectAuthoringError

        try:
            authorize_original_binding(binding[0], binding[1], actor=f"hosted_dms:{subject}")
        except GraphObjectAuthoringError as exc:
            if exc.status_code >= 500:
                raise _unavailable() from None
            raise _denied() from None
    return f"hosted_dms:{subject}"


async def _saved_extraction_source(run_id: str):
    from apps.live_control_server.services.graph_run_registry import GraphRunRegistryError, get_extraction_run
    from apps.live_control_server.services.source_artifact_registry import SourceArtifactRegistryError, get_source_artifact

    try:
        run = await run_in_threadpool(get_extraction_run, run_id)
        artifact = await run_in_threadpool(get_source_artifact, run.source_artifact_id)
    except (GraphRunRegistryError, SourceArtifactRegistryError) as exc:
        if exc.status_code == 404:
            raise _denied() from None
        raise _unavailable() from None
    return run, artifact


async def _owned_worldbuilding_extraction(subject: str, run_id: str):
    run, artifact = await _saved_extraction_source(run_id)
    if run.source_domain != "worldbuilding" or artifact.source_domain != "worldbuilding":
        raise _denied()
    world_id = await _owned_build_page(subject, artifact.workspace_document_id)
    if artifact.world_id != world_id:
        raise _denied()
    return world_id, artifact


async def resolve_hosted_exact_extraction_read(request: Request) -> str:
    from apps.live_control_server.services.graph_run_registry import (
        GraphRunRegistryError, read_recap_source_scope,
    )

    run_id = getattr(request.state, "hosted_route_run_id", None)
    if not run_id or request.query_params or await request.body():
        raise _denied()
    subject = _hosted_subject(request)
    run, artifact = await _saved_extraction_source(run_id)
    recap_binding = None
    if run.source_domain == artifact.source_domain == "worldbuilding":
        world_id = await _owned_build_page(subject, artifact.workspace_document_id)
        if world_id != artifact.world_id:
            raise _denied()
    elif run.source_domain == artifact.source_domain == "recap":
        frozen = run.lineage.get("world_campaign_ingest_context")
        if not isinstance(frozen, dict):
            raise _denied()
        try:
            scope = read_recap_source_scope(frozen, campaign_id=run.campaign_id)
        except GraphRunRegistryError:
            raise _denied() from None
        world = await run_in_threadpool(_owned_world, subject, scope.managed_world_id)
        binding = world.native_graph_binding
        if (binding is None or artifact.world_id != scope.native_world_id or artifact.campaign_id != scope.campaign_id
                or (binding.native_world_id, binding.binding_version) != (scope.native_world_id, scope.binding_version)):
            raise _denied()
        recap_binding = (scope.native_world_id, scope.binding_version)
        world_id = world.world_id
        if request.url.path.endswith("/build-context"):
            document_world = await _owned_build_page(subject, artifact.workspace_document_id)
            if document_world != world_id:
                raise _denied()
    else:
        raise _denied()
    request.state.hosted_build_page_world = world_id
    request.state.hosted_exact_extraction_run = (run_id, run, world_id, recap_binding)
    if request.url.path.endswith("/build-context"):
        request.state.hosted_extraction_build_artifact = artifact
    return world_id


def read_hosted_exact_extraction(request: Request, run_id: str) -> dict:
    from apps.live_control_server.services.native_recap_source_admission import public_run

    admitted = getattr(request.state, "hosted_exact_extraction_run", None)
    if admitted is None or admitted[0] != run_id:
        raise _denied()
    _, run, world_id, recap_binding = admitted
    result = public_run(run)
    _recheck_hosted_exact_extraction_world(request, world_id, recap_binding)
    return result


def _recheck_hosted_exact_extraction_world(request: Request, world_id: str, recap_binding) -> None:
    world = _owned_world(_hosted_subject(request), world_id)
    if recap_binding is not None:
        binding = world.native_graph_binding
        if binding is None or (binding.native_world_id, binding.binding_version) != recap_binding:
            raise _denied()


async def read_hosted_extraction_build_context(request: Request, run_id: str, build_context) -> dict:
    admitted = getattr(request.state, "hosted_exact_extraction_run", None)
    artifact = getattr(request.state, "hosted_extraction_build_artifact", None)
    if admitted is None or admitted[0] != run_id or artifact is None:
        raise _denied()
    _, run, world_id, recap_binding = admitted
    if run.source_artifact_id != artifact.source_artifact_id:
        raise _denied()
    result = build_context(run, artifact)
    document_world = await _owned_build_page(_hosted_subject(request), result["document_id"])
    if document_world != world_id:
        raise _denied()
    await run_in_threadpool(_recheck_hosted_exact_extraction_world, request, world_id, recap_binding)
    return result


def require_hosted_exact_review_package(
    request: Request, *, run_id: str, source_domain: str, source_artifact_id: str,
) -> None:
    if hosted_auth.deployment_environment() in hosted_auth.LOCAL_ENVIRONMENTS:
        return
    admitted = getattr(request.state, "hosted_exact_extraction_run", None)
    if admitted is None:
        raise _denied()
    admitted_id, run, world_id, recap_binding = admitted
    if (run_id, source_domain, source_artifact_id) != (
        admitted_id, run.source_domain, run.source_artifact_id,
    ):
        raise _denied()
    _recheck_hosted_exact_extraction_world(request, world_id, recap_binding)


async def resolve_hosted_recap_selection(request: Request) -> str:
    from apps.live_control_server.models.ingest_selection_context import IngestSelectionContextRequest

    if request.query_params:
        raise _denied()
    selection = IngestSelectionContextRequest.model_validate(await request.json())
    if not selection.expected_world_id:
        raise _denied()
    world = await run_in_threadpool(_owned_world, _hosted_subject(request), selection.expected_world_id)
    request.state.hosted_saved_recap_world = world.world_id
    return world.world_id


def recap_selection_subject(request: Request, world_id: str | None) -> str:
    if hosted_auth.deployment_environment() in hosted_auth.LOCAL_ENVIRONMENTS:
        return enforce_native_graph_gm(request).subject
    if not world_id:
        raise _denied()
    require_saved_recap_access(request, world_id)
    return f"hosted_dms:{_hosted_subject(request)}"


async def resolve_hosted_build_extraction(request: Request) -> str:
    subject = _hosted_subject(request)
    if request.method == "POST":
        document_id = (await request.json()).get("document_id")
        if not isinstance(document_id, str):
            raise _denied()
        world_id = await _owned_build_page(subject, document_id)
    else:
        run_id = getattr(request.state, "hosted_route_run_id", None)
        if not run_id:
            raise _denied()
        world_id, _ = await _owned_worldbuilding_extraction(subject, run_id)
    request.state.hosted_build_page_world = world_id
    return world_id


def hosted_world_media_owner(world_id: str) -> str:
    return f"hosted_world:{world_id}"


def require_hosted_build_page_world(request: Request, world_id: str) -> None:
    if not world_id or getattr(request.state, "hosted_build_page_world", None) != world_id:
        raise _denied()
    _owned_world(_hosted_subject(request), world_id)


async def resolve_hosted_saved_artwork(request: Request) -> str:
    from application_state import media
    from application_state.errors import ApplicationStateError, ApplicationStateNotFoundError

    subject = _hosted_subject(request)
    asset_id = getattr(request.state, "hosted_route_asset_id", None)
    if not asset_id or request.query_params:
        raise _denied()
    if request.method == "POST":
        if request.url.path.endswith("/save") and await request.json() != {}:
            raise _denied()
    elif await request.body():
        raise _denied()
    try:
        if str(UUID(asset_id)) != asset_id:
            raise _denied()
    except ValueError:
        raise _denied() from None

    for world_id in sorted(_owner_world_candidates(subject)):
        try:
            await run_in_threadpool(media.get_asset, asset_id, hosted_world_media_owner(world_id))
        except ApplicationStateNotFoundError:
            continue
        except ApplicationStateError:
            raise _unavailable() from None
        await run_in_threadpool(_owned_world, subject, world_id)
        request.state.hosted_saved_artwork = (asset_id, world_id)
        return world_id
    raise _denied()


def require_hosted_saved_artwork(request: Request, asset_id: UUID) -> str:
    binding = getattr(request.state, "hosted_saved_artwork", None)
    if binding is None or binding[0] != str(asset_id):
        raise _denied()
    world_id = binding[1]
    _owned_world(_hosted_subject(request), world_id)
    return hosted_world_media_owner(world_id)


async def resolve_hosted_plan_create(request: Request) -> str:
    from apps.live_control_server.services.workspace_document_registry import CreateWorldOwnedPlanRequestV2

    if request.query_params:
        raise _denied()
    body = CreateWorldOwnedPlanRequestV2.model_validate(await request.json())
    world = await run_in_threadpool(_owned_world, _hosted_subject(request), body.world_id)
    request.state.hosted_plan_context_world = world.world_id
    return world.world_id


async def resolve_hosted_plan_inventory_page(request: Request) -> str:
    selectors = request.query_params.multi_items()
    keys = {key for key, _ in selectors}
    world_id = request.query_params.get("world_id")
    cursor = {"before_updated_at", "before_document_id"}
    if (not world_id or len(keys) != len(selectors)
            or not keys <= {"world_id", "limit"} | cursor
            or (keys & cursor and not cursor <= keys) or await request.body()):
        raise _denied()
    world = await run_in_threadpool(_owned_world, _hosted_subject(request), world_id)
    request.state.hosted_plan_context_world = world.world_id
    return world.world_id



async def resolve_hosted_rules_lookup(request: Request) -> str:
    query = request.query_params
    world_id = query.get("world_id")
    keys = {"world_id"}
    if request.url.path.endswith("/query"):
        keys |= {"corpus", "question", "limit"}
    elif not request.url.path.endswith("/catalog"):
        keys.add("corpus")
    if not world_id or set(query) != keys or len(query.multi_items()) != len(keys) or await request.body():
        raise _denied()
    world = await run_in_threadpool(_owned_world, _hosted_subject(request), world_id)
    request.state.hosted_conversation_world = world.world_id
    return world.world_id


async def resolve_hosted_agent_readiness(request: Request) -> str:
    selectors = request.query_params
    world_id = selectors.get("world_id")
    if (
        not world_id or len(selectors.multi_items()) != 3
        or set(selectors) != {"world_id", "surface", "world_graph"}
        or selectors.get("surface") not in {"build", "plan", "play"}
        or selectors.get("world_graph") not in {"true", "false"}
        or await request.body()
    ):
        raise _denied()
    world = await run_in_threadpool(_owned_world, _hosted_subject(request), world_id)
    request.state.hosted_conversation_world = world.world_id
    return world.world_id


async def resolve_hosted_runbook_create(request: Request) -> str:
    from apps.live_control_server.services.workspace_document_registry import CreateWorldOwnedRunbookRequestV2

    if request.query_params:
        raise _denied()
    body = CreateWorldOwnedRunbookRequestV2.model_validate(await request.json())
    world = await run_in_threadpool(_owned_world, _hosted_subject(request), body.world_id)
    request.state.hosted_plan_context_world = world.world_id
    return world.world_id


async def resolve_hosted_runbook_write(request: Request) -> str:
    from apps.live_control_server.services.tiptap_markdown_write import (
        TiptapMarkdownWriteCommitRequest, TiptapMarkdownWritePrepareRequest,
    )

    world_id = request.query_params.get("world_id")
    document_id = getattr(request.state, "hosted_route_document_id", None)
    if not world_id or not document_id or request.query_params.multi_items() != [("world_id", world_id)]:
        raise _denied()
    model = TiptapMarkdownWritePrepareRequest if request.url.path.endswith("/prepare") else TiptapMarkdownWriteCommitRequest
    write = model.model_validate(await request.json())
    if write.document_id != document_id or write.world_id != world_id or write.scope_mode != "world":
        raise _denied()
    world = await run_in_threadpool(_owned_world, _hosted_subject(request), world_id)
    request.state.hosted_plan_context_world = world.world_id
    return world.world_id


async def resolve_hosted_runbook_read(request: Request) -> str:
    selectors = request.query_params.multi_items()
    world_id = request.query_params.get("world_id")
    exact_revision = "/committed-revision/" in request.url.path
    keys = {"world_id", "expected_sha256"} if exact_revision else {"world_id"}
    if not world_id or len(selectors) != len(keys) or {key for key, _ in selectors} != keys or await request.body():
        raise _denied()
    world = await run_in_threadpool(_owned_world, _hosted_subject(request), world_id)
    request.state.hosted_plan_context_world = world.world_id
    return world.world_id


async def resolve_hosted_plan_world_context(request: Request) -> str:
    selectors = request.query_params.multi_items()
    world_id = request.query_params.get("world_id")
    if not world_id or await request.body() or sorted(selectors) not in (
        [("world_id", world_id)],
        [("scope_mode", "world"), ("world_id", world_id)],
    ):
        raise _denied()
    if request.url.path.endswith(("/world-plans", "/trash", "/world-runbooks")) and selectors != [("world_id", world_id)]:
        raise _denied()
    world = await run_in_threadpool(_owned_world, _hosted_subject(request), world_id)
    request.state.hosted_plan_context_world = world.world_id
    return world.world_id


def require_hosted_plan_world_context(request: Request | None, world_id: str | None) -> None:
    if hosted_auth.deployment_environment() != hosted_auth.PRODUCTION_ENVIRONMENT:
        return
    if request is None or not world_id or getattr(request.state, "hosted_plan_context_world", None) != world_id:
        raise _denied()
    _owned_world(_hosted_subject(request), world_id)


async def resolve_hosted_build_page_inventory(request: Request) -> str:
    subject = _hosted_subject(request)
    selectors = request.query_params.getlist("world_id")
    if len(selectors) != 1 or not selectors[0] or await request.body():
        raise _denied()
    world = await run_in_threadpool(_owned_world, subject, selectors[0])
    request.state.hosted_build_page_inventory_world = world.world_id
    return world.world_id


def require_hosted_build_page_inventory(request: Request, world_id: str | None) -> None:
    if hosted_auth.deployment_environment() != hosted_auth.PRODUCTION_ENVIRONMENT:
        return
    if not world_id or getattr(request.state, "hosted_build_page_inventory_world", None) != world_id:
        raise _denied()
    _owned_world(_hosted_subject(request), world_id)


def build_pdf_publication_principal(request: Request, world_id: str) -> NativeGraphPrincipal:
    if hosted_auth.deployment_environment() in hosted_auth.LOCAL_ENVIRONMENTS:
        return enforce_native_graph_gm(request)
    require_build_pdf_access(request, world_id)
    subject = _hosted_subject(request)
    return HostedOwnerGraphPrincipal(
        subject=f"hosted_dms:{subject}", dms_subject=subject, role="gm",
        auth_method="hosted_owner", managed_world_id=world_id,
    )


async def resolve_hosted_world_lookup(request: Request) -> str:
    subject = _hosted_subject(request)
    selectors = request.query_params.multi_items()
    if len(selectors) != 1 or selectors[0][0] != "managed_world_id" or await request.body():
        raise _denied()
    world = _owned_world(subject, selectors[0][1])
    request.state.hosted_world_lookup_id = world.world_id
    return world.world_id


_source_warmup_lock = Lock()
_source_warmup_logger = logging.getLogger("uvicorn.error")


def _warm_hosted_world_sources(subject: str, world_id: str) -> None:
    from .plan_source_turn import prepare

    # The worker cache holds one revision. Avoid competing speculative reads.
    if not _source_warmup_lock.acquire(blocking=False):
        return
    started = monotonic()
    try:
        _owned_world(subject, world_id)
        principal = HostedOwnerGraphPrincipal(
            subject=f"hosted_dms:{subject}", dms_subject=subject, role="gm",
            auth_method="hosted_owner", managed_world_id=world_id,
        )
        context, _ = prepare(world_id, principal)
        _source_warmup_logger.info(
            "buddy_world_source_warmup world_id=%s status=%s elapsed_ms=%.1f",
            world_id, "ready" if context is not None else "unavailable",
            (monotonic() - started) * 1000,
        )
    except Exception:
        # Lookup has already returned. Send uses the normal preparation path.
        _source_warmup_logger.warning(
            "buddy_world_source_warmup world_id=%s status=error elapsed_ms=%.1f",
            world_id, (monotonic() - started) * 1000,
        )
    finally:
        _source_warmup_lock.release()


def read_hosted_world_lookup(
    request: Request, managed_world_id: str, background_tasks: BackgroundTasks,
) -> WorldContainerPublicRecord:
    if getattr(request.state, "hosted_world_lookup_id", None) != managed_world_id:
        raise _denied()
    subject = _hosted_subject(request)
    record = WorldContainerPublicRecord.from_record(_owned_world(subject, managed_world_id))
    background_tasks.add_task(_warm_hosted_world_sources, subject, record.world_id)
    return record


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
    return await run_in_threadpool(revalidate_hosted_owner_collection, request)


async def hosted_owner_creation(request: Request) -> dict:
    """Authorize only the exact owner-create entry point, not a World selector."""
    _hosted_subject(request)
    if (
        os.environ.get("DMB_HOSTED_OWNER_CREATION_CAPABILITY", "") != "1"
        or request.method != "POST"
        or request.url.path != WORLD_COLLECTION_PATH
        or request.query_params
    ):
        raise _denied()
    return {"owner_creation": True}


def revalidate_hosted_owner_collection(request: Request) -> dict:
    """Read current owner-filtered metadata after collection request admission."""
    subject = _hosted_subject(request)
    try:
        allowed_ids = list(_owner_world_candidates(subject))
        records = sorted(
            (stored.record for stored in catalog.list_owned_worlds(subject, allowed_ids)),
            key=lambda record: (record.name.casefold(), record.world_id),
        )
        permitted = [
            WorldContainerPublicRecord.from_record(world)
            for world in records
            if world.owner_subject == subject
        ]
    except Exception:
        raise _unavailable() from None
    available = False
    if os.environ.get("DMB_HOSTED_OWNER_CREATION_CAPABILITY", "") == "1":
        from application_state.world_catalog.hosted_creation import creation_enabled
        try:
            available = creation_enabled()
        except ApplicationStateError:
            # Do not block existing static Worlds when creation policy is down.
            available = False
    return WorldContainersListResponse(records=permitted, creation_available=available).model_dump(mode="json")


async def resolve_hosted_worldbuilding_review_context(request: Request) -> str:
    from apps.live_control_server.models.native_recap_preparation import NativeWorldbuildingContextRequest

    if request.query_params:
        raise _denied()
    subject = _hosted_subject(request)
    body = NativeWorldbuildingContextRequest.model_validate(await request.json())
    world_id, artifact = await _owned_worldbuilding_extraction(subject, body.run_id)
    if (body.managed_world_id != world_id or body.source_artifact_id != artifact.source_artifact_id
            or body.source_sha256 != artifact.content_sha256):
        raise _denied()
    request.state.hosted_native_graph_world = world_id
    return world_id


async def resolve_hosted_worldbuilding_evidence_correction(request: Request) -> str:
    from apps.live_control_server.models.extract_promote import WorldbuildingEvidenceCorrectionRequest

    run_id = getattr(request.state, "hosted_route_run_id", None)
    if not run_id or request.query_params:
        raise _denied()
    body = WorldbuildingEvidenceCorrectionRequest.model_validate(await request.json())
    if body.parent_run_id != run_id:
        raise _denied()
    world_id, artifact = await _owned_worldbuilding_extraction(_hosted_subject(request), run_id)
    if (body.world_id != world_id or body.source_artifact_id != artifact.source_artifact_id
            or body.source_sha256 != artifact.content_sha256):
        raise _denied()
    request.state.hosted_build_page_world = world_id
    return world_id


def worldbuilding_evidence_authorizer(request: Request, world_id: str) -> Callable[[], None] | None:
    if hosted_auth.deployment_environment() in hosted_auth.LOCAL_ENVIRONMENTS:
        return None

    def authorize() -> None:
        if getattr(request.state, "hosted_build_page_world", None) != world_id:
            raise _denied()
        _owned_world(_hosted_subject(request), world_id)
        plan = getattr(request.state, "hosted_worldbuilding_confirmation", None)
        if plan is not None:
            from apps.live_control_server.integrations.dungeonmind.historical_worldbuilding_recovery import (
                authenticate_original_plan, authorize_current_binding,
            )
            from apps.live_control_server.services.extract_promote import ExtractPromoteError

            try:
                if plan.publication_binding is None or plan.publication_binding.managed_world_id != world_id:
                    raise _denied()
                authenticate_original_plan(plan)
                authorize_current_binding(plan)
            except ExtractPromoteError as exc:
                if exc.status_code >= 500:
                    raise _unavailable() from None
                raise _denied() from None

    return authorize


async def resolve_hosted_threat_hydration(request: Request) -> str:
    if request.query_params:
        raise _denied()
    body = ThreatQueryHydrationRequestV1.model_validate(await request.json())
    if body.scope_mode != "world":
        raise _denied()
    world = await run_in_threadpool(_owned_world, _hosted_subject(request), body.world_id)
    request.state.hosted_native_graph_world = world.world_id
    return world.world_id


def require_threat_hydration_access(request: Request, body: ThreatQueryHydrationRequestV1) -> None:
    if hosted_auth.deployment_environment() in hosted_auth.LOCAL_ENVIRONMENTS:
        enforce_native_graph_gm(request)
        return
    if body.scope_mode != "world" or getattr(request.state, "hosted_native_graph_world", None) != body.world_id:
        raise _denied()
    hosted_auth.require_hosted_write_origin(request)
    _owned_world(_hosted_subject(request), body.world_id)


async def resolve_hosted_recap_name_review(request: Request) -> str:
    from apps.live_control_server.routes.recap_ingest import RecapIngestRequest

    if request.query_params:
        raise _denied()
    body = RecapIngestRequest.model_validate(await request.json())
    if (body.operation != "generate_recap_memory" or not body.managed_world_id
            or not (body.raw_text or "").strip()):
        raise _denied()
    world = await run_in_threadpool(_owned_world, _hosted_subject(request), body.managed_world_id)
    request.state.hosted_plan_context_world = world.world_id
    return world.world_id


async def resolve_hosted_worldbuilding_write_plan(request: Request) -> str:
    from apps.live_control_server.models.extract_promote import (
        WorldbuildingWritePlanConfirmRequest, WorldbuildingWritePlanPrepareRequest,
    )

    if request.query_params:
        raise _denied()
    subject = _hosted_subject(request)
    payload = await request.json()
    if request.url.path.endswith("/confirm"):
        plan = WorldbuildingWritePlanConfirmRequest.model_validate(payload).plan
        binding = plan.publication_binding
        if binding is None:
            raise _denied()
        from apps.live_control_server.integrations.dungeonmind.historical_worldbuilding_recovery import (
            authenticate_original_plan, authorize_current_binding,
        )
        from apps.live_control_server.services.extract_promote import ExtractPromoteError

        try:
            authenticate_original_plan(plan)
            world_id = binding.managed_world_id
            await run_in_threadpool(_owned_world, subject, world_id)
            await run_in_threadpool(authorize_current_binding, plan)
        except ExtractPromoteError as exc:
            if exc.status_code >= 500:
                raise _unavailable() from None
            raise _denied() from None
        request.state.hosted_worldbuilding_confirmation = plan
    else:
        body = WorldbuildingWritePlanPrepareRequest.model_validate(payload)
        world_id, _ = await _owned_worldbuilding_extraction(subject, body.run_id)
    request.state.hosted_build_page_world = world_id
    return world_id


async def resolve_hosted_native_publication(request: Request) -> str:
    from apps.live_control_server.models.native_recap_preparation import (
        NativeRecapConfirmRequest, NativeRecapPrepareRequest, NativeWorldbuildingPrepareRequest,
    )

    if request.query_params:
        raise _denied()
    subject = _hosted_subject(request)
    payload = await request.json()
    if request.url.path.endswith("/native-confirm"):
        review = NativeRecapConfirmRequest.model_validate(payload).envelope.review
    else:
        review = TypeAdapter(NativeRecapPrepareRequest | NativeWorldbuildingPrepareRequest).validate_python(payload)
    world = await run_in_threadpool(_owned_world, subject, review.managed_world_id)
    request.state.hosted_native_graph_world = world.world_id
    return world.world_id


async def resolve_hosted_recap_correction(request: Request) -> str:
    from apps.live_control_server.services.exact_run_candidate_projection import (
        CandidateProjectionError, build_exact_run_candidate_projection,
    )
    from apps.live_control_server.config import repo_root

    world_id = request.query_params.get("managed_world_id")
    run_id = getattr(request.state, "hosted_route_run_id", None)
    if not world_id or not run_id or request.query_params.multi_items() != [("managed_world_id", world_id)]:
        raise _denied()
    world = await run_in_threadpool(_owned_world, _hosted_subject(request), world_id)
    try:
        await run_in_threadpool(build_exact_run_candidate_projection, repo_root(), run_id, world.world_id)
    except CandidateProjectionError:
        raise _denied() from None
    request.state.hosted_saved_recap_world = world.world_id
    request.state.hosted_native_graph_world = world.world_id
    request.state.hosted_recap_correction_binding = world.native_graph_binding
    return world.world_id


def require_hosted_recap_correction(request: Request, world_id: str) -> None:
    if hosted_auth.deployment_environment() in hosted_auth.LOCAL_ENVIRONMENTS:
        enforce_native_graph_gm(request)
        return
    if getattr(request.state, "hosted_saved_recap_world", None) != world_id:
        raise _denied()
    binding = getattr(request.state, "hosted_recap_correction_binding", None)
    world = _owned_world(_hosted_subject(request), world_id)
    if binding is None or world.native_graph_binding != binding:
        raise _denied()


async def resolve_hosted_image_catalog(request: Request) -> str:
    query = request.query_params
    world_id = query.get("world_id")
    if (not world_id or set(query) - {"world_id", "cursor", "limit"}
            or len(query.multi_items()) != len(query) or await request.body()):
        raise _denied()
    world = await run_in_threadpool(_owned_world, _hosted_subject(request), world_id)
    request.state.hosted_conversation_world = world.world_id
    return world.world_id


async def resolve_hosted_media_library(request: Request) -> str:
    query = request.query_params
    world_id = query.get("world_id")
    if (not world_id or set(query) not in ({"world_id"}, {"world_id", "before_time", "before_id"})
            or len(query.multi_items()) != len(query) or await request.body()):
        raise _denied()
    world = await run_in_threadpool(_owned_world, _hosted_subject(request), world_id)
    request.state.hosted_plan_context_world = world.world_id
    return world.world_id


async def resolve_hosted_managed_projection(request: Request) -> str:
    from apps.live_control_server.services.managed_world_graph_projection import ManagedWorldGraphProjectionRequest

    if request.query_params:
        raise _denied()
    body = ManagedWorldGraphProjectionRequest.model_validate(await request.json())
    world = await run_in_threadpool(_owned_world, _hosted_subject(request), body.managed_world_id)
    request.state.hosted_native_graph_world = world.world_id
    return world.world_id


async def resolve_hosted_source_statement_proposal(request: Request) -> str:
    world_id = request.query_params.get("managed_world_id")
    if not world_id or request.query_params.multi_items() != [("managed_world_id", world_id)] or await request.body():
        raise _denied()
    world = await run_in_threadpool(_owned_world, _hosted_subject(request), world_id)
    request.state.hosted_native_graph_world = world.world_id
    return world.world_id


async def resolve_hosted_source_statement_review(request: Request) -> str:
    world_id = request.query_params.get("managed_world_id")
    if not world_id or request.query_params.multi_items() != [("managed_world_id", world_id)]:
        raise _denied()
    if request.method == "POST":
        from apps.live_control_server.models.source_statement_proposals import ProposalReview

        body = ProposalReview.model_validate(await request.json())
        if body.selection.managed_world_id != world_id:
            raise _denied()
    elif await request.body():
        raise _denied()
    world = await run_in_threadpool(_owned_world, _hosted_subject(request), world_id)
    request.state.hosted_native_graph_world = world.world_id
    return world.world_id


async def resolve_hosted_source_statement_publication(request: Request) -> str:
    from apps.live_control_server.models.source_statements import ConfirmStatement, StatementSelection

    if request.query_params:
        raise _denied()
    subject = _hosted_subject(request)
    payload = await request.json()
    if request.url.path.endswith("/confirm"):
        binding = ConfirmStatement.model_validate(payload).envelope.get("binding")
        world_id = binding.get("managed_world_id") if isinstance(binding, dict) else None
    else:
        world_id = StatementSelection.model_validate(payload).managed_world_id
    if not isinstance(world_id, str) or not world_id:
        raise _denied()
    world = await run_in_threadpool(_owned_world, subject, world_id)
    request.state.hosted_native_graph_world = world.world_id
    return world.world_id


async def resolve_hosted_source_statement_subject(request: Request) -> str:
    world_id = getattr(request.state, "hosted_route_world_id", None)
    selectors = request.query_params.multi_items()
    if (not world_id or len(selectors) != 2
            or {key for key, _ in selectors} != {"campaign_id", "revision_id"}
            or any(not value.strip() for _, value in selectors) or await request.body()):
        raise _denied()
    world = await run_in_threadpool(_owned_world, _hosted_subject(request), world_id)
    request.state.hosted_native_graph_world = world.world_id
    return world.world_id


async def resolve_hosted_source_evidence_extension(request: Request) -> str:
    from apps.live_control_server.models.source_statements import ExtendSourceEvidence

    if request.query_params:
        raise _denied()
    body = ExtendSourceEvidence.model_validate(await request.json())
    world = await run_in_threadpool(_owned_world, _hosted_subject(request), body.managed_world_id)
    request.state.hosted_native_graph_world = world.world_id
    return world.world_id


async def resolve_hosted_build_recap_recovery(request: Request) -> str:
    selectors = request.query_params.multi_items()
    if len(selectors) != 2 or {key for key, _ in selectors} != {
        "document_id", "managed_world_id",
    } or await request.body():
        raise _denied()
    world_id = await _owned_build_page(_hosted_subject(request), request.query_params.get("document_id"))
    if request.query_params.get("managed_world_id") != world_id:
        raise _denied()
    request.state.hosted_build_page_world = world_id
    return world_id


async def resolve_hosted_recap_review_context(request: Request) -> str:
    from apps.live_control_server.models.native_recap_preparation import NativeRecapContextRequest
    from apps.live_control_server.services.graph_run_registry import read_recap_source_scope

    if request.query_params:
        raise _denied()
    subject = _hosted_subject(request)
    body = NativeRecapContextRequest.model_validate(await request.json())
    # Ownership is resolved before extraction/source metadata is read.
    world = await run_in_threadpool(_owned_world, subject, body.managed_world_id)
    run, artifact = await _saved_extraction_source(body.run_id)
    if run.source_domain != "recap" or artifact.source_domain != "recap":
        raise _denied()
    scope = read_recap_source_scope(run.lineage.get("world_campaign_ingest_context"), campaign_id=run.campaign_id)
    binding = world.native_graph_binding
    if (scope.managed_world_id != world.world_id or binding is None
            or (scope.native_world_id, scope.binding_version) != (binding.native_world_id, binding.binding_version)
            or artifact.world_id != scope.native_world_id
            or run.campaign_id != artifact.campaign_id or run.campaign_id != body.campaign_id
            or run.session_id != artifact.session_id or run.session_id != body.session_id
            or run.revision != body.expected_run_revision
            or artifact.source_artifact_id != body.source_artifact_id
            or artifact.content_sha256 != body.source_sha256):
        raise _denied()
    request.state.hosted_native_graph_world = world.world_id
    return world.world_id


async def resolve_hosted_native_profile_transition(request: Request) -> str:
    """Only current owner/signed scope; no source/run/current-head eligibility."""
    from apps.live_control_server.models.native_profile_transition import (
        ProfileTransitionConfirm, ProfileTransitionPrepare,
    )

    if request.query_params:
        raise _denied()
    subject = _hosted_subject(request)
    raw = await request.json()
    if request.url.path.endswith("/prepare"):
        body = ProfileTransitionPrepare.model_validate(raw)
        world = body.managed_world_id
    else:
        body = ProfileTransitionConfirm.model_validate(raw)
        world = body.plan.managed_world_id
    _owned_world(subject, world)
    request.state.hosted_native_graph_world = world
    return world


async def resolve_hosted_native_manual(request: Request) -> str:
    """Current World owner only, before any source or immutable receipt IO."""
    from apps.live_control_server.models.native_manual_knowledge import (
        ManualConfirmRequest, ManualContextRequest, ManualPrepareRequest,
    )

    if request.query_params:
        raise _denied()
    subject = _hosted_subject(request)
    raw = await request.json()
    if request.url.path.endswith('/context'):
        body = ManualContextRequest.model_validate(raw)
        world = body.managed_world_id
    elif request.url.path.endswith('/prepare'):
        body = ManualPrepareRequest.model_validate(raw)
        world = body.source.managed_world_id
    else:
        body = ManualConfirmRequest.model_validate(raw)
        world = body.plan.review.source.managed_world_id
    _owned_world(subject, world)
    request.state.hosted_native_graph_world = world
    return world
