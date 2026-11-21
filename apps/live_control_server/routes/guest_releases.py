"""Owner-only guest-release operations; public delivery is not yet mounted."""
from __future__ import annotations

import os
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field
from starlette.concurrency import run_in_threadpool

from application_state import guest_release
from application_state.errors import ApplicationStateError
from apps.live_control_server.services.guest_release_preparation import ReleaseSelection, GuestReleasePreparationError, prepare
from apps.live_control_server.services.guest_release_validation import GuestReleaseValidationError, publish_candidate
from apps.live_control_server.services.guest_release_evidence import GuestReleaseEvidenceError
from apps.live_control_server.services.guest_release_assertions import GuestReleaseAssertionError
from apps.live_control_server.services.guest_release_sources import GuestReleaseSourceError
from apps.live_control_server.services.guest_release_media import GuestReleaseMediaError
from apps.live_control_server.services.guest_release_native_graph import GuestNativeGraphError
from apps.live_control_server.services.guest_release_selection import selection_options
from apps.live_control_server.services.guest_release_media_selection import list_media, preview_media
from apps.live_control_server.services.hosted_native_graph_access import _hosted_subject, _owned_world

router = APIRouter(prefix="/api/live/worlds/{world_id}/guest-releases", tags=["guest-releases"])


async def resolve_hosted_guest_release_world(request: Request) -> str:
    """Bind exact owner routes to an admitted World before handler dispatch."""
    world_id = getattr(request.state, "hosted_route_world_id", None)
    if not world_id or request.query_params or (request.method == "GET" and await request.body()):
        raise HTTPException(status_code=403, detail={"code": "owned_world_access_required"})
    subject = _hosted_subject(request)
    world = await run_in_threadpool(_owned_world, subject, world_id)
    return world.world_id


class PublishRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    expected_version: int = Field(ge=0, strict=True)
    operation_id: UUID


class RestoreRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=0, strict=True)


class MediaListRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    before_time: datetime | None = None
    before_id: UUID | None = None


def _owner(request: Request, world_id: str) -> str:
    if os.environ.get("DMB_GUEST_RELEASE_ENABLED") != "1":
        raise HTTPException(status_code=503, detail={"code": "guest_release_unavailable"})
    subject = _hosted_subject(request)
    _owned_world(subject, world_id)
    return subject


def _error(exc: ApplicationStateError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail={"code": "guest_release_unavailable"},
                         headers={"Cache-Control": "no-store"})


def _invalid_selection() -> HTTPException:
    return HTTPException(status_code=409, detail={"code": "guest_release_validation_failed"},
                         headers={"Cache-Control": "no-store"})


def _check_owner_generation(*, world_id: str, subject: str, generation: int) -> None:
    if guest_release.owner_generation(world_id=world_id, subject=subject) != generation:
        raise ApplicationStateError("World ownership changed", status_code=409)


@router.post("")
def prepare_release(world_id: str, body: ReleaseSelection, request: Request, response: Response):
    subject = _owner(request, world_id)
    response.headers["Cache-Control"] = "no-store"
    try:
        release_id, digest = prepare(world_id=world_id, subject=subject, selection=body)
    except ApplicationStateError as exc:
        raise _error(exc) from exc
    except (GuestReleaseAssertionError, GuestReleaseEvidenceError, GuestNativeGraphError,
            GuestReleasePreparationError, GuestReleaseSourceError, GuestReleaseMediaError) as exc:
        raise _invalid_selection() from exc
    return {"release_id": str(release_id), "digest": digest}


@router.get("/status")
def release_status(world_id: str, request: Request, response: Response):
    subject = _owner(request, world_id)
    response.headers["Cache-Control"] = "no-store"
    try:
        public_id, version = guest_release.pointer_status(world_id=world_id, subject=subject)
    except ApplicationStateError as exc:
        raise _error(exc) from exc
    return {"public_id": str(public_id) if public_id else None, "version": version}


@router.get("/selection-options")
def release_selection_options(world_id: str, request: Request, response: Response):
    subject = _owner(request, world_id)
    response.headers["Cache-Control"] = "no-store"
    try:
        generation = guest_release.owner_generation(world_id=world_id, subject=subject)
        options = selection_options(world_id=world_id)
        _check_owner_generation(world_id=world_id, subject=subject, generation=generation)
        return options
    except ApplicationStateError as exc:
        raise _error(exc) from exc
    except (GuestReleaseEvidenceError, GuestNativeGraphError, GuestReleaseAssertionError) as exc:
        raise _invalid_selection() from exc


