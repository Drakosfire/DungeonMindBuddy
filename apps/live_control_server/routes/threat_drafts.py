"""ThreatDraft CRUD API."""
from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query

from apps.live_control_server.config import repo_root
from apps.live_control_server.models.threat_draft import (
    DEFAULT_LIST_LIMIT,
    MAX_LIST_LIMIT,
    CreateThreatDraftRequest,
    ThreatDraftListResponse,
    ThreatDraftV1,
    UpdateThreatDraftRequest,
)
from apps.live_control_server.services.threat_draft_store import (
    ThreatDraftStoreError,
    create_threat_draft,
    get_threat_draft,
    list_threat_drafts,
    update_threat_draft,
)

router = APIRouter(prefix="/api/live/threat-drafts", tags=["threat-drafts"])


def _draft_response(draft: ThreatDraftV1) -> dict[str, Any]:
    return draft.model_dump(mode="json", by_alias=True)


@router.post("")
def post_threat_draft(body: CreateThreatDraftRequest) -> dict[str, Any]:
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
        draft = update_threat_draft(repo_root(), draft_id, body)
    except ThreatDraftStoreError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return _draft_response(draft)
