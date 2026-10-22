from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from threading import Barrier
from uuid import uuid4

import psycopg
import pytest

from application_state.combat_encounters import rulesets
from application_state.combat_encounters.service import (
    create_encounter,
    get_encounter,
    list_encounters,
    save_encounter,
)
from application_state.combat_encounters.types import (
    CombatEncounterDraft,
    CombatEncounterRecord,
    CombatEntity,
    CreateCombatEncounterRequest,
    SaveCombatEncounterRequest,
)
from application_state.errors import (
    ApplicationStateConflictError,
    ApplicationStateNotFoundError,
    ApplicationStateValidationError,
)


def _entity(entity_id: str, name: str, order: int) -> CombatEntity:
    return CombatEntity(id=entity_id, name=name, order=order, team="enemy")


def _draft(title: str, *, entity_name: str | None = None) -> CombatEncounterDraft:
    entities = [_entity("enemy-1", entity_name, 1)] if entity_name else []
    return CombatEncounterDraft(title=title, entities=entities)


def test_encounter_create_list_open_save_and_reopen(
    application_state_dsn: str,
) -> None:
    created = create_encounter(
        world_id="elderwyld",
        request=CreateCombatEncounterRequest(
            title="Mireward Gate",
            campaign_id="longmont-c2",
            session=29,
        ),
    )

    assert created.revision == 1
    assert created.ruleset.config_id == "generic.manual-tracking"
    assert len(created.ruleset_digest) == 64
    assert list_encounters(world_id="elderwyld") == [created]
    assert get_encounter(world_id="elderwyld", encounter_id=created.encounter_id) == created

    saved = save_encounter(
        world_id="elderwyld",
        encounter_id=created.encounter_id,
        request=SaveCombatEncounterRequest(
            expected_revision=created.revision,
            draft=_draft("Mireward Gate", entity_name="Geomantic Drake"),
        ),
    )

    assert saved.revision == 2
    reopened = get_encounter(world_id="elderwyld", encounter_id=created.encounter_id)
    assert reopened == saved
    assert reopened.draft.entities[0].name == "Geomantic Drake"


def test_encounter_compare_and_swap_allows_one_concurrent_writer(
    application_state_dsn: str,
) -> None:
    created = create_encounter(
        world_id="elderwyld",
        request=CreateCombatEncounterRequest(title="Concurrent encounter"),
    )
    barrier = Barrier(2)

    def write(title: str):
        barrier.wait(timeout=5)
        return save_encounter(
            world_id="elderwyld",
            encounter_id=created.encounter_id,
            request=SaveCombatEncounterRequest(
                expected_revision=1,
                draft=_draft(title),
            ),
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(write, "Writer A"), executor.submit(write, "Writer B")]
        outcomes = []
        for future in futures:
            try:
                outcomes.append(future.result(timeout=20))
            except ApplicationStateConflictError as error:
                outcomes.append(error)

    winners = [outcome for outcome in outcomes if not isinstance(outcome, Exception)]
    conflicts = [outcome for outcome in outcomes if isinstance(outcome, ApplicationStateConflictError)]
    assert len(winners) == 1
    assert len(conflicts) == 1
    stored = get_encounter(world_id="elderwyld", encounter_id=created.encounter_id)
    assert stored.revision == 2
    assert stored.draft.title == winners[0].draft.title


def test_encounter_is_world_scoped_and_stale_revision_cannot_replace_state(
    application_state_dsn: str,
) -> None:
    created = create_encounter(
        world_id="elderwyld",
        request=CreateCombatEncounterRequest(title="World scoped"),
    )
    with pytest.raises(ApplicationStateNotFoundError):
        get_encounter(world_id="conks-and-cons", encounter_id=created.encounter_id)

    saved = save_encounter(
        world_id="elderwyld",
        encounter_id=created.encounter_id,
        request=SaveCombatEncounterRequest(expected_revision=1, draft=_draft("Saved")),
    )
    with pytest.raises(ApplicationStateConflictError):
        save_encounter(
            world_id="elderwyld",
            encounter_id=created.encounter_id,
            request=SaveCombatEncounterRequest(expected_revision=1, draft=_draft("Stale")),
        )
    assert get_encounter(world_id="elderwyld", encounter_id=created.encounter_id) == saved


