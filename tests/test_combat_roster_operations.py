from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from apps.live_control_server.services.combat_state import (
    CombatEncounterState,
    CombatEntity,
    CombatEntityNotFoundError,
    CombatEntityPatchRequest,
    CombatHpDeltaRequest,
    CombatSetActiveRequest,
    CombatTurnRequest,
    apply_combat_hp_delta,
    combat_state_path,
    patch_combat_entity,
    set_active_combat_turn,
    sort_combat_initiative,
    advance_combat_turn,
    write_current_combat,
)

PACKET = {"campaign_id": "longmont-c2", "session": 22}


def _entity(
    entity_id: str,
    *,
    name: str,
    order: int,
    init: int | None,
    hp: int | str = 10,
    max_hp: int | str = 10,
    temp_hp: int | None = 0,
    defeated: bool = False,
) -> CombatEntity:
    return CombatEntity(
        id=entity_id,
        name=name,
        team="enemy",
        order=order,
        init=init,
        ac=12,
        hp=hp,
        max_hp=max_hp,
        temp_hp=temp_hp,
        defeated=defeated,
    )


def _write_state(base: Path, entities: list[CombatEntity], *, active: str | None = None, round: int = 1) -> None:
    state = CombatEncounterState(
        campaign_id="longmont-c2",
        session=22,
        round=round,
        active_turn_entity_id=active,
        round_start_entity_id=active,
        entities=entities,
        updated_at="2026-06-10T00:00:00Z",
    )
    write_current_combat(base=base, encounter=state)


def _snapshot_files(base: Path) -> dict[str, bytes]:
    return {
        path.relative_to(base).as_posix(): path.read_bytes()
        for path in base.rglob("*")
        if path.is_file()
    }


def _combat_bytes(base: Path) -> bytes:
    return combat_state_path(base).read_bytes()


def test_patch_entity_updates_fields_and_writes_only_current_combat(tmp_path: Path) -> None:
    _write_state(tmp_path, [_entity("a", name="Acolyte", order=1, init=8)])
    (tmp_path / "unrelated.json").write_text('{"keep":true}', encoding="utf-8")
    before = _snapshot_files(tmp_path)

    response = patch_combat_entity(
        base=tmp_path,
        packet=PACKET,
        entity_id="a",
        patch=CombatEntityPatchRequest(
            team="ally",
            init=14,
            hp=7,
            temp_hp=3,
            notes="bloodied",
            conditions=[" prone ", "", "frightened"],
            defeated=True,
        ),
    )

    entity = response.encounter.entities[0]
    assert entity.team == "ally"
    assert entity.init == 14
    assert entity.hp == 7
    assert entity.temp_hp == 3
    assert entity.notes == "bloodied"
    assert entity.conditions == ["prone", "frightened"]
    assert entity.defeated is True
    after = _snapshot_files(tmp_path)
    changed = {path for path, content in after.items() if before.get(path) != content}
    assert changed == {"combat/current_combat.json"}


def test_damage_heal_and_temp_hp_do_not_auto_toggle_defeated(tmp_path: Path) -> None:
    _write_state(
        tmp_path,
        [_entity("a", name="Ogre", order=1, init=10, hp=5, max_hp=20, temp_hp=3)],
    )

    damaged = apply_combat_hp_delta(
        base=tmp_path,
        packet=PACKET,
        entity_id="a",
        delta=CombatHpDeltaRequest(action="damage", amount=20),
    ).encounter.entities[0]
    assert damaged.temp_hp == 0
    assert damaged.hp == 0
    assert damaged.defeated is False

    patch_combat_entity(
        base=tmp_path,
        packet=PACKET,
        entity_id="a",
        patch=CombatEntityPatchRequest(defeated=True),
    )
    healed = apply_combat_hp_delta(
        base=tmp_path,
        packet=PACKET,
        entity_id="a",
        delta=CombatHpDeltaRequest(action="heal", amount=6),
    ).encounter.entities[0]
    assert healed.hp == 6
    assert healed.defeated is True

    temp = apply_combat_hp_delta(
        base=tmp_path,
        packet=PACKET,
        entity_id="a",
        delta=CombatHpDeltaRequest(action="set_temp_hp", amount=4),
    ).encounter.entities[0]
    assert temp.temp_hp == 4
    temp_again = apply_combat_hp_delta(
        base=tmp_path,
        packet=PACKET,
        entity_id="a",
        delta=CombatHpDeltaRequest(action="set_temp_hp", amount=2),
    ).encounter.entities[0]
    assert temp_again.temp_hp == 4


