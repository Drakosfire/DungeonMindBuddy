"""ThreatDraft CRUD API."""
from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query

from apps.live_control_server.config import repo_root
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
from apps.live_control_server.ports.world_graph_authority import WorldGraphAuthorityError
from apps.live_control_server.ports.world_graph_authority_access import get_world_graph_authority
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
        get_world_container(repo_root(), world_id)
    except WorldContainerRegistryError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    if revision_id is None:
        return  # Explicit freestanding snapshot, validated by the request model.
    try:
        revision = get_world_graph_authority().read_revision(world_id, revision_id)
    except WorldGraphAuthorityError as exc:
        status = 503 if exc.code == "authority_unavailable" else 422
        raise HTTPException(status_code=status, detail=str(exc)) from exc
    except RuntimeError as exc:
        # The mounted-port factory can fail before an adapter exists.
        raise HTTPException(status_code=503, detail="World graph authority unavailable") from exc
    if revision.world_id != world_id or revision.revision_id != revision_id:
        raise HTTPException(status_code=422, detail="Graph revision does not belong to this World")


@router.post("")
def post_threat_draft(
    body: CreateThreatDraftRequest | CreateWorldThreatDraftRequest,
) -> dict[str, Any]:
    if isinstance(body, CreateWorldThreatDraftRequest):
        _admit_world_scope(body.world_id, body.graph_context_snapshot.graph_revision_id)
    try:
        draft = create_threat_draft(repo_root(), body)
    except ThreatDraftStoreError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return _draft_response(draft)


@router.get("")
def get_threat_drafts(
    campaign_id: Annotated[str | None, Query()] = None,
    world_id: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=MAX_LIST_LIMIT)] = DEFAULT_LIST_LIMIT,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, Any]:
    try:
        drafts, total = list_threat_drafts(
            repo_root(),
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


@router.get("/{draft_id}")
def get_threat_draft_route(draft_id: str) -> dict[str, Any]:
    try:
        draft = get_threat_draft(repo_root(), draft_id)
    except ThreatDraftStoreError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return _draft_response(draft)


@router.put("/{draft_id}")
def put_threat_draft(draft_id: str, body: UpdateThreatDraftRequest) -> dict[str, Any]:
    try:
        existing = get_threat_draft(repo_root(), draft_id)
        if isinstance(existing, ThreatDraftV2):
            _admit_world_scope(existing.world_id, body.graph_context_snapshot.graph_revision_id)
        draft = update_threat_draft(repo_root(), draft_id, body)
    except ThreatDraftStoreError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return _draft_response(draft)
