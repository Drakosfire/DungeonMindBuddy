"""Combat save-slot lifecycle: import / load / unload / new, with auto-backups.

The live combat surface keeps exactly one ``combat/current_combat.json`` per
session (see ``combat_state.py``). This module adds the operator-facing save-slot
lifecycle on top of that single-file model:

* ``combat/saves/<save_id>.json`` — named, reusable encounter snapshots a GM can
  load on demand (e.g. the imported North Reach Gate state).
* ``combat/backups/current_combat.<ts>.<kind>.json`` — automatic snapshots taken
  *before* any destructive transition so the prior state is never lost. ``kind``
  is ``preload`` (snapshot taken before loading a save) or ``unload`` (snapshot
  taken before unloading / starting a new encounter).

It also bridges the legacy static Mireward command-board save
(``mireward_north_reach_gate_combat_state_v1``) into the live
``dmb_combat_encounter_state_v1`` schema so the same fight that proved useful at
the table can be loaded into the live-control surface.
"""

from __future__ import annotations

import re
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from apps.live_control_server.services.combat_state import (
    CombatEncounterState,
    CombatEntity,
    CombatTeam,
    _initial_state,
    _renumber,
    _utc_now,
    combat_state_path,
    write_current_combat,
)
from src.live_play.live_store import load_json, write_json

STATIC_MIREWARD_SCHEMA = "mireward_north_reach_gate_combat_state_v1"
STATIC_MIREWARD_SCHEMA_V1 = "mireward_combat_state_v1"
STATIC_MIREWARD_SCHEMAS = frozenset({STATIC_MIREWARD_SCHEMA, STATIC_MIREWARD_SCHEMA_V1})
_SAVE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_VALID_TEAMS = {"pc", "ally", "enemy", "neutral"}

BackupKind = Literal["preload", "unload"]


# --------------------------------------------------------------------------- #
# Errors
# --------------------------------------------------------------------------- #
class CombatSaveNotFoundError(ValueError):
    pass


class UnsafeSaveIdError(ValueError):
    pass


class StaticCombatSaveError(ValueError):
    pass


# --------------------------------------------------------------------------- #
# Response models
# --------------------------------------------------------------------------- #
class CombatSaveSummary(BaseModel):
    save_id: str
    title: str
    encounter_id: str
    entity_count: int
    round: int
    updated_at: str | None = None


class CombatSaveSlotResponse(BaseModel):
    schema_version: Literal["dmb_combat_save_slot_v1"] = "dmb_combat_save_slot_v1"
    encounter: CombatEncounterState
    saves: list[CombatSaveSummary] = Field(default_factory=list)
    backups: list[str] = Field(default_factory=list)
    diagnostics: list[str] = Field(default_factory=list)


class NewCombatEncounterRequest(BaseModel):
    title: str | None = None
    encounter_id: str | None = None


class LoadCombatSaveRequest(BaseModel):
    save_id: str = Field(min_length=1)


class SaveCurrentCombatRequest(BaseModel):
    save_id: str = Field(min_length=1)
    title: str | None = None


# --------------------------------------------------------------------------- #
# Path helpers
# --------------------------------------------------------------------------- #
def _combat_dir(base: Path) -> Path:
    return base / "combat"


def _saves_dir(base: Path) -> Path:
    return _combat_dir(base) / "saves"


def _backups_dir(base: Path) -> Path:
    return _combat_dir(base) / "backups"


def _ts() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def _safe_save_id(save_id: str) -> str:
    candidate = (save_id or "").strip()
    if not _SAVE_ID_PATTERN.fullmatch(candidate) or candidate in {".", ".."}:
        raise UnsafeSaveIdError(f"unsafe combat save id: {save_id!r}")
    return candidate


def _save_path(base: Path, save_id: str) -> Path:
    return _saves_dir(base) / f"{_safe_save_id(save_id)}.json"


def _backup_current(base: Path, *, kind: BackupKind) -> str | None:
    """Snapshot the existing current_combat.json into backups; return its rel path.

    Returns ``None`` when there is no current state to preserve.
    """
    source = combat_state_path(base)
    if not source.is_file():
        return None
    backups = _backups_dir(base)
    backups.mkdir(parents=True, exist_ok=True)
    stamp = _ts()
    dest = backups / f"current_combat.{stamp}.{kind}.json"
    suffix = 1
    # Keep the trailing ``.<kind>.json`` suffix stable under same-second collisions
    # by disambiguating the timestamp segment instead.
    while dest.exists():
        dest = backups / f"current_combat.{stamp}-{suffix}.{kind}.json"
        suffix += 1
    shutil.copy2(source, dest)
    return dest.relative_to(base).as_posix()


