"""HTTP API for durable Play Runtime records."""

from __future__ import annotations

import json
from uuid import UUID
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response

from apps.live_control_server.config import repo_root
from apps.live_control_server.services.play_active_run import (
    PlayActiveRunError,
    PlayActiveRunState,
    SetPlayActiveRunRequest,
    WorldPlayActiveRunState,
    get_play_active_run,
    get_world_play_active_run,
    set_play_active_run,
    set_world_play_active_run,
)
from apps.live_control_server.services.play_run_rebase import (
    PlayRunRebaseError,
    RebasePlayRunRequest,
    rebase_or_replay_play_run,
    rebase_or_replay_world_play_run,
)
from apps.live_control_server.services.play_run_registry import (
    CreatePlayRunRequest,
    PlayRunRecord,
    PlayRunRegistryError,
    PlayRunsListResponse,
    ReplacePlayRunProgressRequest,
    WorldPlayRunRecord,
    WorldPlayRunsListResponse,
    create_or_replay_play_run,
    create_or_replay_world_play_run,
    ensure_v2_native_ready,
    get_play_run,
    get_world_play_run,
    list_play_runs,
    list_world_play_runs,
    replace_play_run_progress,
    replace_world_play_run_progress,
)
from apps.live_control_server.services.play_run_reference_manifest import (
    AnyPlayRunReferenceManifest,
    PlayRunReferenceManifestError,
    get_play_run_reference_manifest,
    get_world_play_run_reference_manifest,
    seal_or_replay_play_run_reference_manifest,
    seal_or_replay_world_play_run_reference_manifest,
)

router = APIRouter(prefix="/api/live", tags=["play-runs"])


def _record_response(record: PlayRunRecord) -> dict[str, Any]:
    return record.model_dump(mode="json")


@router.get("/play-active-run", response_model=PlayActiveRunState)
def get_play_active_run_route() -> dict[str, Any]:
    try:
        state = get_play_active_run(repo_root())
    except PlayActiveRunError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return state.model_dump(mode="json")


@router.put("/play-active-run", response_model=PlayActiveRunState)
def put_play_active_run_route(body: SetPlayActiveRunRequest) -> dict[str, Any]:
    try:
        state = set_play_active_run(repo_root(), run_id=body.run_id)
    except PlayActiveRunError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return state.model_dump(mode="json")


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
    response_model=AnyPlayRunReferenceManifest,
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
    response_model=AnyPlayRunReferenceManifest,
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


@router.put("/play-runs/{run_id}/progress", response_model=PlayRunRecord)
def put_play_run_progress_route(
    run_id: str,
    body: ReplacePlayRunProgressRequest,
) -> dict[str, Any]:
    try:
        record = replace_play_run_progress(
            repo_root(),
            run_id=run_id,
            expected_run_revision=body.expected_run_revision,
            progress=body.progress,
        )
    except PlayRunRegistryError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return _record_response(record)


@router.put("/play-runs/{run_id}/rebase", response_model=PlayRunRecord)
def put_play_run_rebase(run_id: str, body: RebasePlayRunRequest) -> dict[str, Any]:
    try:
        record = rebase_or_replay_play_run(
            repo_root(),
            run_id=run_id,
            expected_run_revision=body.expected_run_revision,
            target_playable_revision=body.target_playable_revision,
            target_playable_content_sha256=body.target_playable_content_sha256,
        )
    except PlayRunRegistryError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except PlayRunRebaseError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return _record_response(record)


@router.get("/play-runs/{run_id}", response_model=PlayRunRecord)
def get_play_run_route(
    run_id: str,
    ensure_native_ready: Annotated[bool, Query()] = False,
) -> dict[str, Any]:
    try:
        if ensure_native_ready:
            record = ensure_v2_native_ready(repo_root(), run_id)
        else:
            record = get_play_run(repo_root(), run_id)
    except PlayRunRegistryError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return _record_response(record)


@router.get("/world-play-runs/v2", response_model=WorldPlayRunsListResponse)
def get_world_play_runs_v2(
    world_id: Annotated[str, Query(min_length=1)],
    playable_artifact_id: Annotated[str | None, Query()] = None,
) -> dict[str, Any]:
    try:
        records = list_world_play_runs(
            repo_root(),
            world_id=world_id,
            playable_artifact_id=playable_artifact_id,
        )
    except PlayRunRegistryError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return WorldPlayRunsListResponse(records=records).model_dump(mode="json")


@router.get(
    "/world-play-runs/v2/active", response_model=WorldPlayActiveRunState
)
def get_world_play_active_run_v2(
    world_id: Annotated[str, Query(min_length=1)],
) -> dict[str, Any]:
    try:
        state = get_world_play_active_run(repo_root(), world_id=world_id)
    except PlayActiveRunError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return state.model_dump(mode="json")


