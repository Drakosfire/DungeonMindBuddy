from __future__ import annotations

from typing import Annotated, Any, Literal

from fastapi import APIRouter, HTTPException, Path, Query, Request
from pydantic import BaseModel, Field

from apps.live_control_server.config import repo_root, session_dir
from apps.live_control_server.schema_validation import LiveRowValidationError
from apps.live_control_server.services.live_agent_loop import process_live_query
from apps.live_control_server.session_store import (
    complete_job,
    events_since,
    load_session,
    queue_packet_rebuild_job,
    refresh_current_state,
    validate_and_save_layout,
)
from src.live_play.projections import (
    ArtifactReadResponse,
    CapabilityReadResponse,
    ProjectionCommand,
    ProjectionTarget,
    ProjectionWriteResult,
    build_capability_response,
    build_session_plan_projection,
    execute_projection_command,
    read_artifact_for_target,
)
from src.live_play.projections.artifacts import ArtifactReadError
from src.live_play.resolve_roll import RollResolveError, resolve_roll_from_packet

from apps.live_control_server.services.statblock_corpus_preview import (
    StatblockCorpusPromotionPreviewRequest,
    StatblockCorpusPromotionPreviewResponse,
    build_statblock_corpus_promotion_preview,
)
from apps.live_control_server.services.statblock_corpus_write import (
    CorpusWriterCommitError,
    PreviewTokenMismatchError,
    StatblockCorpusWriteCommitRequest,
    StatblockCorpusWriteCommitResponse,
    StatblockCorpusWritePrepareRequest,
    StatblockCorpusWritePrepareResponse,
    commit_statblock_corpus_write,
    prepare_statblock_corpus_write,
)
from apps.live_control_server.services.statblock_draft_store import (
    ListStatblockDraftsResponse,
    ReadStatblockDraftResponse,
    StatblockDraftNotFoundError,
    StoreStatblockDraftRequest,
    StoreStatblockDraftResponse,
    UnsafeArtifactIdError,
    list_statblock_drafts,
    read_statblock_draft,
    store_statblock_draft,
)
from apps.live_control_server.services.statblock_workbench import (
    StatblockWorkbenchCommandRequest,
    StatblockWorkbenchCommandResponse,
    StatblockWorkbenchSampleResponse,
    build_statblock_workbench_sample_response,
    execute_statblock_workbench_command,
)

router = APIRouter(prefix="/api/live", tags=["live"])
INSPECTABLE_TARGET_TYPE = Literal["event", "roll_table"]
FORBIDDEN_PATH_QUERY_FIELDS = frozenset(
    {"source_path", "file_path", "path", "absolute_path", "relative_path"}
)


class LiveQueryRequest(BaseModel):
    campaign_id: str
    session: int = Field(ge=1)
    mode: Literal["live"] = "live"
    text: str = Field(min_length=1)
    manifest_path: str | None = None


class ResolveRollRequest(BaseModel):
    command: str = Field(min_length=1)


def _reject_forbidden_query_fields(request: Request) -> None:
    blocked = sorted(FORBIDDEN_PATH_QUERY_FIELDS & set(request.query_params.keys()))
    if blocked:
        raise HTTPException(
            status_code=422,
            detail=f"forbidden query fields: {', '.join(blocked)}",
        )


def _target_from_session(
    *,
    target_type: INSPECTABLE_TARGET_TYPE,
    target_id: str,
    packet: dict[str, Any],
    events: list[dict[str, Any]],
) -> ProjectionTarget:
    if target_type == "event":
        for event in events:
            if event.get("id") != target_id:
                continue
            summary = str(event.get("summary") or "").strip()
            label = summary or f"Event {target_id}"
            return ProjectionTarget(
                target_type="event",
                target_id=target_id,
                label=label,
                source_status="authoritative",
            )
        raise HTTPException(
            status_code=404, detail=f"unknown target id for event: {target_id}"
        )

    for row in packet.get("known_roll_tables", []):
        if row.get("table_id") != target_id:
            continue
        title = str(row.get("title") or "").strip() or f"Roll table {target_id}"
        return ProjectionTarget(
            target_type="roll_table",
            target_id=target_id,
            label=title,
            source_status="authoritative",
        )
    raise HTTPException(
        status_code=404, detail=f"unknown target id for roll_table: {target_id}"
    )


@router.get(
    "/statblocks/workbench/sample",
    response_model=StatblockWorkbenchSampleResponse,
)
def get_statblock_workbench_sample() -> dict[str, Any]:
    try:
        response = build_statblock_workbench_sample_response()
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return response.model_dump(mode="json")


@router.post(
    "/statblocks/workbench/command",
    response_model=StatblockWorkbenchCommandResponse,
)
def post_statblock_workbench_command(
    body: StatblockWorkbenchCommandRequest,
) -> dict[str, Any]:
    response = execute_statblock_workbench_command(body)
    if response.artifact is None:
        raise HTTPException(status_code=502, detail=response.model_dump(mode="json"))
    return response.model_dump(mode="json")


@router.post(
    "/statblocks/workbench/drafts",
    response_model=StoreStatblockDraftResponse,
)
def post_statblock_workbench_draft(
    body: StoreStatblockDraftRequest,
) -> dict[str, Any]:
    base = session_dir()
    packet, _, _, _ = load_session(base)
    try:
        record = store_statblock_draft(
            base=base,
            campaign_id=str(packet["campaign_id"]),
            session=int(packet["session"]),
            artifact=body.artifact,
        )
    except UnsafeArtifactIdError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    response = StoreStatblockDraftResponse(
        record=record,
        diagnostics=[
            "stored as non-corpus draft artifact",
            "no corpus write, ingestion, or combat mutation occurred",
        ],
    )
    return response.model_dump(mode="json")


@router.get(
    "/statblocks/workbench/drafts",
    response_model=ListStatblockDraftsResponse,
)
def get_statblock_workbench_drafts() -> dict[str, Any]:
    response = ListStatblockDraftsResponse(
        drafts=list_statblock_drafts(base=session_dir())
    )
    return response.model_dump(mode="json")


@router.get(
    "/statblocks/workbench/drafts/{artifact_id}",
    response_model=ReadStatblockDraftResponse,
)
def get_statblock_workbench_draft(
    artifact_id: Annotated[str, Path(min_length=1)],
) -> dict[str, Any]:
    try:
        record = read_statblock_draft(base=session_dir(), artifact_id=artifact_id)
    except UnsafeArtifactIdError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except StatblockDraftNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    response = ReadStatblockDraftResponse(record=record)
    return response.model_dump(mode="json")


@router.post(
    "/statblocks/workbench/drafts/{artifact_id}/corpus-preview",
    response_model=StatblockCorpusPromotionPreviewResponse,
)
def post_statblock_workbench_draft_corpus_preview(
    artifact_id: Annotated[str, Path(min_length=1)],
    body: StatblockCorpusPromotionPreviewRequest | None = None,
) -> dict[str, Any]:
    base = session_dir()
    packet, _, _, _ = load_session(base)
    request = body or StatblockCorpusPromotionPreviewRequest()
    try:
        response = build_statblock_corpus_promotion_preview(
            base=base,
            packet=packet,
            artifact_id=artifact_id,
            include_writer_allowlist_check=request.include_writer_allowlist_check,
        )
    except UnsafeArtifactIdError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except StatblockDraftNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="statblock corpus preview failed") from exc
    return response.model_dump(mode="json")


@router.post(
    "/statblocks/workbench/drafts/{artifact_id}/corpus-write/prepare",
    response_model=StatblockCorpusWritePrepareResponse,
)
def post_statblock_workbench_draft_corpus_write_prepare(
    artifact_id: Annotated[str, Path(min_length=1)],
    body: StatblockCorpusWritePrepareRequest | None = None,
) -> dict[str, Any]:
    base = session_dir()
    packet, _, _, _ = load_session(base)
    request = body or StatblockCorpusWritePrepareRequest()
    try:
        response = prepare_statblock_corpus_write(
            base=base,
            packet=packet,
            artifact_id=artifact_id,
            expected_preview_token=request.preview_token,
        )
    except UnsafeArtifactIdError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except StatblockDraftNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PreviewTokenMismatchError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="statblock corpus write prepare failed") from exc
    return response.model_dump(mode="json")


@router.post(
    "/statblocks/workbench/drafts/{artifact_id}/corpus-write/commit",
    response_model=StatblockCorpusWriteCommitResponse,
)
def post_statblock_workbench_draft_corpus_write_commit(
    artifact_id: Annotated[str, Path(min_length=1)],
    body: StatblockCorpusWriteCommitRequest,
) -> dict[str, Any]:
    base = session_dir()
    packet, _, _, _ = load_session(base)
    try:
        response = commit_statblock_corpus_write(
            base=base,
            packet=packet,
            artifact_id=artifact_id,
            preview_token=body.preview_token,
            writer_confirm_token=body.writer_confirm_token,
        )
    except UnsafeArtifactIdError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except StatblockDraftNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PreviewTokenMismatchError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except CorpusWriterCommitError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="statblock corpus write commit failed") from exc
    return response.model_dump(mode="json")