def test_hp_delta_rejects_zero_and_non_numeric_hp_failure_leaves_file_unchanged(tmp_path: Path) -> None:
    with pytest.raises(ValidationError):
        CombatHpDeltaRequest(action="damage", amount=0)

    _write_state(
        tmp_path,
        [_entity("a", name="Mist", order=1, init=10, hp="unknown", max_hp="unknown")],
    )
    before = _combat_bytes(tmp_path)

    with pytest.raises(ValueError, match="hp is not numeric"):
        apply_combat_hp_delta(
            base=tmp_path,
            packet=PACKET,
            entity_id="a",
            delta=CombatHpDeltaRequest(action="damage", amount=1),
        )

    assert _combat_bytes(tmp_path) == before


def test_initiative_sort_renumbers_and_sets_active_to_first_sorted_entity(tmp_path: Path) -> None:
    _write_state(
        tmp_path,
        [
            _entity("slow", name="Slow", order=1, init=4),
            _entity("fast", name="Fast", order=2, init=18),
            _entity("none", name="No Init", order=3, init=None),
        ],
        active="slow",
    )

    encounter = sort_combat_initiative(base=tmp_path, packet=PACKET).encounter

    assert [entity.id for entity in encounter.entities] == ["fast", "slow", "none"]
    assert [entity.order for entity in encounter.entities] == [1, 2, 3]
    assert encounter.active_turn_entity_id == "fast"
    assert encounter.round_start_entity_id == "fast"


def test_turn_next_previous_wraps_and_updates_round(tmp_path: Path) -> None:
    _write_state(
        tmp_path,
        [
            _entity("first", name="First", order=1, init=20),
            _entity("second", name="Second", order=2, init=10),
        ],
        active="first",
        round=1,
    )

    next_turn = advance_combat_turn(
        base=tmp_path,
        packet=PACKET,
        request=CombatTurnRequest(direction="next"),
    ).encounter
    assert next_turn.active_turn_entity_id == "second"
    assert next_turn.round == 1

    wrapped = advance_combat_turn(
        base=tmp_path,
        packet=PACKET,
        request=CombatTurnRequest(direction="next"),
    ).encounter
    assert wrapped.active_turn_entity_id == "first"
    assert wrapped.round == 2

    rewound = advance_combat_turn(
        base=tmp_path,
        packet=PACKET,
        request=CombatTurnRequest(direction="previous"),
    ).encounter
    assert rewound.active_turn_entity_id == "second"
    assert rewound.round == 1


def test_entity_not_found_failure_leaves_file_unchanged(tmp_path: Path) -> None:
    _write_state(tmp_path, [_entity("a", name="A", order=1, init=1)])
    before = _combat_bytes(tmp_path)

    with pytest.raises(CombatEntityNotFoundError):
        patch_combat_entity(
            base=tmp_path,
            packet=PACKET,
            entity_id="missing",
            patch=CombatEntityPatchRequest(notes="nope"),
        )
    with pytest.raises(CombatEntityNotFoundError):
        set_active_combat_turn(
            base=tmp_path,
            packet=PACKET,
            request=CombatSetActiveRequest(entity_id="missing"),
        )

    assert _combat_bytes(tmp_path) == before
