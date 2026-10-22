"""Native GM admission for Play-owned prepared tables."""
from typing import Annotated
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool
from application_state.errors import ApplicationStateError
from application_state.play.prepared_table_service import TableRollCommand, inventory, record_roll, receipts
from apps.live_control_server.services.agent_graph_auth import enforce_native_graph_gm

router = APIRouter(prefix="/api/live/world-play-runs/v2/{run_id}/prepared-tables", tags=["prepared-tables"])


def invoke(http_request, action, **kwargs):
    enforce_native_graph_gm(http_request)
    try:
        return action(**kwargs)
    except ApplicationStateError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.get("")
def get_tables(run_id: str, request: Request, world_id: Annotated[str, Query(min_length=1)]):
    return invoke(request, inventory, world_id=world_id, run_id=run_id)


@router.get("/receipts")
def get_receipts(run_id: str, request: Request, world_id: Annotated[str, Query(min_length=1)],
                 before: Annotated[int | None, Query(ge=1)] = None, limit: Annotated[int, Query(ge=1, le=100)] = 20):
    return invoke(request, receipts, world_id=world_id, run_id=run_id, before=before, limit=limit)


@router.put("/commands/{command_id}")
async def put_roll(run_id: str, command_id: str, request: Request, world_id: Annotated[str, Query(min_length=1)]):
    enforce_native_graph_gm(request)
    try:
        body = TableRollCommand.model_validate_json(await request.body())
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors(include_context=False)) from exc
    return await run_in_threadpool(invoke, request, record_roll, world_id=world_id, run_id=run_id, command_id=command_id, request=body)
