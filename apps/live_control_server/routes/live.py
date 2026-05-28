from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query
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
from src.live_play.projections import build_session_plan_projection
from src.live_play.resolve_roll import RollResolveError, resolve_roll_from_packet

router = APIRouter(prefix="/api/live", tags=["live"])


class LiveQueryRequest(BaseModel):
    campaign_id: str
    session: int = Field(ge=1)
    mode: Literal["live"] = "live"
    text: str = Field(min_length=1)


class ResolveRollRequest(BaseModel):
    command: str = Field(min_length=1)


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
        return process_live_query(body.text, base=base)
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
        raise HTTPException(status_code=500, detail="resolve-roll must not append events or jobs")

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