@router.put(
    "/world-play-runs/v2/active", response_model=WorldPlayActiveRunState
)
def put_world_play_active_run_v2(
    body: SetPlayActiveRunRequest,
    world_id: Annotated[str, Query(min_length=1)],
) -> dict[str, Any]:
    try:
        state = set_world_play_active_run(
            repo_root(), world_id=world_id, run_id=body.run_id
        )
    except PlayActiveRunError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return state.model_dump(mode="json")


from application_state.play.session_encounter_types import WorldSessionCreateRequest, WorldSessionSourceRequest
from application_state.play import session_encounters
from apps.live_control_server.services.agent_graph_auth import native_graph_gm_dependency
from apps.live_control_server.routes.combat_encounters import _verified_world
from apps.live_control_server.routes.combat_scene_templates import call
from apps.live_control_server.services.play_run_registry import world_session_outcome


@router.post("/world-play-runs/v2/preparation", dependencies=[Depends(native_graph_gm_dependency)])
def preview_world_session(body: WorldSessionSourceRequest, world_id: str = Query(min_length=1), entry_scene_id: str | None = None):
    return call(session_encounters.preparation_preview, world_id=_verified_world(world_id), request=body, entry_scene_id=entry_scene_id)


@router.put("/world-play-runs/v2/{run_id}", dependencies=[Depends(native_graph_gm_dependency)])
def put_world_play_run_v2(run_id: str, body: WorldSessionCreateRequest, world_id: str = Query(min_length=1)):
    try:
        return create_or_replay_world_play_run(repo_root(), world_id=_verified_world(world_id), run_id=run_id, request=body)
    except PlayRunRegistryError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.get("/world-play-runs/v2/{run_id}/creation", dependencies=[Depends(native_graph_gm_dependency)])
def inspect_world_session(run_id: UUID, world_id: str = Query(min_length=1)):
    return world_session_outcome(call(session_encounters.inspect_creation, world_id=_verified_world(world_id), run_id=run_id))


@router.post("/world-play-runs/v2/{run_id}/creation:cancel", dependencies=[Depends(native_graph_gm_dependency)])
def cancel_world_session(run_id: UUID, body: WorldSessionCreateRequest, world_id: str = Query(min_length=1)):
    return world_session_outcome(call(session_encounters.cancel_creation, world_id=_verified_world(world_id), run_id=run_id, request=body))


@router.get("/world-play-runs/v2/{run_id}", response_model=WorldPlayRunRecord)
def get_world_play_run_v2(
    run_id: str,
    world_id: Annotated[str, Query(min_length=1)],
) -> dict[str, Any]:
    try:
        record = get_world_play_run(repo_root(), world_id=world_id, run_id=run_id)
    except PlayRunRegistryError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return record.model_dump(mode="json")


@router.put(
    "/world-play-runs/v2/{run_id}/progress", response_model=WorldPlayRunRecord
)
def put_world_play_run_progress_v2(
    run_id: str,
    body: ReplacePlayRunProgressRequest,
    world_id: Annotated[str, Query(min_length=1)],
) -> dict[str, Any]:
    try:
        record = replace_world_play_run_progress(
            repo_root(),
            world_id=world_id,
            run_id=run_id,
            expected_run_revision=body.expected_run_revision,
            progress=body.progress,
        )
    except PlayRunRegistryError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return record.model_dump(mode="json")


@router.put(
    "/world-play-runs/v2/{run_id}/rebase", response_model=WorldPlayRunRecord
)
def put_world_play_run_rebase_v2(
    run_id: str,
    body: RebasePlayRunRequest,
    world_id: Annotated[str, Query(min_length=1)],
) -> dict[str, Any]:
    try:
        record = rebase_or_replay_world_play_run(
            repo_root(),
            world_id=world_id,
            run_id=run_id,
            expected_run_revision=body.expected_run_revision,
            target_playable_revision=body.target_playable_revision,
            target_playable_content_sha256=body.target_playable_content_sha256,
        )
    except PlayRunRebaseError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except PlayRunRegistryError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return record.model_dump(mode="json")


@router.get(
    "/world-play-runs/v2/{run_id}/reference-manifest",
    response_model=AnyPlayRunReferenceManifest,
    response_model_exclude_none=True,
)
def get_world_play_run_reference_manifest_v2(
    run_id: str,
    world_id: Annotated[str, Query(min_length=1)],
) -> dict[str, Any]:
    try:
        manifest = get_world_play_run_reference_manifest(
            repo_root(), world_id=world_id, run_id=run_id
        )
    except PlayRunRegistryError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except PlayRunReferenceManifestError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return manifest.model_dump(mode="json", exclude_none=True)


