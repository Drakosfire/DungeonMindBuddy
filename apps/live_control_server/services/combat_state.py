from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from apps.live_control_server.services.statblock_draft_store import read_statblock_draft
from apps.live_control_server.services.statblock_view import (
    StatblockViewError,
    read_generated_statblock,
)
from src.live_play.live_store import load_json, write_json

COMBAT_REL_PATH = Path("combat") / "current_combat.json"
CombatTeam = Literal["pc", "ally", "enemy", "neutral"]
CombatSource = Literal["corpus", "generated_pending", "manual", "imported"]


class CombatEntity(BaseModel):
    id: str
    name: str
    team: CombatTeam = "enemy"
    order: int
    init: int | None = None
    ac: int | str | None = None
    hp: int | str | None = None
    max_hp: int | str | None = None
    temp_hp: int | None = None
    defeated: bool = False
    notes: str = ""
    conditions: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    statblock_path: str | None = None
    statblock_artifact_id: str | None = None
    statblock_title: str | None = None
    corpus_fingerprint: str | None = None
    source: CombatSource = "corpus"
    provenance: list[dict[str, Any]] = Field(default_factory=list)


class CombatEncounterState(BaseModel):
    schema: Literal["dmb_combat_encounter_state_v1"] = "dmb_combat_encounter_state_v1"
    campaign_id: str
    session: int
    encounter_id: str = "current-combat"
    title: str = "Current Combat"
    round: int = 1
    active_turn_entity_id: str | None = None
    round_start_entity_id: str | None = None
    queue_model: Literal["circular_barrel_v1"] = "circular_barrel_v1"
    entities: list[CombatEntity] = Field(default_factory=list)
    groups: list[dict[str, Any]] = Field(default_factory=list)
    provenance: list[dict[str, Any]] = Field(default_factory=list)
    updated_at: str


class CombatEntityPatchRequest(BaseModel):
    name: str | None = None
    team: CombatTeam | None = None
    init: int | None = None
    ac: int | str | None = None
    hp: int | str | None = None
    max_hp: int | str | None = None
    temp_hp: int | None = Field(default=None, ge=0)
    defeated: bool | None = None
    notes: str | None = None
    conditions: list[str] | None = None


class CombatHpDeltaRequest(BaseModel):
    action: Literal["damage", "heal", "set_temp_hp"]
    amount: int = Field(gt=0, le=999)


class CombatTurnRequest(BaseModel):
    direction: Literal["next", "previous"] = "next"


class CombatSetActiveRequest(BaseModel):
    entity_id: str | None = None


class CombatMutationResponse(BaseModel):
    schema_version: Literal["dmb_combat_mutation_v1"] = "dmb_combat_mutation_v1"
    encounter: CombatEncounterState
    diagnostics: list[str] = Field(default_factory=list)


class AddGeneratedStatblockCombatRequest(BaseModel):
    team: CombatTeam = "enemy"
    count: int = Field(default=1, ge=1, le=20)
    name_override: str | None = None
    initiative: int | None = None
    insert_after_entity_id: str | None = None
    group_key: str | None = None
    notes: str | None = None
    hp_override: int | None = Field(default=None, ge=0)
    max_hp_override: int | None = Field(default=None, ge=0)


class AddGeneratedStatblockCombatResponse(BaseModel):
    schema_version: Literal["dmb_add_generated_statblock_to_combat_v1"] = (
        "dmb_add_generated_statblock_to_combat_v1"
    )
    added_entities: list[CombatEntity]
    encounter: CombatEncounterState
    diagnostics: list[str] = Field(default_factory=list)


def _utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def combat_state_path(base: Path) -> Path:
    return base / COMBAT_REL_PATH


def _initial_state(*, packet: dict[str, Any]) -> CombatEncounterState:
    return CombatEncounterState(
        campaign_id=str(packet["campaign_id"]),
        session=int(packet["session"]),
        updated_at=_utc_now(),
        provenance=[
            {
                "source": "live_control_server",
                "reason": "initialized current combat state from live packet metadata",
            }
        ],
    )