@router.post("/selection-media/list")
def release_selection_media(world_id: str, body: MediaListRequest, request: Request, response: Response):
    subject = _owner(request, world_id)
    response.headers["Cache-Control"] = "no-store"
    if (body.before_time is None) != (body.before_id is None) or (body.before_time is not None and body.before_time.utcoffset() is None):
        raise HTTPException(status_code=422, detail={"code": "invalid_media_cursor"}, headers={"Cache-Control": "no-store"})
    try:
        generation = guest_release.owner_generation(world_id=world_id, subject=subject)
        result = list_media(world_id=world_id, before=(body.before_time, body.before_id) if body.before_time is not None else None)
        _check_owner_generation(world_id=world_id, subject=subject, generation=generation)
        return result
    except ApplicationStateError as exc:
        raise _error(exc) from exc


@router.get("/selection-media/{asset_id}")
def release_selection_media_preview(world_id: str, asset_id: UUID, request: Request):
    subject = _owner(request, world_id)
    try:
        generation = guest_release.owner_generation(world_id=world_id, subject=subject)
        mime, content = preview_media(world_id=world_id, asset_id=asset_id)
        _check_owner_generation(world_id=world_id, subject=subject, generation=generation)
    except ApplicationStateError as exc:
        raise _error(exc) from exc
    except GuestReleaseMediaError as exc:
        raise _invalid_selection() from exc
    return Response(content, media_type=mime, headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
                                                       "Content-Security-Policy": "default-src 'none'; sandbox"})


@router.get("/candidates")
def list_candidates(world_id: str, request: Request, response: Response):
    subject = _owner(request, world_id)
    response.headers["Cache-Control"] = "no-store"
    try:
        return {"candidates": guest_release.list_candidates(world_id=world_id, subject=subject)}
    except ApplicationStateError as exc:
        raise _error(exc) from exc


@router.get("/published")
def list_published(world_id: str, request: Request, response: Response):
    subject = _owner(request, world_id)
    response.headers["Cache-Control"] = "no-store"
    try:
        return {"releases": guest_release.list_published(world_id=world_id, subject=subject)}
    except ApplicationStateError as exc:
        raise _error(exc) from exc


@router.get("/candidates/{release_id}")
def review_release(world_id: str, release_id: UUID, request: Request, response: Response):
    subject = _owner(request, world_id)
    response.headers["Cache-Control"] = "no-store"
    try:
        manifest, digest = guest_release.review(world_id=world_id, subject=subject, release_id=release_id)
        source_visibility = guest_release.review_source_visibility(world_id=world_id, subject=subject, release_id=release_id)
    except ApplicationStateError as exc:
        raise _error(exc) from exc
    return {"manifest": manifest, "digest": digest, "source_visibility": source_visibility}


@router.get("/candidates/{release_id}/assets/{asset_id}")
def review_asset(world_id: str, release_id: UUID, asset_id: UUID, request: Request):
    subject = _owner(request, world_id)
    try:
        mime, content = guest_release.review_asset(world_id=world_id, subject=subject,
                                                   release_id=release_id, asset_id=asset_id)
    except ApplicationStateError as exc:
        raise _error(exc) from exc
    return Response(content, media_type=mime, headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})


@router.post("/candidates/{release_id}/publish")
def publish_release(world_id: str, release_id: UUID, body: PublishRequest, request: Request, response: Response):
    subject = _owner(request, world_id)
    response.headers["Cache-Control"] = "no-store"
    try:
        public_id, version = publish_candidate(world_id=world_id, subject=subject, release_id=release_id,
            digest=body.digest, expected_version=body.expected_version, operation_id=body.operation_id)
    except ApplicationStateError as exc:
        raise _error(exc) from exc
    except (GuestReleaseValidationError, GuestReleaseEvidenceError, GuestNativeGraphError, GuestReleaseAssertionError) as exc:
        raise _invalid_selection() from exc
    return {"public_id": str(public_id), "version": version}


@router.post("/candidates/{release_id}/revoke", status_code=204)
def revoke_release(world_id: str, release_id: UUID, request: Request):
    subject = _owner(request, world_id)
    try:
        guest_release.revoke(world_id=world_id, subject=subject, release_id=release_id)
    except ApplicationStateError as exc:
        raise _error(exc) from exc
    return Response(status_code=204, headers={"Cache-Control": "no-store"})


@router.post("/candidates/{release_id}/restore")
def restore_release(world_id: str, release_id: UUID, body: RestoreRequest, request: Request, response: Response):
    subject = _owner(request, world_id)
    response.headers["Cache-Control"] = "no-store"
    try:
        public_id, version = guest_release.restore(world_id=world_id, subject=subject, release_id=release_id,
                                                   expected_version=body.expected_version)
    except ApplicationStateError as exc:
        raise _error(exc) from exc
    return {"public_id": str(public_id), "version": version}