@router.post("/query")
def post_live_query(body: LiveQueryRequest) -> dict[str, Any]:
    base = session_dir()
    packet, _, _, _ = load_session(base)
    if body.campaign_id != packet["campaign_id"] or body.session != packet["session"]:
        raise HTTPException(
            status_code=400,
            detail="campaign_id/session do not match loaded live packet",
        )
    try:
        return process_live_query(
            body.text, base=base, request_manifest_path=body.manifest_path
        )
    except LiveRowValidationError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/state")
def get_live_state() -> dict[str, Any]:
    return refresh_current_state(session_dir())


@router.get("/events")
def get_live_events(since: str | None = Query(default=None)) -> dict[str, Any]:
    base = session_dir()
    _, _, events, _ = load_session(base)
    return {"events": events_since(events, since)}


@router.get("/jobs")
def get_live_jobs() -> dict[str, Any]:
    base = session_dir()
    _, _, _, jobs = load_session(base)
    return {"jobs": jobs}


@router.get("/surface")
def get_live_surface() -> dict[str, Any]:
    base = session_dir()
    packet, layout, _, _ = load_session(base)
    return {
        "catalog": packet["surface_catalog"],
        "layout": layout,
        "state": refresh_current_state(base),
    }


@router.get("/plan-view")
def get_live_plan_view() -> dict[str, Any]:
    base = session_dir()
    packet, _, events, jobs = load_session(base)
    return build_session_plan_projection(packet, events, jobs)


@router.get("/artifact", response_model=ArtifactReadResponse)
def get_live_artifact(
    request: Request,
    target_type: Annotated[INSPECTABLE_TARGET_TYPE, Query()],
    target_id: Annotated[str, Query(min_length=1)],
) -> dict[str, Any]:
    _reject_forbidden_query_fields(request)
    base = session_dir()
    packet, _, events, _ = load_session(base)
    try:
        artifact = read_artifact_for_target(
            target_type=target_type,
            target_id=target_id,
            packet=packet,
            events=events,
            root=repo_root(),
        )
    except ArtifactReadError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return artifact.model_dump(mode="json")


@router.get("/capabilities", response_model=CapabilityReadResponse)
def get_live_capabilities(
    request: Request,
    target_type: Annotated[INSPECTABLE_TARGET_TYPE, Query()],
    target_id: Annotated[str, Query(min_length=1)],
) -> dict[str, Any]:
    _reject_forbidden_query_fields(request)
    base = session_dir()
    packet, _, events, _ = load_session(base)
    target = _target_from_session(
        target_type=target_type,
        target_id=target_id,
        packet=packet,
        events=events,
    )
    response = build_capability_response(target)
    return response.model_dump(mode="json")


@router.post("/commands", response_model=ProjectionWriteResult)
def post_live_command(command: ProjectionCommand) -> dict[str, Any]:
    base = session_dir()
    packet, _, events, jobs = load_session(base)
    result = execute_projection_command(
        command=command,
        base=base,
        root=repo_root(),
        packet=packet,
        events=events,
        jobs=jobs,
    )
    return result.model_dump(mode="json")


@router.put("/surface/layout")
def put_live_surface_layout(body: dict[str, Any]) -> dict[str, Any]:
    base = session_dir()
    packet, _, _, _ = load_session(base)
    try:
        saved = validate_and_save_layout(base, packet, body)
    except LiveRowValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"layout": saved}


@router.post("/jobs/{job_id}/complete")
def post_complete_job(job_id: str) -> dict[str, Any]:
    updated = complete_job(session_dir(), job_id)
    if updated is None:
        raise HTTPException(status_code=404, detail=f"job not found: {job_id}")
    return {"job": updated}


@router.post("/resolve-roll")
def post_resolve_roll(body: ResolveRollRequest) -> dict[str, Any]:
    base = session_dir()
    packet, _, events_before, jobs_before = load_session(base)
    try:
        resolved = resolve_roll_from_packet(packet, body.command, root=repo_root())
    except RollResolveError as exc:
        raise HTTPException(status_code=422, detail=exc.diagnostic.message) from exc

    _, _, events_after, jobs_after = load_session(base)
    if len(events_after) != len(events_before) or len(jobs_after) != len(jobs_before):
        raise HTTPException(
            status_code=500, detail="resolve-roll must not append events or jobs"
        )

    return {
        "table_id": resolved.table_id,
        "roll": resolved.roll,
        "title": resolved.title,
        "row_text": resolved.row_text,
        "row_locator": resolved.row_locator,
        "source_path": resolved.source_path,
        "provenance": resolved.provenance,
    }


@router.post("/rebuild-packet", status_code=202)
def post_rebuild_packet() -> dict[str, Any]:
    base = session_dir()
    packet, _, _, _ = load_session(base)
    try:
        job = queue_packet_rebuild_job(base, packet)
    except LiveRowValidationError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"job_id": job["id"], "status": job["status"], "job": job}
