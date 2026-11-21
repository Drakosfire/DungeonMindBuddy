"""Read-only delivery of already-published release-owned data."""
from __future__ import annotations

import os
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from starlette.concurrency import run_in_threadpool

from application_state import guest_release
from application_state.errors import ApplicationStateError
from apps.live_control_server.services.hosted_auth import _read_bounded_request_body

router = APIRouter(prefix="/api/live/guest-releases", tags=["guest-releases"])
_HEADERS = {"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"}


async def _enabled(request: Request) -> None:
    if (os.environ.get("DMB_GUEST_RELEASE_ENABLED") != "1"
        or os.environ.get("DMB_GUEST_RELEASE_PUBLIC_ENABLED") != "1"):
        raise HTTPException(status_code=404, detail={"code": "guest_release_unavailable"}, headers=_HEADERS)
    # The hosted boundary enforces this too; preserve it for local operation.
    try:
        if request.query_params or await _read_bounded_request_body(request, max_bytes=0):
            raise HTTPException(status_code=400)
    except HTTPException as exc:
        raise HTTPException(status_code=400, detail={"code": "invalid_guest_request"}, headers=_HEADERS) from exc


@router.get("/{public_id}")
async def manifest(public_id: UUID, request: Request):
    await _enabled(request)
    if request.url.path != f"/api/live/guest-releases/{public_id}":
        raise HTTPException(status_code=404, detail={"code": "guest_release_unavailable"}, headers=_HEADERS)
    try:
        release_id, data = await run_in_threadpool(guest_release.public_manifest, public_id)
    except ApplicationStateError as exc:
        raise HTTPException(status_code=404, detail={"code": "guest_release_unavailable"}, headers=_HEADERS) from exc
    return JSONResponse({"release_id": str(release_id), "manifest": data}, headers=_HEADERS)


@router.get("/{public_id}/releases/{release_id}/assets/{asset_id}")
async def asset(public_id: UUID, release_id: UUID, asset_id: UUID, request: Request):
    await _enabled(request)
    if request.url.path != f"/api/live/guest-releases/{public_id}/releases/{release_id}/assets/{asset_id}":
        raise HTTPException(status_code=404, detail={"code": "guest_release_unavailable"}, headers=_HEADERS)
    try:
        mime, content = await run_in_threadpool(guest_release.public_asset, public_id, release_id, asset_id)
    except ApplicationStateError as exc:
        raise HTTPException(status_code=404, detail={"code": "guest_release_unavailable"}, headers=_HEADERS) from exc
    return Response(content, media_type=mime, headers={**_HEADERS, "Content-Security-Policy": "default-src 'none'; sandbox"})