def load_or_initialize_current_combat(
    *, base: Path, packet: dict[str, Any]
) -> CombatEncounterState:
    path = combat_state_path(base)
    if not path.is_file():
        return _initial_state(packet=packet)
    return CombatEncounterState.model_validate(load_json(path))


def write_current_combat(*, base: Path, encounter: CombatEncounterState) -> None:
    path = combat_state_path(base)
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json(path, encounter.model_dump(mode="json"))


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "combatant"


def _copy_suffix(index: int) -> str:
    # Spreadsheet-style A..Z, AA.. for the bounded count used here.
    value = index
    chars: list[str] = []
    while True:
        chars.append(chr(ord("A") + (value % 26)))
        value = (value // 26) - 1
        if value < 0:
            return "".join(reversed(chars))


def _base_name(*, explicit: str | None, fallback: str | None, title: str) -> str:
    for candidate in (explicit, fallback, title):
        text = str(candidate or "").strip()
        if text:
            return text
    return "Generated Statblock"


def _entity_name(base_name: str, *, index: int, count: int) -> str:
    if count == 1:
        return base_name
    return f"{base_name} {_copy_suffix(index)}"


def _next_order(encounter: CombatEncounterState) -> int:
    if not encounter.entities:
        return 1
    return max(entity.order for entity in encounter.entities) + 1


def _renumber(encounter: CombatEncounterState) -> None:
    for order, entity in enumerate(encounter.entities, start=1):
        entity.order = order


def _insert_entities(
    *,
    encounter: CombatEncounterState,
    added_entities: list[CombatEntity],
    insert_after_entity_id: str | None,
) -> None:
    if not insert_after_entity_id:
        encounter.entities.extend(added_entities)
        _renumber(encounter)
        return
    for index, entity in enumerate(encounter.entities):
        if entity.id == insert_after_entity_id:
            encounter.entities[index + 1 : index + 1] = added_entities
            _renumber(encounter)
            return
    encounter.entities.extend(added_entities)
    _renumber(encounter)


def _default_notes(*, warning_count: int, retrieval_status: Any) -> str:
    status = str(retrieval_status or "not activated")
    return (
        "Added from generated Statblock View; "
        f"review warnings: {warning_count}; retrieval: {status}."
    )


def _workbench_draft_notes(*, warning_count: int) -> str:
    return (
        "Added from workbench draft; "
        f"review warnings: {warning_count}; not corpus-promoted."
    )


def _group_key(artifact_id: str) -> str:
    return f"generated-{_slug(artifact_id)}-{uuid.uuid4().hex[:6]}"


def add_generated_statblock_to_combat(
    *,
    base: Path,
    root: Path,
    packet: dict[str, Any],
    artifact_id: str,
    request: AddGeneratedStatblockCombatRequest,
) -> AddGeneratedStatblockCombatResponse:
    detail = read_generated_statblock(base=base, root=root, artifact_id=artifact_id)
    combat = detail.combat_defaults
    if combat is None:
        raise StatblockViewError("generated statblock combat_defaults are missing")

    encounter = load_or_initialize_current_combat(base=base, packet=packet)
    base_name = _base_name(
        explicit=request.name_override,
        fallback=combat.name,
        title=detail.title,
    )
    hp = request.hp_override if request.hp_override is not None else combat.hit_points
    max_hp = (
        request.max_hp_override
        if request.max_hp_override is not None
        else combat.hit_points
    )
    notes = request.notes if request.notes is not None else _default_notes(
        warning_count=len(detail.warnings), retrieval_status=detail.retrieval.get("status")
    )
    group_key = request.group_key or (_group_key(artifact_id) if request.count > 1 else None)
    provenance = {
        "source": "generated_statblock_view",
        "artifact_id": detail.artifact_id,
        "draft_id": detail.draft_id,
        "corpus_display_path": detail.corpus_display_path,
        "corpus_file_fingerprint": detail.corpus_file_fingerprint,
        "retrieval_status": detail.retrieval.get("status"),
        "retrieval_verified_at": detail.retrieval.get("verified_at"),
        "added_at": _utc_now(),
        "hydration_contract": "combat_defaults",
    }

    added_entities: list[CombatEntity] = []
    next_order = _next_order(encounter)
    for index in range(request.count):
        name = _entity_name(base_name, index=index, count=request.count)
        entity_id = f"{_slug(name)}-{uuid.uuid4().hex[:6]}"
        added_entities.append(
            CombatEntity(
                id=entity_id,
                name=name,
                team=request.team,
                order=next_order + index,
                init=request.initiative,
                ac=combat.armor_class,
                hp=hp,
                max_hp=max_hp,
                notes=notes,
                tags=["generated_statblock", "corpus_backed", "statblock_view"],
                statblock_path=detail.corpus_display_path,
                statblock_artifact_id=detail.artifact_id,
                statblock_title=detail.title,
                corpus_fingerprint=detail.corpus_file_fingerprint,
                source="corpus",
                provenance=[provenance],
            )
        )

    _insert_entities(
        encounter=encounter,
        added_entities=added_entities,
        insert_after_entity_id=request.insert_after_entity_id,
    )
    if group_key:
        encounter.groups.append(
            {
                "group_key": group_key,
                "label": base_name,
                "statblock_path": detail.corpus_display_path,
                "member_ids": [entity.id for entity in added_entities],
                "collapsed": False,
            }
        )
    encounter.updated_at = _utc_now()
    encounter.provenance.append(
        {
            "source": "statblock_combat_add",
            "artifact_id": detail.artifact_id,
            "added_entity_ids": [entity.id for entity in added_entities],
            "added_at": encounter.updated_at,
        }
    )
    write_current_combat(base=base, encounter=encounter)
    return AddGeneratedStatblockCombatResponse(
        added_entities=added_entities,
        encounter=encounter,
        diagnostics=[
            "added generated statblock to current combat from combat_defaults",
            "wrote only combat/current_combat.json",
        ],
    )


def add_workbench_draft_to_combat(
    *,
    base: Path,
    packet: dict[str, Any],
    artifact_id: str,
    request: AddGeneratedStatblockCombatRequest,
) -> AddGeneratedStatblockCombatResponse:
    record = read_statblock_draft(base=base, artifact_id=artifact_id)
    combat = record.artifact.combat_defaults
    if combat is None:
        raise StatblockViewError("workbench draft combat_defaults are missing")

    encounter = load_or_initialize_current_combat(base=base, packet=packet)
    base_name = _base_name(
        explicit=request.name_override,
        fallback=combat.name,
        title=record.title,
    )
    hp = request.hp_override if request.hp_override is not None else combat.hit_points
    max_hp = (
        request.max_hp_override
        if request.max_hp_override is not None
        else combat.hit_points
    )
    notes = request.notes if request.notes is not None else _workbench_draft_notes(
        warning_count=len(record.artifact.warnings)
    )
    group_key = request.group_key or (_group_key(artifact_id) if request.count > 1 else None)
    provenance = {
        "source": "workbench_draft",
        "artifact_id": record.artifact_id,
        "draft_id": record.artifact.draft_id,
        "storage_path": record.storage_path,
        "added_at": _utc_now(),
        "hydration_contract": "combat_defaults",
    }

    added_entities: list[CombatEntity] = []
    next_order = _next_order(encounter)
    for index in range(request.count):
        name = _entity_name(base_name, index=index, count=request.count)
        entity_id = f"{_slug(name)}-{uuid.uuid4().hex[:6]}"
        added_entities.append(
            CombatEntity(
                id=entity_id,
                name=name,
                team=request.team,
                order=next_order + index,
                init=request.initiative,
                ac=combat.armor_class,
                hp=hp,
                max_hp=max_hp,
                notes=notes,
                tags=["workbench_draft", "of_conks_play"],
                statblock_path=record.corpus_display_path,
                statblock_artifact_id=record.artifact_id,
                statblock_title=record.title,
                corpus_fingerprint=None,
                source="generated_pending",
                provenance=[provenance],
            )
        )

    _insert_entities(
        encounter=encounter,
        added_entities=added_entities,
        insert_after_entity_id=request.insert_after_entity_id,
    )
    if group_key:
        encounter.groups.append(
            {
                "group_key": group_key,
                "label": base_name,
                "statblock_path": record.corpus_display_path,
                "member_ids": [entity.id for entity in added_entities],
                "collapsed": False,
            }
        )
    encounter.updated_at = _utc_now()
    encounter.provenance.append(
        {
            "source": "workbench_draft_combat_add",
            "artifact_id": record.artifact_id,
            "added_entity_ids": [entity.id for entity in added_entities],
            "added_at": encounter.updated_at,
        }
    )
    write_current_combat(base=base, encounter=encounter)
    return AddGeneratedStatblockCombatResponse(
        added_entities=added_entities,
        encounter=encounter,
        diagnostics=[
            "added workbench draft to current combat from combat_defaults",
            "wrote only combat/current_combat.json",
        ],
    )


class CombatEntityNotFoundError(ValueError):
    pass


def _find_entity(encounter: CombatEncounterState, entity_id: str) -> CombatEntity:
    for entity in encounter.entities:
        if entity.id == entity_id:
            return entity
    raise CombatEntityNotFoundError(f"combat entity not found: {entity_id}")


def _touch_and_write(
    *,
    base: Path,
    encounter: CombatEncounterState,
    source: str,
    diagnostics: list[str],
) -> CombatMutationResponse:
    encounter.updated_at = _utc_now()
    encounter.provenance.append(
        {
            "source": source,
            "updated_at": encounter.updated_at,
            "writes": [COMBAT_REL_PATH.as_posix()],
        }
    )
    write_current_combat(base=base, encounter=encounter)
    return CombatMutationResponse(encounter=encounter, diagnostics=diagnostics)


def _load_mutable_current_combat(*, base: Path, packet: dict[str, Any]) -> CombatEncounterState:
    return load_or_initialize_current_combat(base=base, packet=packet)


def patch_combat_entity(
    *,
    base: Path,
    packet: dict[str, Any],
    entity_id: str,
    patch: CombatEntityPatchRequest,
) -> CombatMutationResponse:
    encounter = _load_mutable_current_combat(base=base, packet=packet)
    entity = _find_entity(encounter, entity_id)
    updates = patch.model_dump(exclude_unset=True, mode="json")
    if "conditions" in updates:
        updates["conditions"] = [
            str(item).strip() for item in updates["conditions"] if str(item).strip()
        ]
    for key, value in updates.items():
        setattr(entity, key, value)
    return _touch_and_write(
        base=base,
        encounter=encounter,
        source="combat_entity_patch",
        diagnostics=["patched combat entity", "wrote only combat/current_combat.json"],
    )


def _as_int(value: int | str | None) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.lstrip("-").isdigit():
            return int(stripped)
    return None


def apply_combat_hp_delta(
    *,
    base: Path,
    packet: dict[str, Any],
    entity_id: str,
    delta: CombatHpDeltaRequest,
) -> CombatMutationResponse:
    encounter = _load_mutable_current_combat(base=base, packet=packet)
    entity = _find_entity(encounter, entity_id)
    hp = _as_int(entity.hp)
    max_hp = _as_int(entity.max_hp)
    if delta.action == "set_temp_hp":
        entity.temp_hp = max(entity.temp_hp or 0, delta.amount)
    elif hp is None:
        raise ValueError(f"combat entity hp is not numeric: {entity_id}")
    elif delta.action == "damage":
        remaining = delta.amount
        if entity.temp_hp:
            absorbed = min(entity.temp_hp, remaining)
            entity.temp_hp -= absorbed
            remaining -= absorbed
        entity.hp = max(0, hp - remaining)
    elif delta.action == "heal":
        healed = hp + delta.amount
        entity.hp = min(healed, max_hp) if max_hp is not None else healed
    return _touch_and_write(
        base=base,
        encounter=encounter,
        source="combat_hp_delta",
        diagnostics=[
            f"applied {delta.action} to combat entity",
            "wrote only combat/current_combat.json",
        ],
    )


def sort_combat_initiative(
    *,
    base: Path,
    packet: dict[str, Any],
) -> CombatMutationResponse:
    encounter = _load_mutable_current_combat(base=base, packet=packet)
    encounter.entities.sort(
        key=lambda entity: (
            entity.init is None,
            -(entity.init or 0),
            entity.order,
            entity.name.lower(),
        )
    )
    _renumber(encounter)
    if encounter.entities:
        encounter.active_turn_entity_id = encounter.entities[0].id
        encounter.round_start_entity_id = encounter.entities[0].id
    return _touch_and_write(
        base=base,
        encounter=encounter,
        source="combat_sort_initiative",
        diagnostics=["sorted combat roster by initiative", "wrote only combat/current_combat.json"],
    )


def set_active_combat_turn(
    *,
    base: Path,
    packet: dict[str, Any],
    request: CombatSetActiveRequest,
) -> CombatMutationResponse:
    encounter = _load_mutable_current_combat(base=base, packet=packet)
    if request.entity_id is not None:
        _find_entity(encounter, request.entity_id)
    encounter.active_turn_entity_id = request.entity_id
    if request.entity_id and encounter.round_start_entity_id is None:
        encounter.round_start_entity_id = request.entity_id
    return _touch_and_write(
        base=base,
        encounter=encounter,
        source="combat_set_active_turn",
        diagnostics=["set active combat turn", "wrote only combat/current_combat.json"],
    )


def advance_combat_turn(
    *,
    base: Path,
    packet: dict[str, Any],
    request: CombatTurnRequest,
) -> CombatMutationResponse:
    encounter = _load_mutable_current_combat(base=base, packet=packet)
    if not encounter.entities:
        encounter.active_turn_entity_id = None
        return _touch_and_write(
            base=base,
            encounter=encounter,
            source="combat_advance_turn",
            diagnostics=["combat roster is empty", "wrote only combat/current_combat.json"],
        )
    ids = [entity.id for entity in encounter.entities]
    if encounter.active_turn_entity_id not in ids:
        encounter.active_turn_entity_id = ids[0]
        if encounter.round_start_entity_id is None:
            encounter.round_start_entity_id = ids[0]
        return _touch_and_write(
            base=base,
            encounter=encounter,
            source="combat_advance_turn",
            diagnostics=["initialized active combat turn", "wrote only combat/current_combat.json"],
        )
    index = ids.index(encounter.active_turn_entity_id)
    step = 1 if request.direction == "next" else -1
    next_index = (index + step) % len(ids)
    if request.direction == "next" and next_index == 0:
        encounter.round += 1
        encounter.round_start_entity_id = ids[0]
    elif request.direction == "previous" and index == 0 and encounter.round > 1:
        encounter.round -= 1
        encounter.round_start_entity_id = ids[0]
    encounter.active_turn_entity_id = ids[next_index]
    return _touch_and_write(
        base=base,
        encounter=encounter,
        source="combat_advance_turn",
        diagnostics=[
            f"moved combat turn {request.direction}",
            "wrote only combat/current_combat.json",
        ],
    )