# --------------------------------------------------------------------------- #
# Listing
# --------------------------------------------------------------------------- #
def list_combat_saves(base: Path) -> list[CombatSaveSummary]:
    saves_dir = _saves_dir(base)
    summaries: list[CombatSaveSummary] = []
    if not saves_dir.is_dir():
        return summaries
    for path in sorted(saves_dir.glob("*.json")):
        try:
            data = load_json(path)
        except (ValueError, TypeError, OSError):
            continue
        entities = data.get("entities") if isinstance(data.get("entities"), list) else []
        summaries.append(
            CombatSaveSummary(
                save_id=path.stem,
                title=str(data.get("title") or path.stem),
                encounter_id=str(data.get("encounter_id") or path.stem),
                entity_count=len(entities),
                round=int(data.get("round") or 1),
                updated_at=data.get("updated_at"),
            )
        )
    return summaries


def list_combat_backups(base: Path) -> list[str]:
    backups_dir = _backups_dir(base)
    if not backups_dir.is_dir():
        return []
    return [path.relative_to(base).as_posix() for path in sorted(backups_dir.glob("*.json"))]


def _slot_response(
    base: Path, encounter: CombatEncounterState, *, diagnostics: list[str]
) -> CombatSaveSlotResponse:
    return CombatSaveSlotResponse(
        encounter=encounter,
        saves=list_combat_saves(base),
        backups=list_combat_backups(base),
        diagnostics=diagnostics,
    )


# --------------------------------------------------------------------------- #
# Lifecycle operations
# --------------------------------------------------------------------------- #
def load_combat_save(*, base: Path, packet: dict[str, Any], save_id: str) -> CombatSaveSlotResponse:
    """Load a named save into current_combat, preserving the prior state."""
    save_path = _save_path(base, save_id)
    if not save_path.is_file():
        raise CombatSaveNotFoundError(f"combat save not found: {save_id}")
    encounter = CombatEncounterState.model_validate(load_json(save_path))
    preload = _backup_current(base, kind="preload")
    encounter.updated_at = _utc_now()
    encounter.provenance.append(
        {
            "source": "combat_load_save",
            "save_id": _safe_save_id(save_id),
            "preload_backup": preload,
            "loaded_at": encounter.updated_at,
        }
    )
    write_current_combat(base=base, encounter=encounter)
    note = (
        f"preserved prior current_combat at {preload}"
        if preload
        else "no prior current_combat.json to preserve"
    )
    return _slot_response(
        base,
        encounter,
        diagnostics=[f"loaded combat save '{save_id}'", note],
    )


def unload_current_combat(*, base: Path, packet: dict[str, Any]) -> CombatSaveSlotResponse:
    """Snapshot the current encounter, then reset to a fresh empty encounter."""
    backup = _backup_current(base, kind="unload")
    fresh = _initial_state(packet=packet)
    fresh.provenance.append({"source": "combat_unload", "unload_backup": backup})
    write_current_combat(base=base, encounter=fresh)
    note = (
        f"preserved unloaded state at {backup}"
        if backup
        else "no prior current_combat.json to preserve"
    )
    return _slot_response(base, fresh, diagnostics=["unloaded current combat", note])


def new_combat_encounter(
    *, base: Path, packet: dict[str, Any], request: NewCombatEncounterRequest
) -> CombatSaveSlotResponse:
    """Snapshot the current encounter, then start a fresh (optionally named) one."""
    backup = _backup_current(base, kind="unload")
    fresh = _initial_state(packet=packet)
    if request.title:
        fresh.title = request.title
    if request.encounter_id:
        fresh.encounter_id = request.encounter_id
    fresh.provenance.append({"source": "combat_new_encounter", "unload_backup": backup})
    write_current_combat(base=base, encounter=fresh)
    note = (
        f"preserved prior state at {backup}"
        if backup
        else "no prior current_combat.json to preserve"
    )
    return _slot_response(base, fresh, diagnostics=["started new combat encounter", note])


