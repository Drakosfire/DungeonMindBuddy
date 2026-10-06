"""Local-only browser session bootstrap for the native Graph GM capability."""

from __future__ import annotations

from fastapi import APIRouter, Request, Response

from apps.live_control_server.services.agent_graph_local_session import (
    COOKIE_NAME,
    COOKIE_PATH,
    MAX_AGE,
    issue_session,
    require_session,
    revoke_session,
)

router = APIRouter(prefix="/api/live/agent/local-session", tags=["agent-local-session"])


def _no_store(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"


@router.post("")
def bootstrap(request: Request, response: Response) -> dict[str, str]:
    session_id, csrf = issue_session(request)
    response.set_cookie(
        COOKIE_NAME, session_id, max_age=MAX_AGE, path=COOKIE_PATH,
        httponly=True, samesite="strict", secure=False,
    )
    _no_store(response)
    return {"status": "active", "csrf_token": csrf}


@router.get("")
def status(request: Request, response: Response) -> dict[str, str]:
    csrf = require_session(request)
    _no_store(response)
    return {"status": "active", "csrf_token": csrf}


@router.delete("")
def revoke(request: Request, response: Response) -> dict[str, str]:
    revoke_session(request)
    response.delete_cookie(COOKIE_NAME, path=COOKIE_PATH)
    _no_store(response)
    return {"status": "revoked"}
