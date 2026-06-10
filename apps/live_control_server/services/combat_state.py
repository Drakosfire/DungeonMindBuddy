from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

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
