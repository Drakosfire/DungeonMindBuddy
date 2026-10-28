"""Durable Combat encounter API, scoped to a verified managed World."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from application_state.combat_encounters.types import (
    AddGeneratedStatblockRequest,
    AddGeneratedStatblockResponse,
    CombatEncounterRecord,
    CombatMechanicsSelection, CombatMechanicsSnapshot,
    AcceptedCombatMechanicsSelection, AcceptedCombatMechanicsSnapshot,
    CreateCombatEncounterRequest,
    SaveCombatEncounterRequest,
)
from application_state.errors import ApplicationStateError
from apps.live_control_server.config import managed_world_data_root, repo_root
from apps.live_control_server.services import combat_encounters, combat_mechanics
from apps.live_control_server.integrations.dungeonmind_statblocks.errors import StatblockIntegrationError
from apps.live_control_server.services.managed_world_graph_projection import (
    WorldGraphProjectionServiceError,
    resolve_managed_world_binding,
)
from apps.live_control_server.services.statblock_draft_store import (
    StatblockDraftNotFoundError,
    UnsafeArtifactIdError,
)
from apps.live_control_server.services.statblock_view import StatblockViewError
from apps.live_control_server.services.threat_draft_store import ThreatDraftStoreError

from apps.live_control_server.services.agent_graph_auth import native_graph_gm_dependency

router = APIRouter(prefix="/api/live/combat/encounters", tags=["combat-encounters"],
                   dependencies=[Depends(native_graph_gm_dependency)])


def _verified_world(world_id: str) -> str:
    try:
        return resolve_managed_world_binding(
            world_id, root=managed_world_data_root(repo_root())
        ).managed_world_id
    except WorldGraphProjectionServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


def _raise_state_error(exc: ApplicationStateError) -> None:
    raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.get("", response_model=list[CombatEncounterRecord])
def list_encounters(world_id: Annotated[str, Query(min_length=1, max_length=63)]) -> list[dict]:
    owner = _verified_world(world_id)
    try:
        return [record.model_dump(mode="json") for record in combat_encounters.list_world_combat_encounters(world_id=owner)]
    except ApplicationStateError as exc:
        _raise_state_error(exc)


@router.post("", response_model=CombatEncounterRecord)
def create_encounter_route(
    world_id: Annotated[str, Query(min_length=1, max_length=63)],
    body: CreateCombatEncounterRequest,
) -> dict:
    owner = _verified_world(world_id)
    try:
        return combat_encounters.create_world_combat_encounter(
            world_id=owner, request=body
        ).model_dump(mode="json")
    except ApplicationStateError as exc:
        _raise_state_error(exc)


@router.get("/{encounter_id}", response_model=CombatEncounterRecord)
def get_encounter_route(
    encounter_id: str,
    world_id: Annotated[str, Query(min_length=1, max_length=63)],
) -> dict:
    owner = _verified_world(world_id)
    try:
        return combat_encounters.get_world_combat_encounter(
            world_id=owner, encounter_id=encounter_id
        ).model_dump(mode="json")
    except ApplicationStateError as exc:
        _raise_state_error(exc)


@router.put("/{encounter_id}", response_model=CombatEncounterRecord)
def save_encounter_route(
    encounter_id: str,
    world_id: Annotated[str, Query(min_length=1, max_length=63)],
    body: SaveCombatEncounterRequest,
) -> dict:
    owner = _verified_world(world_id)
    try:
        return combat_encounters.save_world_combat_encounter(
            world_id=owner, encounter_id=encounter_id, request=body
        ).model_dump(mode="json")
    except ThreatDraftStoreError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except StatblockIntegrationError as exc:
        raise HTTPException(status_code=503, detail="Exact accepted mechanics are unavailable") from exc
    except WorldGraphProjectionServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except ApplicationStateError as exc:
        _raise_state_error(exc)


@router.post(
    "/{encounter_id}/statblocks/{artifact_id}",
    response_model=AddGeneratedStatblockResponse,
)
def add_generated_statblock_route(
    encounter_id: str,
    artifact_id: str,
    world_id: Annotated[str, Query(min_length=1, max_length=63)],
    body: AddGeneratedStatblockRequest,
) -> dict:
    owner = _verified_world(world_id)
    try:
        return combat_encounters.add_generated_statblock_to_world_combat_encounter(
            world_id=owner,
            encounter_id=encounter_id,
            artifact_id=artifact_id,
            request=body,
        ).model_dump(mode="json")
    except ApplicationStateError as exc:
        _raise_state_error(exc)
    except UnsafeArtifactIdError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except StatblockDraftNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except StatblockViewError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=getattr(exc, "status_code", 422), detail=str(exc)) from exc


@router.post("/world-mechanics/preview", response_model=CombatMechanicsSnapshot)
def preview_mechanics(world_id: Annotated[str, Query(min_length=1, max_length=63)], body: CombatMechanicsSelection):
    owner = _verified_world(world_id)
    try:
        return combat_mechanics.preview(world_id=owner, selection=body)
    except ApplicationStateError as exc:
        _raise_state_error(exc)
    except WorldGraphProjectionServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except ThreatDraftStoreError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except StatblockIntegrationError as exc:
        raise HTTPException(status_code=503, detail="Exact accepted mechanics are unavailable") from exc


@router.post("/accepted-mechanics/preview", response_model=AcceptedCombatMechanicsSnapshot)
def preview_accepted_mechanics(world_id: Annotated[str, Query(min_length=1, max_length=63)], body: AcceptedCombatMechanicsSelection):
    owner = _verified_world(world_id)
    try:
        return combat_mechanics.preview_accepted(world_id=owner, selection=body)
    except ApplicationStateError as exc:
        _raise_state_error(exc)
    except ThreatDraftStoreError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except StatblockIntegrationError as exc:
        raise HTTPException(status_code=503, detail="Exact accepted mechanics are unavailable") from exc


from uuid import UUID
from application_state.combat_encounters import adoption
from application_state.combat_encounters.adoption_types import AdoptMechanicsRequest,AdoptionOutcome,AdoptionPreview,SavedMechanicsPreviewRequest,AdoptionHistoryPage


def _adoption_call(action):
    try:return action()
    except ApplicationStateError as exc:_raise_state_error(exc)
    except ThreatDraftStoreError as exc:raise HTTPException(status_code=exc.status_code,detail=str(exc)) from exc
    except StatblockIntegrationError as exc:raise HTTPException(status_code=503,detail='Exact saved mechanics are unavailable') from exc


@router.post('/saved-mechanics/preview',response_model=AdoptionPreview)
def preview_saved_mechanics_route(world_id:Annotated[str,Query(min_length=1,max_length=63)],body:SavedMechanicsPreviewRequest):
    owner=_verified_world(world_id)
    return _adoption_call(lambda:combat_mechanics.preview_saved_override(world_id=owner,draft_id=body.draft_id,locator=body.locator))


@router.post('/{encounter_id}/mechanics-adoptions',response_model=AdoptionOutcome)
def adopt_mechanics_route(encounter_id:UUID,world_id:Annotated[str,Query(min_length=1,max_length=63)],body:AdoptMechanicsRequest):
    owner=_verified_world(world_id)
    return _adoption_call(lambda:combat_mechanics.adopt_saved_override(world_id=owner,encounter_id=encounter_id,request=body))


@router.post('/{encounter_id}/mechanics-adoptions:cancel',response_model=AdoptionOutcome)
def cancel_mechanics_adoption_route(encounter_id:UUID,world_id:Annotated[str,Query(min_length=1,max_length=63)],body:AdoptMechanicsRequest):
    owner=_verified_world(world_id)
    return _adoption_call(lambda:adoption.cancel(world_id=owner,encounter_id=encounter_id,request=body))


@router.get('/{encounter_id}/mechanics-adoptions/{operation_id}',response_model=AdoptionOutcome|None)
def inspect_mechanics_adoption_route(encounter_id:UUID,operation_id:UUID,world_id:Annotated[str,Query(min_length=1,max_length=63)]):
    owner=_verified_world(world_id)
    return _adoption_call(lambda:adoption.inspect(world_id=owner,encounter_id=encounter_id,operation_id=operation_id))


@router.get('/{encounter_id}/mechanics-adoptions',response_model=AdoptionHistoryPage)
def mechanics_adoption_history_route(encounter_id:UUID,world_id:Annotated[str,Query(min_length=1,max_length=63)],before_operation_id:UUID|None=None,limit:int=Query(default=20,ge=1,le=100)):
    owner=_verified_world(world_id)
    return _adoption_call(lambda:adoption.history(world_id=owner,encounter_id=encounter_id,before_operation_id=before_operation_id,limit=limit))
