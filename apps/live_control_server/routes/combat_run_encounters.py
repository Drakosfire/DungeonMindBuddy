"""GM-only scoped encounter commands. APP verifies complete Run ownership."""
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from application_state.play import session_encounters as sessions
from application_state.play.session_encounter_types import (
    RunEncounterScope, MaterializeSceneEncounterRequest,
)
from application_state.combat_encounters import adoption
from application_state.combat_encounters.types import SaveCombatEncounterRequest, CombatEncounterRecord
from application_state.combat_encounters.adoption_types import AdoptMechanicsRequest, AdoptionOutcome, AdoptionHistoryPage
from apps.live_control_server.routes.combat_encounters import _verified_world, _adoption_call
from apps.live_control_server.routes.combat_scene_templates import call
from apps.live_control_server.services import combat_encounters, combat_mechanics
from apps.live_control_server.services.agent_graph_auth import native_graph_gm_dependency

router = APIRouter(prefix='/api/live/combat/run-encounters/{run_id}/scenes/{scene_id}',
    tags=['combat-run-encounters'], dependencies=[Depends(native_graph_gm_dependency)])

@router.get('')
def read(run_id: UUID, scene_id: str, world_id: str = Query(min_length=1,max_length=63)):
    return call(sessions.read_encounter,world_id=_verified_world(world_id),run_id=run_id,scene_id=scene_id)

@router.get('/preview')
def preview(run_id: UUID, scene_id: str, world_id: str = Query(min_length=1,max_length=63)):
    return call(sessions.preview_encounter,world_id=_verified_world(world_id),run_id=run_id,scene_id=scene_id)

@router.post('')
def create(run_id: UUID, scene_id: str, body: MaterializeSceneEncounterRequest, world_id: str = Query(min_length=1,max_length=63)):
    return call(sessions.materialize_encounter,world_id=_verified_world(world_id),run_id=run_id,scene_id=scene_id,request=body)

@router.post('/cancel')
def cancel(run_id: UUID, scene_id: str, body: MaterializeSceneEncounterRequest, world_id: str = Query(min_length=1,max_length=63)):
    return call(sessions.cancel_materialization,world_id=_verified_world(world_id),run_id=run_id,scene_id=scene_id,request=body)

@router.post('/inspect')
def inspect(run_id: UUID, scene_id: str, body: MaterializeSceneEncounterRequest, world_id: str = Query(min_length=1,max_length=63)):
    return call(sessions.inspect_materialization,world_id=_verified_world(world_id),run_id=run_id,scene_id=scene_id,request=body)

@router.get('/encounters/{encounter_id}',response_model=CombatEncounterRecord)
def get(run_id: UUID, scene_id: str, encounter_id: UUID, world_id: str = Query(min_length=1,max_length=63)):
    return call(combat_encounters.get_world_combat_encounter,world_id=_verified_world(world_id),encounter_id=str(encounter_id),scope=RunEncounterScope(run_id=run_id,scene_id=scene_id))

@router.put('/encounters/{encounter_id}',response_model=CombatEncounterRecord)
def save(run_id: UUID, scene_id: str, encounter_id: UUID, body: SaveCombatEncounterRequest, world_id: str = Query(min_length=1,max_length=63)):
    return _adoption_call(lambda:combat_encounters.save_world_combat_encounter(world_id=_verified_world(world_id),encounter_id=str(encounter_id),request=body,scope=RunEncounterScope(run_id=run_id,scene_id=scene_id)))

@router.post('/encounters/{encounter_id}/mechanics-adoptions',response_model=AdoptionOutcome)
def adopt(run_id: UUID, scene_id: str, encounter_id: UUID, body: AdoptMechanicsRequest, world_id: str = Query(min_length=1,max_length=63)):
    return _adoption_call(lambda:combat_mechanics.adopt_saved_override(world_id=_verified_world(world_id),encounter_id=encounter_id,request=body,scope=RunEncounterScope(run_id=run_id,scene_id=scene_id)))

@router.post('/encounters/{encounter_id}/mechanics-adoptions:cancel',response_model=AdoptionOutcome)
def cancel_adoption(run_id: UUID, scene_id: str, encounter_id: UUID, body: AdoptMechanicsRequest, world_id: str = Query(min_length=1,max_length=63)):
    return _adoption_call(lambda:adoption.cancel(world_id=_verified_world(world_id),encounter_id=encounter_id,request=body,scope=RunEncounterScope(run_id=run_id,scene_id=scene_id)))

@router.get('/encounters/{encounter_id}/mechanics-adoptions/{operation_id}',response_model=AdoptionOutcome|None)
def inspect_adoption(run_id: UUID, scene_id: str, encounter_id: UUID, operation_id: UUID, world_id: str = Query(min_length=1,max_length=63)):
    return _adoption_call(lambda:adoption.inspect(world_id=_verified_world(world_id),encounter_id=encounter_id,operation_id=operation_id,scope=RunEncounterScope(run_id=run_id,scene_id=scene_id)))


@router.get('/encounters/{encounter_id}/mechanics-adoptions',response_model=AdoptionHistoryPage)
def adoption_history(run_id:UUID,scene_id:str,encounter_id:UUID,world_id:str=Query(min_length=1,max_length=63),before_operation_id:UUID|None=None,limit:int=Query(default=20,ge=1,le=100)):
    return _adoption_call(lambda:adoption.history(world_id=_verified_world(world_id),encounter_id=encounter_id,before_operation_id=before_operation_id,limit=limit,scope=RunEncounterScope(run_id=run_id,scene_id=scene_id)))
