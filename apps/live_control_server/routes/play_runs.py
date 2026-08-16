"""HTTP API for durable Play Runtime records."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query, Request

from apps.live_control_server.config import repo_root
from apps.live_control_server.services.play_run_registry import (
    CreatePlayRunRequest,
    PlayRunRecord,
    PlayRunRegistryError,
    PlayRunsListResponse,
    create_or_replay_play_run,
    get_play_run,
    list_play_runs,
)
from apps.live_control_server.services.play_run_reference_manifest import (
    PlayRunReferenceManifest,
    PlayRunReferenceManifestError,
    get_play_run_reference_manifest,
    seal_or_replay_play_run_reference_manifest,
)

router = APIRouter(prefix="/api/live", tags=["play-runs"])


def _record_response(record: PlayRunRecord) -> dict[str, Any]:
    return record.model_dump(mode="json")


@router.get("/play-runs", response_model=PlayRunsListResponse)
def get_play_runs(
    campaign_id: Annotated[str | None, Query()] = None,
    playable_artifact_id: Annotated[str | None, Query()] = None,
) -> dict[str, Any]:
    try:
        records = list_play_runs(
            repo_root(),
            campaign_id=campaign_id,
            playable_artifact_id=playable_artifact_id,
        )
    except PlayRunRegistryError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return PlayRunsListResponse(records=records).model_dump(mode="json")


@router.put("/play-runs/{run_id}", response_model=PlayRunRecord)
def put_play_run(run_id: str, body: CreatePlayRunRequest) -> dict[str, Any]:
    try:
        record = create_or_replay_play_run(
            repo_root(),
            run_id=run_id,
            playable_artifact_id=body.playable_artifact_id,
            expected_playable_revision=body.expected_playable_revision,
            expected_playable_content_sha256=body.expected_playable_content_sha256,
        )
    except PlayRunRegistryError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return _record_response(record)


@router.put(
    "/play-runs/{run_id}/reference-manifest",
    response_model=PlayRunReferenceManifest,
    response_model_exclude_none=True,
)
async def put_play_run_reference_manifest(run_id: str, request: Request) -> dict[str, Any]:
    raw = await request.body()
    if raw.strip():
        raise HTTPException(
            status_code=422,
            detail="reference-manifest seal does not accept a request body",
        )
    try:
        manifest = seal_or_replay_play_run_reference_manifest(repo_root(), run_id)
    except PlayRunRegistryError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except PlayRunReferenceManifestError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return manifest.model_dump(mode="json", exclude_none=True)


@router.get(
    "/play-runs/{run_id}/reference-manifest",
    response_model=PlayRunReferenceManifest,
    response_model_exclude_none=True,
)
def get_play_run_reference_manifest_route(run_id: str) -> dict[str, Any]:
    try:
        manifest = get_play_run_reference_manifest(repo_root(), run_id)
    except PlayRunRegistryError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except PlayRunReferenceManifestError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return manifest.model_dump(mode="json", exclude_none=True)


@router.get("/play-runs/{run_id}", response_model=PlayRunRecord)
def get_play_run_route(run_id: str) -> dict[str, Any]:
    try:
        record = get_play_run(repo_root(), run_id)
    except PlayRunRegistryError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return _record_response(record)
