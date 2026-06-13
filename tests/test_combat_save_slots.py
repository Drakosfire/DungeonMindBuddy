from __future__ import annotations

import json
from pathlib import Path

import pytest

from apps.live_control_server.config import repo_root
from apps.live_control_server.services.combat_saves import (
    CombatSaveNotFoundError,
    LoadCombatSaveRequest,
    NewCombatEncounterRequest,
    SaveCurrentCombatRequest,
    UnsafeSaveIdError,
    convert_static_mireward_save,
    list_combat_backups,
    list_combat_saves,
    load_combat_save,
    new_combat_encounter,
    save_current_as,
    unload_current_combat,
    write_combat_save,
)
from apps.live_control_server.services.combat_state import (
    CombatEncounterState,
    CombatEntity,
    combat_state_path,
    write_current_combat,
)

PACKET = {"campaign_id": "longmont-c2", "session": 23}


def _entity(entity_id: str, *, order: int, init: int | None = 10) -> CombatEntity:
    return CombatEntity(id=entity_id, name=entity_id.title(), team="enemy", order=order, init=init)


def _state(entities: list[CombatEntity], *, title: str = "Live", round: int = 1) -> CombatEncounterState:
    return CombatEncounterState(
        campaign_id="longmont-c2",
        session=23,
        title=title,
        round=round,
        active_turn_entity_id=entities[0].id if entities else None,
        round_start_entity_id=entities[0].id if entities else None,
        entities=entities,
        updated_at="2026-06-10T00:00:00Z",
    )


def _write_current(base: Path, encounter: CombatEncounterState) -> None:
    write_current_combat(base=base, encounter=encounter)


def _backup_dir(base: Path) -> Path:
    return base / "combat" / "backups"


# --------------------------------------------------------------------------- #
# load preserves prior state
# --------------------------------------------------------------------------- #
def test_load_save_preserves_prior_state_in_preload_backup(tmp_path: Path) -> None:
    prior = _state([_entity("ogre", order=1)], title="Prior fight")
    _write_current(tmp_path, prior)
    prior_bytes = combat_state_path(tmp_path).read_bytes()

    incoming = _state([_entity("goblin", order=1), _entity("kobold", order=2)], title="Saved fight")
    write_combat_save(base=tmp_path, save_id="saved", encounter=incoming)

    response = load_combat_save(base=tmp_path, packet=PACKET, save_id="saved")

    # current_combat now holds the loaded save
    assert response.encounter.title == "Saved fight"
    assert [e.id for e in response.encounter.entities] == ["goblin", "kobold"]
    loaded_on_disk = CombatEncounterState.model_validate(
        json.loads(combat_state_path(tmp_path).read_text(encoding="utf-8"))
    )
    assert [e.id for e in loaded_on_disk.entities] == ["goblin", "kobold"]

    # the prior fight is preserved byte-for-byte in exactly one preload backup
    preloads = list(_backup_dir(tmp_path).glob("*.preload.json"))
    assert len(preloads) == 1
    assert preloads[0].read_bytes() == prior_bytes
    assert response.backups == [preloads[0].relative_to(tmp_path).as_posix()]

    # provenance records the preload pointer
    prov = response.encounter.provenance[-1]
    assert prov["source"] == "combat_load_save"
    assert prov["preload_backup"] == response.backups[0]


def test_load_missing_save_raises_and_leaves_current_unchanged(tmp_path: Path) -> None:
    _write_current(tmp_path, _state([_entity("ogre", order=1)]))
    before = combat_state_path(tmp_path).read_bytes()
    with pytest.raises(CombatSaveNotFoundError):
        load_combat_save(base=tmp_path, packet=PACKET, save_id="nope")
    assert combat_state_path(tmp_path).read_bytes() == before


def test_unsafe_save_id_rejected(tmp_path: Path) -> None:
    for bad in ["../escape", "a/b", ".", "..", "with space", ""]:
        with pytest.raises((UnsafeSaveIdError, Exception)):
            write_combat_save(base=tmp_path, save_id=bad, encounter=_state([]))


# --------------------------------------------------------------------------- #
# unload snapshots then resets
# --------------------------------------------------------------------------- #
def test_unload_snapshots_then_resets_to_empty(tmp_path: Path) -> None:
    prior = _state([_entity("ogre", order=1), _entity("orc", order=2)], title="Prior")
    _write_current(tmp_path, prior)
    prior_bytes = combat_state_path(tmp_path).read_bytes()

    response = unload_current_combat(base=tmp_path, packet=PACKET)

    assert response.encounter.entities == []
    assert response.encounter.active_turn_entity_id is None
    unloads = list(_backup_dir(tmp_path).glob("*.unload.json"))
    assert len(unloads) == 1
    assert unloads[0].read_bytes() == prior_bytes


