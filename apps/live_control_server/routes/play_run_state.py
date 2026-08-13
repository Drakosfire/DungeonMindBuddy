"""Play run-state API (scene/beat progress + notes)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import ValidationError

from apps.live_control_server.services.play_run_state import (
    PlayRunStateDocument,
    load_play_run_state,
    save_play_run_state,
)

router = APIRouter(prefix="/api/live", tags=["play-run-state"])


@router.get(
    "/play-run-state/{run_id}",
    response_model=PlayRunStateDocument,
)
def get_play_run_state(run_id: str) -> dict[str, Any]:
    try:
        return load_play_run_state(run_id).model_dump(mode="json")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put(
    "/play-run-state/{run_id}",
    response_model=PlayRunStateDocument,
)
def put_play_run_state(run_id: str, body: dict[str, Any]) -> dict[str, Any]:
    try:
        payload = {**body, "run_id": run_id.strip()}
        saved = save_play_run_state(payload)
        return saved.model_dump(mode="json")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc
