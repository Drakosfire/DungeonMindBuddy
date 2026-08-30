"""Retired Eldyrwild bootstrap routes (CUTOVER D.3A).

Routes remain registered and return import-free 410 responses. Reviewed
first-world initialization is a separate mounted product surface.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter(
    prefix="/api/live/world-graph-bootstrap",
    tags=["world-graph-bootstrap"],
)

_RETIRED = {
    "code": "world_graph_bootstrap_retired",
    "message": (
        "Legacy world-graph-bootstrap status/prepare/confirm is retired. "
        "Use reviewed first-world initialization on DungeonMind authority."
    ),
}


def _retired() -> JSONResponse:
    return JSONResponse(status_code=410, content={"detail": _RETIRED})


@router.get("/status")
def get_bootstrap_status(request: Request) -> JSONResponse:
    _ = request
    return _retired()


@router.post("/prepare")
def post_bootstrap_prepare(body: dict[str, Any] | None = None) -> JSONResponse:
    _ = body
    return _retired()


@router.post("/confirm")
def post_bootstrap_confirm(body: dict[str, Any] | None = None) -> JSONResponse:
    _ = body
    return _retired()