def test_new_encounter_preserves_old_and_applies_title(tmp_path: Path) -> None:
    prior = _state([_entity("ogre", order=1)], title="Old")
    _write_current(tmp_path, prior)
    prior_bytes = combat_state_path(tmp_path).read_bytes()

    response = new_combat_encounter(
        base=tmp_path,
        packet=PACKET,
        request=NewCombatEncounterRequest(title="Ambush", encounter_id="ambush-1"),
    )

    assert response.encounter.title == "Ambush"
    assert response.encounter.encounter_id == "ambush-1"
    assert response.encounter.entities == []
    unloads = list(_backup_dir(tmp_path).glob("*.unload.json"))
    assert len(unloads) == 1
    assert unloads[0].read_bytes() == prior_bytes


def test_unload_without_current_state_is_safe(tmp_path: Path) -> None:
    response = unload_current_combat(base=tmp_path, packet=PACKET)
    assert response.encounter.entities == []
    assert response.backups == []


# --------------------------------------------------------------------------- #
# round-trip: load preserves old, then we can load the old back without loss
# --------------------------------------------------------------------------- #
def test_load_unload_load_chain_never_loses_state(tmp_path: Path) -> None:
    fight_a = _state([_entity("a1", order=1)], title="Fight A")
    fight_b = _state([_entity("b1", order=1), _entity("b2", order=2)], title="Fight B")
    write_combat_save(base=tmp_path, save_id="a", encounter=fight_a)
    write_combat_save(base=tmp_path, save_id="b", encounter=fight_b)

    # start with A live
    _write_current(tmp_path, fight_a)
    # load B (A snapshotted as preload)
    load_combat_save(base=tmp_path, packet=PACKET, save_id="b")
    # unload B (B snapshotted as unload)
    unload_current_combat(base=tmp_path, packet=PACKET)
    # load A back
    response = load_combat_save(base=tmp_path, packet=PACKET, save_id="a")

    assert response.encounter.title == "Fight A"
    # both transitions left durable snapshots
    assert len(list(_backup_dir(tmp_path).glob("*.preload.json"))) == 2
    assert len(list(_backup_dir(tmp_path).glob("*.unload.json"))) == 1


def test_save_current_as_creates_listed_slot(tmp_path: Path) -> None:
    _write_current(tmp_path, _state([_entity("ogre", order=1)], title="Live"))
    save_current_as(base=tmp_path, request=SaveCurrentCombatRequest(save_id="snap", title="Snapshot"))
    summaries = list_combat_saves(tmp_path)
    assert [s.save_id for s in summaries] == ["snap"]
    assert summaries[0].title == "Snapshot"
    assert summaries[0].entity_count == 1


# --------------------------------------------------------------------------- #
# static bridge converter
# --------------------------------------------------------------------------- #
def test_convert_static_mireward_save_maps_fields() -> None:
    static = {
        "schema": "mireward_north_reach_gate_combat_state_v1",
        "source": "test",
        "state": {
            "round": 2,
            "turnIndex": 1,
            "entities": [
                {"id": "pc1", "name": "Karsemine", "team": "pc", "order": 0, "init": "25", "hp": "54", "maxHp": "44", "notes": "", "defeated": False, "statblockPath": ""},
                {"id": "enemy1", "name": "Meatwing", "team": "enemy", "order": 1, "init": "10", "hp": "0", "maxHp": 18, "notes": "down", "defeated": True, "statblockPath": "corpus/x.md"},
            ],
        },
    }
    encounter = convert_static_mireward_save(static=static, packet=PACKET)

    assert encounter.schema == "dmb_combat_encounter_state_v1"
    assert encounter.round == 2
    assert encounter.round_start_entity_id == "pc1"
    assert encounter.active_turn_entity_id == "enemy1"  # turnIndex 1
    assert [e.order for e in encounter.entities] == [1, 2]  # renumbered 1-based

    pc1, enemy1 = encounter.entities
    assert pc1.init == 25  # coerced to int
    assert pc1.hp == "54" and pc1.max_hp == "44"  # preserved as strings
    assert pc1.statblock_path is None  # empty -> None
    assert pc1.source == "imported"
    assert "imported_static_combat" in pc1.tags

    assert enemy1.team == "enemy"
    assert enemy1.defeated is True
    assert enemy1.max_hp == 18  # int preserved
    assert enemy1.statblock_path == "corpus/x.md"


def test_convert_real_static_save_fidelity() -> None:
    static_path = (
        repo_root()
        / "evals/c2_live_prep/mireward-prep/saves/combat/longmont-c2__session_22__north_reach_gate__combat_state_v1.json"
    )
    if not static_path.is_file():
        pytest.skip("static mireward save fixture not present")
    static = json.loads(static_path.read_text(encoding="utf-8"))
    encounter = convert_static_mireward_save(static=static, packet=PACKET)
    assert len(encounter.entities) == 25
    assert encounter.round == 2
    assert encounter.round_start_entity_id == "karsemine"
    assert encounter.active_turn_entity_id == "caelynn"  # static turnIndex 16