@router.put(
    "/world-play-runs/v2/{run_id}/reference-manifest",
    response_model=AnyPlayRunReferenceManifest,
    response_model_exclude_none=True,
)
async def put_world_play_run_reference_manifest_v2(
    run_id: str,
    request: Request,
    world_id: Annotated[str, Query(min_length=1)],
) -> dict[str, Any]:
    raw = await request.body()
    if raw.strip():
        raise HTTPException(
            status_code=422,
            detail="reference-manifest seal does not accept a request body",
        )
    try:
        manifest = seal_or_replay_world_play_run_reference_manifest(
            repo_root(), world_id=world_id, run_id=run_id
        )
    except PlayRunRegistryError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except PlayRunReferenceManifestError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return manifest.model_dump(mode="json", exclude_none=True)


# Run-local editions deliberately coexist with the original Run/manifest DTOs.
@router.get("/world-play-runs/v2/{run_id}/content")
def get_world_run_content(
    run_id: str, request: Request, world_id: Annotated[str, Query(min_length=1)]
):
    from apps.live_control_server.services.agent_graph_auth import (
        enforce_native_graph_gm,
    )
    from apps.live_control_server.services.play_run_edition import (
        edition_response,
        read_content,
    )

    enforce_native_graph_gm(request)
    return edition_response(read_content, run_id=run_id, world_id=world_id)


@router.get("/world-play-runs/v2/{run_id}/content/revisions/{revision_n}")
def get_world_run_content_revision(
    run_id: str,
    revision_n: int,
    request: Request,
    world_id: Annotated[str, Query(min_length=1)],
):
    from apps.live_control_server.services.agent_graph_auth import (
        enforce_native_graph_gm,
    )
    from apps.live_control_server.services.play_run_edition import (
        edition_response,
        read_content,
    )

    enforce_native_graph_gm(request)
    return edition_response(
        read_content, run_id=run_id, world_id=world_id, revision_n=revision_n
    )


@router.get("/world-play-runs/v2/{run_id}/content/commands/{command_id}")
def get_world_run_content_command(
    run_id: str,
    command_id: str,
    request: Request,
    world_id: Annotated[str, Query(min_length=1)],
):
    from apps.live_control_server.services.agent_graph_auth import (
        enforce_native_graph_gm,
    )
    from apps.live_control_server.services.play_run_edition import (
        edition_response,
        read_command,
    )

    enforce_native_graph_gm(request)
    return edition_response(
        read_command, run_id=run_id, world_id=world_id, command_id=command_id
    )


@router.put("/world-play-runs/v2/{run_id}/content/commands/{command_id}")
async def put_world_run_content_command(
    run_id: str,
    command_id: str,
    request: Request,
    world_id: Annotated[str, Query(min_length=1)],
):
    from apps.live_control_server.services.agent_graph_auth import (
        enforce_native_graph_gm,
    )
    from apps.live_control_server.services.play_run_edition import (
        edition_response,
        parse_commit,
        commit_content,
    )

    enforce_native_graph_gm(request)
    # Bound the streamed request before allocating an unbounded body buffer.
    raw = bytearray()
    async for chunk in request.stream():
        if len(raw) + len(chunk) > 1048576:
            raise HTTPException(
                status_code=413, detail="Run content command exceeds 1 MiB UTF8"
            )
        raw.extend(chunk)
    body = parse_commit(bytes(raw))
    return edition_response(
        commit_content,
        run_id=run_id,
        world_id=world_id,
        command_id=command_id,
        request=body,
    )


@router.get("/world-play-runs/v2/{run_id}/content/proposals")
def list_world_run_scene_proposals(run_id: str, request: Request, world_id: Annotated[str, Query(min_length=1)]):
    from apps.live_control_server.services.agent_graph_auth import enforce_native_graph_gm
    enforce_native_graph_gm(request)
    from application_state.play_scene_edit.service import PlaySceneEditProposalService
    from apps.live_control_server.services.play_scene_edit_proposal import public_record
    from application_state.errors import ApplicationStateError
    try:
        from uuid import UUID
        return {"proposals": [public_record(record) for record in PlaySceneEditProposalService().list_records(world_id=world_id, run_id=UUID(run_id))]}
    except ApplicationStateError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Invalid proposal or Run identity") from exc


