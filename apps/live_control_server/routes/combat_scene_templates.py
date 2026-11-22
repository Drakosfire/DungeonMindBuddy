"""Verified World/GM scene-template preparation routes."""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from application_state.combat_encounters import scene_templates as service
from application_state.combat_encounters.scene_template_types import CreateSceneTemplateRequest, PreviewNamedEncounterRequest, SceneTemplateView
from application_state.combat_encounters.manual_encounters import AnyCombatRecord
from application_state.errors import ApplicationStateError
from apps.live_control_server.routes.combat_encounters import _verified_world
from apps.live_control_server.services.agent_graph_auth import enforce_native_graph_gm

from apps.live_control_server.services.hosted_auth import PRODUCTION_ENVIRONMENT, deployment_environment
from apps.live_control_server.services.hosted_native_graph_access import require_hosted_plan_world_context


def scene_template_access(request: Request, world_id: str = Query(min_length=1, max_length=63)) -> None:
    if deployment_environment() == PRODUCTION_ENVIRONMENT:
        require_hosted_plan_world_context(request, world_id)
    else:
        enforce_native_graph_gm(request)


router=APIRouter(prefix='/api/live/combat/scene-templates',tags=['combat-scene-templates'],dependencies=[Depends(scene_template_access)])

def call(http_request: Request, fn, *, world_id: str, write: bool = False, **kwargs):
    def authorize() -> None:
        require_hosted_plan_world_context(http_request, world_id)

    hosted = deployment_environment() == PRODUCTION_ENVIRONMENT
    if hosted and write:
        kwargs["authorize"] = authorize
    world_id = _verified_world(world_id)
    try:
        result = fn(world_id=world_id, **kwargs)
    except ApplicationStateError as exc:
        raise HTTPException(status_code=exc.status_code,detail=str(exc)) from exc

    if hosted:
        authorize()
    return result

@router.post('',response_model=SceneTemplateView)
def create(http_request: Request, body:CreateSceneTemplateRequest,world_id:str=Query(min_length=1,max_length=63)):
    return call(http_request, service.create,world_id=world_id,write=True,request=body)

@router.post('/preview-saved', response_model=AnyCombatRecord)
def preview_saved(http_request: Request, body: PreviewNamedEncounterRequest, world_id: str = Query(min_length=1, max_length=63)):
    return call(http_request, service.preview_named_copy, world_id=world_id, pin=body.pin, title=body.title)

@router.post('/cancel')
def cancel(http_request: Request, body:CreateSceneTemplateRequest,world_id:str=Query(min_length=1,max_length=63)):
    return call(http_request, service.cancel,world_id=world_id,write=True,request=body)

@router.get('/operations/{operation_id}',response_model=SceneTemplateView|None)
def inspect(http_request: Request, operation_id:UUID,world_id:str=Query(min_length=1,max_length=63)):
    return call(http_request, service.inspect_operation,world_id=world_id,operation_id=operation_id)

@router.get('/{document_id}/scenes/{scene_id}',response_model=SceneTemplateView|None)
def read(http_request: Request, document_id:UUID,scene_id:str,world_id:str=Query(min_length=1,max_length=63)):
    return call(http_request, service.read,world_id=world_id,document_id=document_id,scene_id=scene_id)

@router.get('/{document_id}/scenes/{scene_id}/versions/{revision}',response_model=AnyCombatRecord)
def version(http_request: Request, document_id:UUID,scene_id:str,revision:int,world_id:str=Query(min_length=1,max_length=63)):
    if revision<1:
        raise HTTPException(status_code=422,detail='Prepared version must be positive')
    return call(http_request, service.read_version,world_id=world_id,document_id=document_id,scene_id=scene_id,revision=revision)
