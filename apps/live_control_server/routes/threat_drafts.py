"""ThreatDraft CRUD API."""
from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request, Response

from application_state.errors import ApplicationStateError, ApplicationStateIntegrityError
from apps.live_control_server.integrations.dungeonmind_statblocks.errors import StatblockIntegrationError
from apps.live_control_server.services import statblock_permanent_deletion
from apps.live_control_server.routes.statblock_storage import statblock_data_root
from apps.live_control_server.routes.native_threat_creation import router as native_creation_router
from apps.live_control_server.config import ManagedWorldDataRootError, managed_world_data_root, repo_root
from apps.live_control_server.models.threat_draft import (
    DEFAULT_LIST_LIMIT,
    MAX_LIST_LIMIT,
    CreateThreatDraftRequest,
    CreateWorldThreatDraftRequest,
    ThreatDraft,
    ThreatDraftListResponse,
    ThreatDraftV2,
    UpdateThreatDraftRequest,
)
from dungeonmind.domain.errors import PersistenceIntegrityError

from apps.live_control_server.integrations.dungeonmind import native_registry_source as native
from apps.live_control_server.services.managed_world_graph_projection import resolve_managed_world_binding
from apps.live_control_server.services.world_graph_projection import WorldGraphProjectionServiceError
from apps.live_control_server.services.threat_draft_store import (
    ThreatDraftStoreError,
    create_threat_draft,
    get_threat_draft,
    list_threat_drafts,
    update_threat_draft,
)
from apps.live_control_server.services.world_container_registry import (
    WorldContainerRegistryError,
    get_world_container,
)

router = APIRouter(prefix="/api/live/threat-drafts", tags=["threat-drafts"])


def _draft_response(draft: ThreatDraft) -> dict[str, Any]:
    return draft.model_dump(mode="json", by_alias=True)


def _admit_world_scope(world_id: str, revision_id: str | None) -> None:
    """Admit ownership, not model grounding. Legacy campaign drafts are unchanged."""
    try:
        world_root = managed_world_data_root(default=repo_root())
        get_world_container(world_id)
    except ManagedWorldDataRootError as exc:
        raise HTTPException(status_code=503, detail="Managed World storage unavailable") from exc
    except WorldContainerRegistryError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    if revision_id is None:
        return  # Explicit freestanding snapshot, validated by the request model.
    try:
        binding = resolve_managed_world_binding(world_id, root=world_root)
        # A World draft carries the exact native projection pin. Admission is
        # identity-only: never read a head, build a context, or open classic
        # WorldGraph services (which also require historical genesis state).
        try:
            snapshot = native.read_repository().get_revision(binding.native_world_id, revision_id)
        except PersistenceIntegrityError as exc:
            raise HTTPException(status_code=500, detail="Native graph revision integrity failure") from exc
        except Exception as exc:
            raise HTTPException(status_code=503, detail="Native graph authority unavailable") from exc
        if resolve_managed_world_binding(world_id, root=world_root) != binding:
            raise HTTPException(status_code=409, detail="World Graph binding changed; refresh and retry")
    except WorldGraphProjectionServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    revision = getattr(snapshot, "revision", None)
    if (revision is None or getattr(revision, "space_id", None) != binding.native_world_id
            or getattr(revision, "revision_id", None) != revision_id):
        raise HTTPException(status_code=422, detail="Graph revision does not belong to this World")


@router.post("")
def post_threat_draft(
    body: CreateThreatDraftRequest | CreateWorldThreatDraftRequest,
) -> dict[str, Any]:
    root = statblock_data_root(repo_root())
    if isinstance(body, CreateWorldThreatDraftRequest):
        _admit_world_scope(body.world_id, body.graph_context_snapshot.graph_revision_id)
    try:
        draft = create_threat_draft(root, body)
    except ThreatDraftStoreError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return _draft_response(draft)


@router.get("")
def get_threat_drafts(
    campaign_id: Annotated[str | None, Query()] = None,
    world_id: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=MAX_LIST_LIMIT)] = DEFAULT_LIST_LIMIT,
    offset: Annotated[int, Query(ge=0)] = 0,
    request: Request = None,
) -> dict[str, Any]:
    from apps.live_control_server.services.hosted_native_graph_access import require_hosted_plan_world_context

    require_hosted_plan_world_context(request, world_id)
    try:
        drafts, total = list_threat_drafts(
            statblock_data_root(repo_root()),
            campaign_id=campaign_id,
            world_id=world_id,
            limit=limit,
            offset=offset,
        )
    except ThreatDraftStoreError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return ThreatDraftListResponse(
        drafts=drafts,
        limit=limit,
        offset=offset,
        total=total,
    ).model_dump(mode="json", by_alias=True)


@router.delete("/{draft_id}/saved-statblock", status_code=204)
def delete_saved_statblock(draft_id: UUID, world_id: str, expected_version: int, request: Request):
    from apps.live_control_server.services.hosted_native_graph_access import require_build_pdf_access

    require_build_pdf_access(request, world_id)
    _admit_world_scope(world_id, None)
    try:
        statblock_permanent_deletion.delete_saved_statblock(
            statblock_data_root(repo_root()), world_id=world_id,
            draft_id=draft_id, expected_version=expected_version,
            authorize=lambda: require_build_pdf_access(request, world_id),
        )
    except ThreatDraftStoreError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except ApplicationStateIntegrityError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ApplicationStateError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except StatblockIntegrationError as exc:
        raise HTTPException(status_code=503, detail="Saved mechanics provider is unavailable. Retry deletion.") from exc
    return Response(status_code=204, headers={"Cache-Control": "no-store"})


@router.get("/{draft_id}")
def get_threat_draft_route(draft_id: str) -> dict[str, Any]:
    try:
        draft = get_threat_draft(statblock_data_root(repo_root()), draft_id)
    except ThreatDraftStoreError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return _draft_response(draft)


@router.put("/{draft_id}")
def put_threat_draft(draft_id: str, body: UpdateThreatDraftRequest) -> dict[str, Any]:
    try:
        existing = get_threat_draft(statblock_data_root(repo_root()), draft_id)
        if isinstance(existing, ThreatDraftV2):
            _admit_world_scope(existing.world_id, body.graph_context_snapshot.graph_revision_id)
        draft = update_threat_draft(statblock_data_root(repo_root()), draft_id, body)
    except ThreatDraftStoreError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return _draft_response(draft)


# Native creation uses GM authority and WK/Core independently of the old campaign
# publication ledgers. The parent retains ownership of the draft URL namespace.

router.include_router(native_creation_router)
