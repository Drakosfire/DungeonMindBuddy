"""Bounded initial owner-only access to the hosted native graph explorer.

Authentication is DMS-owned. APP owns exact World ownership. Existing action
sharing grants are not native GM visibility roles and are deliberately not
promoted by this first hosted capability.
"""

from __future__ import annotations

from collections.abc import Callable

from dataclasses import dataclass
from uuid import UUID

from fastapi import HTTPException, Request
from pydantic import TypeAdapter
from starlette.concurrency import run_in_threadpool

from application_state.world_catalog import service as catalog

from apps.live_control_server.models.native_graph_explorer import (
    NativeGraphExplorerGraphRequest,
    NativeGraphExplorerOperationRequest,
    NativeGraphExplorerPrepareRequest,
)
from apps.live_control_server.models.native_graph_inspection import InspectionPin, InspectionRead, InspectionScope, NativeCompleteObjectRead
from apps.live_control_server.models.native_source_inspection import NativeSourceRead
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
    "/api/live/native-graph-inspection/catalog": TypeAdapter(InspectionPin | InspectionScope),
    "/api/live/native-source-inspection/catalog": TypeAdapter(InspectionScope),
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
    elif isinstance(body, (InspectionRead, NativeSourceRead)):
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
    """Authorize only the exact World recorded on the server-owned ingest run."""
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
    if request.url.path == FIRST_WORLD_PREPARE_PATH:
        payload = FirstWorldGraphPrepareRequest.model_validate(await request.json())
        run_id = payload.run_id
        claimed_world = None
    elif request.url.path == FIRST_WORLD_CONFIRM_PATH:
        confirmation = FirstWorldGraphConfirmRequest.model_validate(await request.json())
        run_id = confirmation.plan.run_id
        claimed_world = confirmation.plan.world_id
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


def require_build_pdf_access(request: Request, world_id: str) -> None:
    if hosted_auth.deployment_environment() in hosted_auth.LOCAL_ENVIRONMENTS:
        enforce_native_graph_gm(request)
        return
    if getattr(request.state, "hosted_build_pdf_world", None) != world_id:
        raise _denied()
    _owned_world(_hosted_subject(request), world_id)


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


async def resolve_hosted_play_read(request: Request) -> str:
    if await request.body():
        raise _denied()
    return await _resolve_hosted_play_world(request)


async def resolve_hosted_play_table_roll(request: Request) -> str:
    return await _resolve_hosted_play_world(request)


async def _resolve_hosted_play_world(request: Request) -> str:
    world_id = request.query_params.get("world_id")
    if not world_id or request.query_params.multi_items() != [("world_id", world_id)]:
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
    allowed = {"world_id", "limit", "offset"} if request.url.path.endswith("/threat-drafts") else {"world_id"}
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


async def resolve_hosted_saved_statblock(request: Request) -> str:
    selectors = request.query_params.multi_items()
    world_id = request.query_params.get("world_id")
    keys = {key for key, _ in selectors}
    allowed = {"world_id", "limit", "offset"} if request.url.path.endswith("/mechanics-revisions") else {"world_id"}
    if not world_id or len(keys) != len(selectors) or not keys <= allowed or await request.body():
        raise _denied()
    world = await run_in_threadpool(_owned_world, _hosted_subject(request), world_id)
    # The exact revision may include a portrait from a World-owned PDF review.
    request.state.hosted_build_pdf_world = world.world_id
    return world.world_id


async def resolve_hosted_build_native_source(request: Request) -> str:
    selectors = request.query_params.multi_items()
    if await request.body() or (selectors and (
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
    elif request.url.path.endswith("/candidate-projection"):
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


async def resolve_hosted_build_extraction(request: Request) -> str:
    from apps.live_control_server.services.graph_run_registry import GraphRunRegistryError, get_extraction_run
    from apps.live_control_server.services.source_artifact_registry import SourceArtifactRegistryError, get_source_artifact

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
        try:
            run = await run_in_threadpool(get_extraction_run, run_id)
            artifact = await run_in_threadpool(get_source_artifact, run.source_artifact_id)
        except (GraphRunRegistryError, SourceArtifactRegistryError) as exc:
            if exc.status_code == 404:
                raise _denied() from None
            raise _unavailable() from None
        if run.source_domain != "worldbuilding" or artifact.source_domain != "worldbuilding":
            raise _denied()
        world_id = await _owned_build_page(subject, artifact.workspace_document_id)
        if artifact.world_id != world_id:
            raise _denied()
    request.state.hosted_build_page_world = world_id
    return world_id


def hosted_world_media_owner(world_id: str) -> str:
    return f"hosted_world:{world_id}"


async def resolve_hosted_saved_artwork(request: Request) -> str:
    from application_state import media
    from application_state.errors import ApplicationStateError, ApplicationStateNotFoundError

    subject = _hosted_subject(request)
    asset_id = getattr(request.state, "hosted_route_asset_id", None)
    if not asset_id or request.query_params or await request.body():
        raise _denied()
    try:
        if str(UUID(asset_id)) != asset_id:
            raise _denied()
    except ValueError:
        raise _denied() from None

    for world_id, subjects in hosted_auth.hosted_world_access().items():
        if subject not in subjects:
            continue
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


async def resolve_hosted_plan_world_context(request: Request) -> str:
    selectors = request.query_params.multi_items()
    world_id = request.query_params.get("world_id")
    if not world_id or await request.body() or sorted(selectors) not in (
        [("world_id", world_id)],
        [("scope_mode", "world"), ("world_id", world_id)],
    ):
        raise _denied()
    if request.url.path.endswith("/world-plans") and selectors != [("world_id", world_id)]:
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
    world = _owned_world(subject, selectors[0])
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


def read_hosted_world_lookup(request: Request, managed_world_id: str) -> WorldContainerPublicRecord:
    if getattr(request.state, "hosted_world_lookup_id", None) != managed_world_id:
        raise _denied()
    return WorldContainerPublicRecord.from_record(
        _owned_world(_hosted_subject(request), managed_world_id)
    )


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
        allowed_ids = [world_id for world_id, subjects in access.items() if subject in subjects]
        records = sorted(
            (stored.record for stored in catalog.list_owned_worlds(subject, allowed_ids)),
            key=lambda record: (record.name.casefold(), record.world_id),
        )
        permitted = [
            WorldContainerPublicRecord.from_record(world)
            for world in records
            if world.owner_subject == subject
            and subject in access.get(world.world_id, ())
        ]
    except Exception:
        raise _unavailable() from None
    return WorldContainersListResponse(records=permitted).model_dump(mode="json")