def save_current_as(
    *, base: Path, request: SaveCurrentCombatRequest
) -> CombatSaveSlotResponse:
    """Persist the current encounter as a reusable named save slot."""
    current_path = combat_state_path(base)
    if not current_path.is_file():
        raise CombatSaveNotFoundError("no current_combat.json to save")
    encounter = CombatEncounterState.model_validate(load_json(current_path))
    if request.title:
        encounter.title = request.title
    saves_dir = _saves_dir(base)
    saves_dir.mkdir(parents=True, exist_ok=True)
    target = _save_path(base, request.save_id)
    write_json(target, encounter.model_dump(mode="json"))
    return _slot_response(
        base,
        encounter,
        diagnostics=[f"saved current combat as '{request.save_id}'"],
    )


def write_combat_save(
    *, base: Path, save_id: str, encounter: CombatEncounterState
) -> Path:
    """Write a validated encounter to a named save slot (no current_combat change)."""
    saves_dir = _saves_dir(base)
    saves_dir.mkdir(parents=True, exist_ok=True)
    target = _save_path(base, save_id)
    write_json(target, encounter.model_dump(mode="json"))
    return target


# --------------------------------------------------------------------------- #
# Static-save bridge (mireward_north_reach_gate_combat_state_v1 -> live schema)
# --------------------------------------------------------------------------- #
def _as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.lstrip("-").isdigit():
            return int(stripped)
    return None


def _coerce_hp(value: Any) -> int | str | None:
    """Preserve numeric ints as ints and keep non-empty strings verbatim."""
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    text = str(value).strip()
    return text or None


def _coerce_team(value: Any) -> CombatTeam:
    text = str(value or "").strip().lower()
    return text if text in _VALID_TEAMS else "enemy"  # type: ignore[return-value]


def convert_static_mireward_save(
    *, static: dict[str, Any], packet: dict[str, Any]
) -> CombatEncounterState:
    """Convert the static command-board combat save into the live schema."""
    schema = static.get("schema")
    if schema not in STATIC_MIREWARD_SCHEMAS:
        expected = ", ".join(sorted(STATIC_MIREWARD_SCHEMAS))
        raise StaticCombatSaveError(f"expected schema one of ({expected}), got {schema!r}")
    state = static.get("state") if isinstance(static.get("state"), dict) else static
    raw_entities = state.get("entities") if isinstance(state.get("entities"), list) else []
    ordered = sorted(raw_entities, key=lambda item: _as_int(item.get("order")) or 0)
    encounter_slug = str(static.get("encounter_slug") or "north_reach_gate").strip()

    entities: list[CombatEntity] = []
    for entity in ordered:
        statblock_path = str(entity.get("statblockPath") or "").strip() or None
        entities.append(
            CombatEntity(
                id=str(entity["id"]),
                name=str(entity.get("name") or entity["id"]),
                team=_coerce_team(entity.get("team")),
                order=0,  # renumbered below
                init=_as_int(entity.get("init")),
                hp=_coerce_hp(entity.get("hp")),
                max_hp=_coerce_hp(entity.get("maxHp")),
                defeated=bool(entity.get("defeated")),
                notes=str(entity.get("notes") or "").strip(),
                statblock_path=statblock_path,
                source="imported",
                tags=["imported_static_combat"],
            )
        )

    encounter = CombatEncounterState(
        campaign_id=str(packet["campaign_id"]),
        session=int(packet["session"]),
        encounter_id=encounter_slug,
        title=encounter_slug.replace("_", " ").title() + " Combat",
        round=_as_int(state.get("round")) or 1,
        queue_model="circular_barrel_v1",
        entities=entities,
        updated_at=_utc_now(),
        provenance=[
            {
                "source": "static_mireward_import",
                "origin_schema": schema,
                "origin_source": static.get("source"),
                "origin_exported_at": static.get("exportedAt"),
            }
        ],
    )
    _renumber(encounter)

    if entities:
        encounter.round_start_entity_id = entities[0].id
        turn_index = _as_int(state.get("turnIndex"))
        if turn_index is not None and 0 <= turn_index < len(entities):
            encounter.active_turn_entity_id = entities[turn_index].id
        else:
            encounter.active_turn_entity_id = entities[0].id
    return encounter
