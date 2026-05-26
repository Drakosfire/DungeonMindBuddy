from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from apps.live_control_server.config import session_dir
from apps.live_control_server.services.live_agent_loop import process_live_query
from apps.live_control_server.session_store import events_since, load_session, refresh_current_state

router = APIRouter(prefix="/api/live", tags=["live"])


class LiveQueryRequest(BaseModel):
    campaign_id: str
    session: int = Field(ge=1)
    mode: Literal["live"] = "live"
    text: str = Field(min_length=1)


@router.post("/query")
def post_live_query(body: LiveQueryRequest) -> dict[str, Any]:
    base = session_dir()
    packet, _, _, _ = load_session(base)
    if body.campaign_id != packet["campaign_id"] or body.session != packet["session"]:
        raise HTTPException(
            status_code=400,
            detail="campaign_id/session do not match loaded live packet",
        )
    return process_live_query(body.text, base=base)


@router.get("/state")
def get_live_state() -> dict[str, Any]:
    from src.live_play.live_store import load_json

    base = session_dir()
    state_path = base / "current_state.json"
    if state_path.is_file():
        return load_json(state_path)
    return refresh_current_state(base)


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
