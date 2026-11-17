"""Verified World/GM scene-template preparation routes."""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from application_state.combat_encounters import scene_templates as service
from application_state.combat_encounters.scene_template_types import CreateSceneTemplateRequest, SceneTemplateView
from application_state.combat_encounters.types import CombatEncounterRecord
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

def call(fn,**kwargs):
    try:
        return fn(**kwargs)
    except ApplicationStateError as exc:
        raise HTTPException(status_code=exc.status_code,detail=str(exc)) from exc

@router.post('',response_model=SceneTemplateView)
def create(body:CreateSceneTemplateRequest,world_id:str=Query(min_length=1,max_length=63)):
    return call(service.create,world_id=_verified_world(world_id),request=body)

@router.post('/cancel')
def cancel(body:CreateSceneTemplateRequest,world_id:str=Query(min_length=1,max_length=63)):
    return call(service.cancel,world_id=_verified_world(world_id),request=body)

@router.get('/operations/{operation_id}',response_model=SceneTemplateView|None)
def inspect(operation_id:UUID,world_id:str=Query(min_length=1,max_length=63)):
    return call(service.inspect_operation,world_id=_verified_world(world_id),operation_id=operation_id)

@router.get('/{document_id}/scenes/{scene_id}',response_model=SceneTemplateView|None)
def read(document_id:UUID,scene_id:str,world_id:str=Query(min_length=1,max_length=63)):
    return call(service.read,world_id=_verified_world(world_id),document_id=document_id,scene_id=scene_id)

@router.get('/{document_id}/scenes/{scene_id}/versions/{revision}',response_model=CombatEncounterRecord)
def version(document_id:UUID,scene_id:str,revision:int,world_id:str=Query(min_length=1,max_length=63)):
    if revision<1:
        raise HTTPException(status_code=422,detail='Prepared version must be positive')
    return call(service.read_version,world_id=_verified_world(world_id),document_id=document_id,scene_id=scene_id,revision=revision)