def test_ruleset_snapshot_survives_catalog_change_without_following_latest(
    application_state_dsn: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    created = create_encounter(
        world_id="elderwyld",
        request=CreateCombatEncounterRequest(title="Pinned rules"),
    )
    original_config = rulesets.load_ruleset("generic.manual-tracking")
    changed_config = original_config.model_copy(update={"revision": "2"})
    monkeypatch.setitem(rulesets._CATALOG, original_config.config_id, changed_config)

    reopened = get_encounter(world_id="elderwyld", encounter_id=created.encounter_id)
    assert reopened.ruleset.revision == "1"
    assert reopened.ruleset_digest == created.ruleset_digest


def test_corrupt_ruleset_digest_fails_closed(
    application_state_dsn: str,
) -> None:
    created = create_encounter(
        world_id="elderwyld",
        request=CreateCombatEncounterRequest(title="Corrupt pin"),
    )
    with psycopg.connect(application_state_dsn) as conn:
        conn.execute(
            "UPDATE combat.encounter SET ruleset_digest = %s WHERE encounter_id = %s",
            ("0" * 64, created.encounter_id),
        )

    with pytest.raises(ApplicationStateValidationError, match="digest is invalid"):
        get_encounter(world_id="elderwyld", encounter_id=created.encounter_id)


def test_create_rejects_session_without_campaign_and_draft_duplicate_references() -> None:
    with pytest.raises(ValueError, match="requires a campaign"):
        CreateCombatEncounterRequest(title="Invalid", session=29)

    with pytest.raises(ValueError, match="combatant IDs must be unique"):
        CombatEncounterDraft(
            title="Invalid draft",
            entities=[_entity("duplicate", "First", 1), _entity("duplicate", "Second", 2)],
        )

    with pytest.raises(ValueError, match="group keys must be unique"):
        CombatEncounterDraft(
            title="Invalid groups",
            entities=[_entity("one", "One", 1), _entity("two", "Two", 2)],
            groups=[
                {"group_key": "drakes", "label": "Drakes", "member_ids": ["one"]},
                {"group_key": "drakes", "label": "More drakes", "member_ids": ["two"]},
            ],
        )


@pytest.mark.parametrize("campaign_id", ["", "   "])
@pytest.mark.parametrize("session", [None, 29])
def test_blank_campaign_scope_is_rejected_by_request_and_record(
    campaign_id: str,
    session: int | None,
) -> None:
    with pytest.raises(ValueError, match="campaign_id must not be blank"):
        CreateCombatEncounterRequest(
            title="Invalid campaign scope",
            campaign_id=campaign_id,
            session=session,
        )

    ruleset = rulesets.load_ruleset("generic.manual-tracking")
    now = datetime.now(UTC)
    valid_record = CombatEncounterRecord(
        encounter_id=uuid4(),
        world_id="elderwyld",
        campaign_id="longmont-c2",
        session=session,
        revision=1,
        ruleset=ruleset,
        ruleset_digest=rulesets.ruleset_digest(ruleset),
        draft=_draft("Valid scope"),
        created_at=now,
        updated_at=now,
    )
    payload = valid_record.model_dump()
    payload["campaign_id"] = campaign_id
    with pytest.raises(ValueError, match="campaign_id must not be blank"):
        CombatEncounterRecord.model_validate(payload)


def test_world_id_validation_fails_before_database_access() -> None:
    with pytest.raises(ApplicationStateValidationError, match="canonical managed World"):
        list_encounters(world_id="Elderwyld")


def test_draft_rejects_payload_that_exceeds_storage_limit() -> None:
    from application_state.combat_encounters.types import CombatEntityProvenance

    repeated_provenance = [
        CombatEntityProvenance(
            source="generated_statblock_view",
            artifact_id=f"statblock-{entity_index}-{item_index}",
            corpus_display_path="x" * 1024,
            added_at="2026-10-17T00:00:00Z",
        )
        for entity_index in range(100)
        for item_index in range(16)
    ]
    entities = [
        _entity(f"entity-{index}", f"Creature {index}", index + 1).model_copy(
            update={"provenance": repeated_provenance[:16]}
        )
        for index in range(100)
    ]
    with pytest.raises(ValueError, match="700 KiB storage limit"):
        CombatEncounterDraft(title="Large", entities=entities)


def test_new_world_identity_requires_server_verification(application_state_dsn):
    from application_state.combat_encounters.types import CombatWorldIdentity
    created = create_encounter(world_id="elderwyld", request=CreateCombatEncounterRequest(title="Manual assembly"))
    identity = CombatWorldIdentity(managed_world_id="elderwyld", native_world_id="native-world", binding_version=1,
        graph_revision_id="graph-a", node_id="npc-a", label="Scout", kind="npc", role="npc", campaign_scope=None)
    actor = _entity("scout-a", "Scout", 1).model_copy(update={"world_identity": identity})
    with pytest.raises(ApplicationStateValidationError, match="must be verified"):
        save_encounter(world_id="elderwyld", encounter_id=created.encounter_id,
            request=SaveCombatEncounterRequest(expected_revision=1,draft=CombatEncounterDraft(title="Manual assembly",entities=[actor])))
    assert get_encounter(world_id="elderwyld",encounter_id=created.encounter_id) == created


def test_actor_removal_with_cleaned_pointers_and_groups_saves_and_reopens(application_state_dsn):
    created = create_encounter(world_id="elderwyld", request=CreateCombatEncounterRequest(title="Roster removal"))
    original = CombatEncounterDraft(
        title="Roster removal", round=4,
        entities=[_entity("a", "First", 1), _entity("b", "Second", 2)],
        active_turn_entity_id="a", round_start_entity_id="a",
        groups=[{"group_key":"pair", "label":"Pair", "member_ids":["a","b"], "collapsed":False}],
    )
    baseline = save_encounter(world_id="elderwyld", encounter_id=created.encounter_id,
        request=SaveCombatEncounterRequest(expected_revision=1, draft=original))
    # Omission does not authorize dangling turn or group identities.
    for changes in [
        {"entities":[original.entities[1]]},
        {"entities":[original.entities[1]], "active_turn_entity_id":"b", "round_start_entity_id":None},
    ]:
        with pytest.raises(ValueError):
            CombatEncounterDraft.model_validate({**original.model_dump(), **changes})
    cleaned = original.model_copy(update={
        "entities":[original.entities[1].model_copy(update={"order":1})],
        "active_turn_entity_id":"b", "round_start_entity_id":None,
        "groups":[original.groups[0].model_copy(update={"member_ids":["b"]})],
    })
    saved = save_encounter(world_id="elderwyld", encounter_id=created.encounter_id,
        request=SaveCombatEncounterRequest(expected_revision=baseline.revision, draft=cleaned))
    assert saved.revision == 3 and saved.draft.round == 4
    assert get_encounter(world_id="elderwyld", encounter_id=created.encounter_id) == saved
    assert saved.draft.entities[0] == cleaned.entities[0]
    with pytest.raises(ApplicationStateConflictError):
        save_encounter(world_id="elderwyld", encounter_id=created.encounter_id,
            request=SaveCombatEncounterRequest(expected_revision=baseline.revision, draft=original))
    assert get_encounter(world_id="elderwyld", encounter_id=created.encounter_id) == saved
