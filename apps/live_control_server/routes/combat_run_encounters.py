"""GM-only scoped encounter commands. APP verifies complete Run ownership."""
from uuid import UUID
from fastapi import APIRouter, Depends, Query, Request
from application_state.play import session_encounters as sessions
from application_state.play.session_encounter_types import (
    RunEncounterScope, AnyMaterializeSceneEncounterRequest,
)
from application_state.combat_encounters import adoption
from application_state.combat_encounters.manual_encounters import AnySaveEncounterRequest, AnyCombatRecord
from application_state.combat_encounters.adoption_types import AdoptMechanicsRequest, AdoptionOutcome, AdoptionHistoryPage
from apps.live_control_server.routes.combat_encounters import _verified_world, _adoption_call
from apps.live_control_server.services.hosted_auth import PRODUCTION_ENVIRONMENT, deployment_environment
from apps.live_control_server.services import combat_encounters, combat_mechanics
from apps.live_control_server.services.hosted_native_graph_access import require_combat_encounter_access


def run_encounter_access(request: Request, world_id: str = Query(min_length=1, max_length=63)) -> None:
    require_combat_encounter_access(request, world_id)


router = APIRouter(prefix='/api/live/combat/run-encounters/{run_id}/scenes/{scene_id}',
    tags=['combat-run-encounters'], dependencies=[Depends(run_encounter_access)])

def call(http_request: Request, fn, *, world_id: str, write: bool = False, **kwargs):
    def authorize() -> None:
        require_combat_encounter_access(http_request, world_id)

    hosted = deployment_environment() == PRODUCTION_ENVIRONMENT
    if hosted and write:
        kwargs["authorize"] = authorize
    result = _adoption_call(lambda: fn(world_id=_verified_world(world_id), **kwargs))
    if hosted:
        authorize()
    return result


@router.get('')
def read(http_request: Request, run_id: UUID, scene_id: str, world_id: str = Query(min_length=1,max_length=63)):
    return call(http_request, sessions.read_encounter,world_id=world_id,run_id=run_id,scene_id=scene_id)

@router.get('/preview')
def preview(http_request: Request, run_id: UUID, scene_id: str, world_id: str = Query(min_length=1,max_length=63)):
    return call(http_request, sessions.preview_encounter,world_id=world_id,run_id=run_id,scene_id=scene_id)

@router.post('')
def create(http_request: Request, run_id: UUID, scene_id: str, body: AnyMaterializeSceneEncounterRequest, world_id: str = Query(min_length=1,max_length=63)):
    return call(http_request, sessions.materialize_encounter,world_id=world_id,write=True,run_id=run_id,scene_id=scene_id,request=body)

@router.post('/cancel')
def cancel(http_request: Request, run_id: UUID, scene_id: str, body: AnyMaterializeSceneEncounterRequest, world_id: str = Query(min_length=1,max_length=63)):
    return call(http_request, sessions.cancel_materialization,world_id=world_id,write=True,run_id=run_id,scene_id=scene_id,request=body)

@router.post('/inspect')
def inspect(http_request: Request, run_id: UUID, scene_id: str, body: AnyMaterializeSceneEncounterRequest, world_id: str = Query(min_length=1,max_length=63)):
    return call(http_request, sessions.inspect_materialization,world_id=world_id,run_id=run_id,scene_id=scene_id,request=body)

@router.get('/encounters/{encounter_id}',response_model=AnyCombatRecord)
def get(http_request: Request, run_id: UUID, scene_id: str, encounter_id: UUID, world_id: str = Query(min_length=1,max_length=63)):
    return call(http_request, combat_encounters.get_world_combat_encounter,world_id=world_id,encounter_id=str(encounter_id),scope=RunEncounterScope(run_id=run_id,scene_id=scene_id))

@router.put('/encounters/{encounter_id}',response_model=AnyCombatRecord)
def save(http_request: Request, run_id: UUID, scene_id: str, encounter_id: UUID, body: AnySaveEncounterRequest, world_id: str = Query(min_length=1,max_length=63)):
    return call(http_request, combat_encounters.save_world_combat_encounter, world_id=world_id,write=True,encounter_id=str(encounter_id),request=body,scope=RunEncounterScope(run_id=run_id,scene_id=scene_id))

@router.post('/encounters/{encounter_id}/mechanics-adoptions',response_model=AdoptionOutcome)
def adopt(http_request: Request, run_id: UUID, scene_id: str, encounter_id: UUID, body: AdoptMechanicsRequest, world_id: str = Query(min_length=1,max_length=63)):
    return call(http_request, combat_mechanics.adopt_saved_override, world_id=world_id,write=True,encounter_id=encounter_id,request=body,scope=RunEncounterScope(run_id=run_id,scene_id=scene_id))

@router.post('/encounters/{encounter_id}/mechanics-adoptions:cancel',response_model=AdoptionOutcome)
def cancel_adoption(http_request: Request, run_id: UUID, scene_id: str, encounter_id: UUID, body: AdoptMechanicsRequest, world_id: str = Query(min_length=1,max_length=63)):
    return call(http_request, adoption.cancel, world_id=world_id,write=True,encounter_id=encounter_id,request=body,scope=RunEncounterScope(run_id=run_id,scene_id=scene_id))

@router.get('/encounters/{encounter_id}/mechanics-adoptions/{operation_id}',response_model=AdoptionOutcome|None)
def inspect_adoption(http_request: Request, run_id: UUID, scene_id: str, encounter_id: UUID, operation_id: UUID, world_id: str = Query(min_length=1,max_length=63)):
    return call(http_request, adoption.inspect, world_id=world_id,encounter_id=encounter_id,operation_id=operation_id,scope=RunEncounterScope(run_id=run_id,scene_id=scene_id))


@router.get('/encounters/{encounter_id}/mechanics-adoptions',response_model=AdoptionHistoryPage)
def adoption_history(http_request: Request, run_id:UUID,scene_id:str,encounter_id:UUID,world_id:str=Query(min_length=1,max_length=63),before_operation_id:UUID|None=None,limit:int=Query(default=20,ge=1,le=100)):
    return call(http_request, adoption.history, world_id=world_id,encounter_id=encounter_id,before_operation_id=before_operation_id,limit=limit,scope=RunEncounterScope(run_id=run_id,scene_id=scene_id))
