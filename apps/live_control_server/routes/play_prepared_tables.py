"""Native GM admission for Play-owned prepared tables."""
from typing import Annotated
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool
from application_state.errors import ApplicationStateError
from application_state.play.prepared_table_service import TableRollCommand, inventory, record_roll, receipts
from apps.live_control_server.services.agent_graph_auth import enforce_native_graph_gm
from apps.live_control_server.services import hosted_auth
from apps.live_control_server.services.hosted_native_graph_access import require_hosted_plan_world_context

router = APIRouter(prefix="/api/live/world-play-runs/v2/{run_id}/prepared-tables", tags=["prepared-tables"])


def authorize(request: Request, world_id: str) -> None:
    if hosted_auth.deployment_environment() == hosted_auth.PRODUCTION_ENVIRONMENT:
        require_hosted_plan_world_context(request, world_id)
    else:
        enforce_native_graph_gm(request)


def invoke(action, **kwargs):
    try:
        return action(**kwargs)
    except ApplicationStateError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.get("")
def get_tables(run_id: str, request: Request, world_id: Annotated[str, Query(min_length=1)]):
    authorize(request, world_id)
    return invoke(inventory, world_id=world_id, run_id=run_id)


@router.get("/receipts")
def get_receipts(run_id: str, request: Request, world_id: Annotated[str, Query(min_length=1)],
                 before: Annotated[int | None, Query(ge=1)] = None, limit: Annotated[int, Query(ge=1, le=100)] = 20):
    enforce_native_graph_gm(request)
    return invoke(receipts, world_id=world_id, run_id=run_id, before=before, limit=limit)


@router.put("/commands/{command_id}")
async def put_roll(run_id: str, command_id: str, request: Request, world_id: Annotated[str, Query(min_length=1)]):
    authorize(request, world_id)
    try:
        body = TableRollCommand.model_validate_json(await request.body())
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors(include_context=False)) from exc
    return await run_in_threadpool(invoke, record_roll, world_id=world_id, run_id=run_id, command_id=command_id, request=body)
