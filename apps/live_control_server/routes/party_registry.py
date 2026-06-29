"""Party Registry read/write API for /plan toolbox."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query

from apps.live_control_server.services.party_registry_surface import (
    PartyRegistrySurfaceResponse,
    build_party_registry_surface,
)
from apps.live_control_server.services.party_registry_write import (
    PartyRegistrySessionRosterWriteCommitRequest,
    PartyRegistrySessionRosterWriteCommitResponse,
    PartyRegistrySessionRosterWritePrepareRequest,
    PartyRegistrySessionRosterWritePrepareResponse,
    PartyRegistryWriteConflictError,
    PartyRegistryWriteError,
    commit_party_registry_session_roster_write,
    prepare_party_registry_session_roster_write,
)

router = APIRouter(prefix="/api/live/party-registry", tags=["party-registry"])


@router.get("", response_model=PartyRegistrySurfaceResponse)
def get_party_registry(
    campaign_id: Annotated[str, Query()],
    session: Annotated[int, Query(ge=1)],
) -> dict[str, Any]:
    try:
        payload = build_party_registry_surface(campaign_id=campaign_id, session=session)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return payload.model_dump(mode="json")


@router.post(
    "/session-roster/prepare",
    response_model=PartyRegistrySessionRosterWritePrepareResponse,
)
def post_party_registry_session_roster_prepare(
    body: PartyRegistrySessionRosterWritePrepareRequest,
) -> dict[str, Any]:
    try:
        response = prepare_party_registry_session_roster_write(body)
    except PartyRegistryWriteError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return response.model_dump(mode="json")


@router.post(
    "/session-roster/commit",
    response_model=PartyRegistrySessionRosterWriteCommitResponse,
)
def post_party_registry_session_roster_commit(
    body: PartyRegistrySessionRosterWriteCommitRequest,
) -> dict[str, Any]:
    try:
        response = commit_party_registry_session_roster_write(body)
    except PartyRegistryWriteConflictError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except PartyRegistryWriteError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return response.model_dump(mode="json")
