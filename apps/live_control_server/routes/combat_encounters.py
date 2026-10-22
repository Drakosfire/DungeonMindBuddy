"""Durable Combat encounter API, scoped to a verified managed World."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from application_state.combat_encounters.types import (
    AddGeneratedStatblockRequest,
    AddGeneratedStatblockResponse,
    CombatEncounterRecord,
    CreateCombatEncounterRequest,
    SaveCombatEncounterRequest,
)
from application_state.errors import ApplicationStateError
from apps.live_control_server.config import managed_world_data_root, repo_root
from apps.live_control_server.services import combat_encounters
from apps.live_control_server.services.managed_world_graph_projection import (
    WorldGraphProjectionServiceError,
    resolve_managed_world_binding,
)
from apps.live_control_server.services.statblock_draft_store import (
    StatblockDraftNotFoundError,
    UnsafeArtifactIdError,
)
from apps.live_control_server.services.statblock_view import StatblockViewError

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