@router.get("/world-play-runs/v2/{run_id}/content/proposals/{proposal_id}")
def get_world_run_scene_proposal(run_id: str, proposal_id: str, request: Request, world_id: Annotated[str, Query(min_length=1)]):
    from apps.live_control_server.services.agent_graph_auth import enforce_native_graph_gm
    enforce_native_graph_gm(request)
    from application_state.play_scene_edit.service import PlaySceneEditProposalService
    from apps.live_control_server.services.play_scene_edit_proposal import public_record
    from application_state.errors import ApplicationStateError
    try:
        from uuid import UUID
        return public_record(PlaySceneEditProposalService().get(world_id=world_id, run_id=UUID(run_id), proposal_id=UUID(proposal_id)))
    except ApplicationStateError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Invalid proposal or Run identity") from exc


@router.post("/world-play-runs/v2/{run_id}/content/proposals/{proposal_id}")
async def post_world_run_scene_proposal(run_id: str, proposal_id: str, request: Request, world_id: Annotated[str, Query(min_length=1)]):
    from apps.live_control_server.services.agent_graph_auth import enforce_native_graph_gm
    enforce_native_graph_gm(request)
    from uuid import UUID
    from pydantic import ValidationError
    from application_state.errors import ApplicationStateError
    from apps.live_control_server.config import managed_world_data_root
    from apps.live_control_server.models.play_scene_edit_proposal import PlaySceneEditProposalRequest
    from apps.live_control_server.services.play_scene_edit_proposal import propose_scene_edit
    raw = bytearray()
    async for chunk in request.stream():
        if len(raw) + len(chunk) > 65536:
            raise HTTPException(status_code=413, detail="Scene edit request exceeds 64 KiB UTF8")
        raw.extend(chunk)
    try:
        body = PlaySceneEditProposalRequest.model_validate_json(bytes(raw))
        return await propose_scene_edit(root=managed_world_data_root(), world_id=world_id, run_id=str(UUID(run_id)),
                                        proposal_id=UUID(proposal_id), request=body)
    except ApplicationStateError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors(include_context=False)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/world-play-runs/v2/{run_id}/review")
def get_world_session_review(run_id: str, request: Request, world_id: Annotated[str, Query(min_length=1)]):
    from apps.live_control_server.services.agent_graph_auth import enforce_native_graph_gm
    from application_state.play.session_review import read_review
    from application_state.errors import ApplicationStateError
    enforce_native_graph_gm(request)
    try:
        return read_review(run_id=run_id, world_id=world_id)
    except ApplicationStateError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.put("/world-play-runs/v2/{run_id}/review/commands/{command_id}")
async def put_world_session_review(run_id: str, command_id: str, request: Request, world_id: Annotated[str, Query(min_length=1)]):
    from apps.live_control_server.services.agent_graph_auth import enforce_native_graph_gm
    from application_state.play.session_review import ReviewCommand, commit_review
    from application_state.errors import ApplicationStateError
    from pydantic import ValidationError
    enforce_native_graph_gm(request)
    raw = bytearray()
    async for chunk in request.stream():
        if len(raw) + len(chunk) > 1100000:
            raise HTTPException(status_code=413, detail="Review command too large")
        raw.extend(chunk)
    try:
        body = ReviewCommand.model_validate_json(bytes(raw))
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors(include_context=False)) from exc
    try:
        return commit_review(run_id=run_id, world_id=world_id, command_id=command_id, request=body)
    except ApplicationStateError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.get("/world-session-evidence")
def list_session_evidence_route(
    request: Request,
    world_id: Annotated[str, Query(min_length=1, max_length=128)],
    limit: Annotated[int, Query(ge=1, le=20)] = 20,
):
    from apps.live_control_server.services.agent_graph_auth import enforce_native_graph_gm
    from application_state.play.session_evidence import (
        MAX_SESSION_EVIDENCE_INDEX_BYTES,
        recent_session_evidence_index,
    )
    from application_state.errors import ApplicationStateError

    enforce_native_graph_gm(request)
    try:
        result = recent_session_evidence_index(world_id=world_id, limit=limit)
        payload = json.dumps(result, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        if len(payload) > MAX_SESSION_EVIDENCE_INDEX_BYTES:
            raise HTTPException(status_code=422, detail={"code": "session_evidence_index_too_large"})
        return Response(
            content=payload,
            media_type="application/json",
            headers={"Cache-Control": "no-store", "Pragma": "no-cache"},
        )
    except ApplicationStateError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.get("/world-session-evidence/{run_id}/revisions/{revision}")
def read_session_evidence_route(run_id:str,revision:int,request:Request,world_id:Annotated[str,Query(min_length=1)]):
    from apps.live_control_server.services.agent_graph_auth import enforce_native_graph_gm
    from application_state.play.session_evidence import read_session_evidence
    from application_state.errors import ApplicationStateError
    enforce_native_graph_gm(request)
    try:return read_session_evidence(world_id=world_id,run_id=run_id,revision=revision)
    except ApplicationStateError as exc:raise HTTPException(status_code=exc.status_code,detail=str(exc)) from exc
