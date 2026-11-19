"""Private record/version invariants without persistence or provider execution."""

import copy
import hashlib
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from application_state.combat_encounters.manual_encounters import (
    ManualEncounterDraft, ManualEncounterRecord, ManualParticipant,
    OrderedRoundTurn, OrderedTurn, SideTurn, SpotlightTurn, decode_combat_record, empty_manual_draft,
)
from application_state.combat_encounters.manual_profiles import (
    ManualCombatProfile, initial_actor_values, manual_profile_digest,
)
from application_state.combat_encounters.types import (
    AcceptedCombatMechanicsSnapshot, CombatEncounterRecord, CombatMechanicsSnapshot,
    ConversationVariantCombatSnapshot, SavedCombatMechanicsSnapshot,
)

FIXTURES = Path(__file__).parent / "fixtures"
WORLD = "crossing-world"
UUID = "11111111-1111-4111-8111-111111111111"


def spotlight_record():
    body=record().model_dump(mode='json',by_alias=True)
    body['ruleset']['pacing']={'mode':'spotlight','rounds':False}
    rules=ManualCombatProfile.model_validate(body['ruleset'])
    body['ruleset_digest']=manual_profile_digest(rules)
    body['draft']['turn']={'kind':'spotlight','active_actor_id':'crew-a'}
    return decode_combat_record(body)


def test_spotlight_is_explicit_without_an_order_side_or_round_and_resets_only_selection():
    from application_state.play.session_encounters import initialize_draft
    current=spotlight_record();before=current.model_dump(mode='json',by_alias=True)
    assert isinstance(empty_manual_draft(current.ruleset,'New').turn,SpotlightTurn)
    assert current.draft.sides==[]
    current.draft.entities[0].notes='Keep this note'
    current.draft.entities[0].statuses=('Exposed',)
    live,actor_map,_=initialize_draft(current,fresh_ids=True)
    assert live.turn==SpotlightTurn()
    assert live.entities[0].id==actor_map['crew-a']!='crew-a'
    assert live.entities[0].values==current.draft.entities[0].values
    assert live.entities[0].notes=='Keep this note' and live.entities[0].statuses==('Exposed',)
    assert current.draft.turn.active_actor_id==before['draft']['turn']['active_actor_id']


@pytest.mark.parametrize('turn',[
    {'kind':'ordered','active_actor_id':None},
    {'kind':'side','active_side_id':None,'active_actor_id':None,'acted_actor_ids':[]},
    {'kind':'spotlight','active_actor_id':'missing'},
    {'kind':'spotlight','active_actor_id':'crew-a','round':1},
    {'kind':'spotlight','active_actor_id':None,'acted_actor_ids':[]},
])
def test_spotlight_refuses_mismatched_modes_stale_references_and_invented_round_state(turn):
    body=spotlight_record().model_dump(mode='json',by_alias=True);body['draft']['turn']=turn
    with pytest.raises(ValidationError):decode_combat_record(body)


def test_out_of_action_cannot_retain_an_active_spotlight():
    body=spotlight_record().model_dump(mode='json',by_alias=True)
    body['draft']['entities'][0]['participation']='out_of_action'
    with pytest.raises(ValidationError,match='in-action'):decode_combat_record(body)
    body['draft']['turn']['active_actor_id']=None
    assert decode_combat_record(body).draft.entities[0].values.resources['stress'].current==2


@pytest.mark.parametrize('rounds',[True,0,'false',None])
def test_spotlight_never_coerces_rounds_or_invents_a_counter(rounds):
    body=spotlight_record().ruleset.model_dump(mode='json',by_alias=True);body['pacing']['rounds']=rounds
    with pytest.raises(ValidationError):ManualCombatProfile.model_validate(body)


def side_record():
    body = record().model_dump(mode="json", by_alias=True)
    body["ruleset"]["pacing"] = {"mode": "side", "rounds": False}
    rules = ManualCombatProfile.model_validate(body["ruleset"])
    body["ruleset_digest"] = manual_profile_digest(rules)
    body["draft"]["sides"] = [{"id": "crew", "label": "Crew"}, {"id": "river", "label": "River"}]
    body["draft"]["entities"][0]["side_id"] = "crew"
    body["draft"]["turn"] = {"kind": "side", "active_side_id": "crew", "active_actor_id": None, "acted_actor_ids": ["crew-a"]}
    return decode_combat_record(body)


def test_existing_ordered_creation_input_retains_its_default_mode_and_preimage():
    old=profile().model_dump(mode="json",by_alias=True)
    without_mode=copy.deepcopy(old)
    del without_mode['pacing']['mode']
    assert ManualCombatProfile.model_validate(without_mode).model_dump(mode="json",by_alias=True)==old


def test_side_profile_keeps_explicit_turn_markers_and_initializes_fresh_phase():
    from application_state.play.session_encounters import initialize_draft
    current = side_record()
    current.draft.entities[0].participation = "out_of_action"
    current = decode_combat_record(current.model_dump(mode="json", by_alias=True))
    assert isinstance(empty_manual_draft(current.ruleset, "New").turn, SideTurn)
    assert not current.ruleset.pacing.rounds
    assert current.draft.turn.acted_actor_ids == ("crew-a",)
    before = current.model_dump(mode="json", by_alias=True)
    live, actor_map, _ = initialize_draft(current, fresh_ids=True)
    assert live.turn == SideTurn()
    assert live.entities[0].id == actor_map["crew-a"] != "crew-a"
    assert live.entities[0].side_id == live.sides[0].id != "crew"
    assert live.entities[0].values == current.draft.entities[0].values
    assert live.entities[0].participation == "out_of_action"
    assert current.model_dump(mode="json", by_alias=True) == before


@pytest.mark.parametrize("patch", [
    {"active_side_id": "missing"},
    {"active_side_id": None},
    {"active_side_id": "river"},
    {"active_actor_id": "crew-a"},
    {"acted_actor_ids": ["crew-a", "crew-a"]},
    {"acted_actor_ids": ["missing"]},
    {"kind": "ordered"},
])
def test_side_turn_rejects_foreign_duplicate_mismatched_and_simultaneous_references(patch):
    body = side_record().model_dump(mode="json", by_alias=True)
    body["draft"]["turn"].update(patch)
    with pytest.raises(ValidationError):
        decode_combat_record(body)


@pytest.mark.parametrize("rounds", [True, 0, "false", None])
def test_side_profile_never_coerces_rounds_or_claims_a_round_counter(rounds):
    body = side_record().ruleset.model_dump(mode="json", by_alias=True)
    body["pacing"]["rounds"] = rounds
    with pytest.raises(ValidationError):
        ManualCombatProfile.model_validate(body)


def test_manual_scene_create_retains_exact_non_alias_digest_preimage():
    from application_state.combat_encounters.scene_template_types import CreateSceneTemplateRequest
    fixture=json.loads((FIXTURES/'combat/manual-scene-create-v2.json').read_text())
    normalized=dict(world_id=fixture['world_id'],request=CreateSceneTemplateRequest.model_validate(fixture['intent']).model_dump(mode='json'))
    assert normalized==fixture['normalized']
    assert normalized['request']['encounter']['profile']['schema_']=='dmb_combat_profile_v2'
    canonical=json.dumps(normalized,ensure_ascii=False,sort_keys=True,separators=(',',':'))
    assert 'sha256:'+hashlib.sha256(canonical.encode()).hexdigest()==fixture['digest']


def profile(rounds=False):
    return ManualCombatProfile(profile_id="crossing", name="Crossing under pressure", system_id="synthetic-crossing",
        stats=[{"field_id": "position", "label": "Position", "value_type": "text", "initial": "Exposed"}],
        resources=[{"field_id": "stress", "label": "Stress", "initial": {"current": 2, "minimum": 0, "maximum": 6}}],
        pacing={"mode": "ordered", "rounds": rounds})


def participant(actor_id="crew-a", **changes):
    return ManualParticipant(id=actor_id, name=actor_id, values=initial_actor_values(profile()), **changes)


def record(rounds=False, **changes):
    rules = profile(rounds)
    draft = empty_manual_draft(rules, "Crossing")
    draft.entities = [participant()]
    return ManualEncounterRecord(encounter_id=UUID, world_id=WORLD, revision=1, ruleset=rules,
        ruleset_digest=manual_profile_digest(rules), draft=draft,
        created_at="2026-11-18T00:00:00Z", updated_at="2026-11-18T00:00:00Z", **changes)


def identity(world=WORLD, node="creature:bridge"):
    return {"managed_world_id": world, "native_world_id": "native-crossing", "binding_version": 1,
        "graph_revision_id": "revision-1", "node_id": node, "label": "Bridge creature", "kind": "Creature",
        "role": "creature", "campaign_scope": None}


@pytest.mark.parametrize("rounds", [False, True])
def test_manual_run_initialization_preserves_preparation_and_mints_references(rounds):
    from application_state.play.session_encounters import initialize_draft
    from application_state.combat_encounters.manual_encounters import ManualGroup, ManualSide
    prepared = record(rounds)
    actor = prepared.draft.entities[0]
    actor.side_id = "crew-side"
    actor.notes = "Carry this tactical note"
    actor.statuses = ("Pinned",)
    actor.participation = "out_of_action"
    actor.values.resources["stress"] = actor.values.resources["stress"].model_copy(update={"current": 0})
    prepared.draft.sides = [ManualSide(id="crew-side", label="Crew")]
    prepared.draft.groups = [ManualGroup(id="crew-group", label="Bridge crew", member_ids=[actor.id])]
    original = prepared.model_dump(mode="json", by_alias=True)
    preview, preview_map, changes = initialize_draft(prepared)
    live, actor_map, _ = initialize_draft(prepared, fresh_ids=True)
    assert preview_map == {actor.id: actor.id}
    assert changes[0]["values"]["resources"]["stress"]["current"] == 0
    assert live.entities[0].id == actor_map[actor.id] != actor.id
    assert live.entities[0].side_id == live.sides[0].id != "crew-side"
    assert live.groups[0].id != "crew-group"
    assert live.groups[0].member_ids == (actor_map[actor.id],)
    assert live.entities[0].values == actor.values
    assert live.entities[0].participation == "out_of_action"
    assert live.entities[0].statuses == ("Pinned",)
    assert live.entities[0].notes == actor.notes
    assert live.turn.active_actor_id is None
    assert prepared.model_dump(mode="json", by_alias=True) == original
    live.entities[0].values.stats["position"] = "Covered"
    assert actor.values.stats["position"] == "Exposed"


def source(kind="associated", world=WORLD):
    resource = json.loads((FIXTURES / "statblocks/v1/exact-revision-response.json").read_text())
    locator = {"provider": "dungeonmind", **{key: resource[key] for key in (
        "statblock_id", "revision_id", "contract", "contract_version", "definition_digest")}}
    payload = {"locator": locator, "resource": resource}
    if kind == "associated":
        model = CombatMechanicsSnapshot
        payload.update(association_id=UUID, association_version=1, target=identity(world))
    elif kind == "accepted":
        model = AcceptedCombatMechanicsSnapshot
        payload.update(origin="world_accepted_mechanics_v1", managed_world_id=world, draft_id=UUID, draft_version=1,
            acceptance_operation_id="accept", acceptance_request_digest="sha256:" + "a" * 64,
            accepted_from_draft_version=1, accepted_from_candidate_id=None)
    elif kind == "saved":
        model = SavedCombatMechanicsSnapshot
        payload.update(origin="buddy_saved_mechanics_override_v1", managed_world_id=world, draft_id=UUID,
            origin_acceptance_operation_id="accept", revision_operation_id=None)
    else:
        model = ConversationVariantCombatSnapshot
        payload.update(origin="conversation_variant_mechanics_v1", managed_world_id=world,
            conversation_id=UUID, turn_id=UUID, review_id=UUID)
    return model.model_validate(payload | {"snapshot_digest": model.digest_payload(payload)})


def test_round_free_manual_record_has_no_dnd_fields_or_fabricated_round_state():
    current = record()
    payload = current.model_dump(mode="json", by_alias=True)
    assert payload["draft"]["turn"] == {"kind": "ordered", "active_actor_id": None}
    actor = payload["draft"]["entities"][0]
    assert actor["values"] == {"stats": {"position": "Exposed"}, "resources": {
        "stress": {"current": 2, "minimum": 0, "maximum": 6}}}
    assert not {"hp", "ac", "init", "temp_hp", "max_hp", "team", "order"}.intersection(actor)
    assert isinstance(decode_combat_record(payload), ManualEncounterRecord)


def test_rounds_enabled_empty_and_active_states_keep_explicit_identity_anchor():
    current = record(True)
    assert isinstance(current.draft.turn, OrderedRoundTurn)
    assert current.draft.turn.round == 1
    payload = current.model_dump(mode="json", by_alias=True)
    payload["draft"]["entities"].append(participant("crew-b", participation="out_of_action").model_dump(mode="json"))
    payload["draft"]["turn"].update(active_actor_id="crew-a", round_start_actor_id="crew-b", round=4)
    restored = decode_combat_record(payload)
    assert restored.draft.turn.round == 4
    assert restored.draft.turn.round_start_actor_id == "crew-b"
    assert restored.draft.entities[1].participation == "out_of_action"
    assert restored.draft.entities[1].values.resources["stress"].current == 2
    assert isinstance(empty_manual_draft(profile(), "Empty").turn, OrderedTurn)
    assert empty_manual_draft(profile(True), "Empty").entities == []


@pytest.mark.parametrize("turn", [
    {"kind": "spotlight"}, {"kind": "sides"}, {"active_actor_id": None},
    {"kind": "ordered", "round": 1}, {"kind": "ordered", "round_start_actor_id": "crew-a"},
    {"kind": "ordered", "active_actor_id": "missing"},
    {"kind": "ordered_rounds", "round": True},
    {"kind": "ordered_rounds", "round": 0}, {"kind": "ordered_rounds", "round": 10000},
    {"kind": "ordered_rounds", "round_start_actor_id": "missing"},
])
def test_incomplete_modes_and_invalid_turn_states_refuse(turn):
    payload = record().model_dump(mode="json", by_alias=True)
    payload["draft"]["turn"] = turn
    with pytest.raises((ValidationError, ValueError)):
        decode_combat_record(payload)


@pytest.mark.parametrize("rounds", [False, True])
def test_profile_and_turn_round_capability_must_agree(rounds):
    payload = record(rounds).model_dump(mode="json", by_alias=True)
    payload["draft"]["turn"] = {"kind": "ordered_rounds" if not rounds else "ordered"}
    with pytest.raises(ValidationError, match="round capability"):
        decode_combat_record(payload)


def test_out_of_action_is_explicit_and_does_not_reset_nonzero_resources_or_notes():
    payload = record().model_dump(mode="json", by_alias=True)
    actor = payload["draft"]["entities"][0]
    actor.update(participation="out_of_action", notes="Retain the clue", statuses=["Marked"])
    parsed = decode_combat_record(payload)
    assert parsed.draft.entities[0].values.resources["stress"].current == 2
    assert parsed.draft.entities[0].notes == "Retain the clue"
    payload["draft"]["turn"]["active_actor_id"] = actor["id"]
    with pytest.raises(ValidationError, match="in-action"):
        decode_combat_record(payload)


def test_arbitrary_sides_and_noncontiguous_groups_have_independent_resolving_membership():
    payload = record().model_dump(mode="json", by_alias=True)
    payload["draft"]["entities"].extend([participant("storm").model_dump(mode="json"), participant("crew-b").model_dump(mode="json")])
    payload["draft"]["sides"] = [{"id": "survey", "label": "Survey crew"}, {"id": "weather", "label": "Storm"}]
    for actor in payload["draft"]["entities"]:
        actor["side_id"] = "weather" if actor["id"] == "storm" else "survey"
    payload["draft"]["groups"] = [{"id": "crew", "label": "Crew", "member_ids": ["crew-a", "crew-b"], "collapsed": True}]
    parsed = decode_combat_record(payload)
    assert [actor.id for actor in parsed.draft.entities] == ["crew-a", "storm", "crew-b"]
    assert parsed.draft.groups[0].member_ids == ("crew-a", "crew-b")


@pytest.mark.parametrize("mutation", ["duplicate-actor", "duplicate-side", "unknown-side", "duplicate-group", "foreign-member", "duplicate-member", "two-groups", "duplicate-status"])
def test_duplicate_and_foreign_references_refuse(mutation):
    payload = record().model_dump(mode="json", by_alias=True)
    draft = payload["draft"]
    group = {"id": "crew", "label": "Crew", "member_ids": ["crew-a"]}
    if mutation == "duplicate-actor": draft["entities"].append(copy.deepcopy(draft["entities"][0]))
    elif mutation == "duplicate-side": draft["sides"] = [{"id": "s", "label": "S"}] * 2
    elif mutation == "unknown-side": draft["entities"][0]["side_id"] = "missing"
    elif mutation == "duplicate-status": draft["entities"][0]["statuses"] = ["Marked", "Marked"]
    elif mutation == "duplicate-group": draft["groups"] = [group, copy.deepcopy(group)]
    elif mutation == "foreign-member": draft["groups"] = [group | {"member_ids": ["missing"]}]
    elif mutation == "duplicate-member": draft["groups"] = [group | {"member_ids": ["crew-a", "crew-a"]}]
    else: draft["groups"] = [group, group | {"id": "another"}]
    with pytest.raises(ValidationError): decode_combat_record(payload)


@pytest.mark.parametrize("kind", ["associated", "accepted", "saved", "conversation"])
def test_exact_source_is_a_reference_not_a_mapping_to_manual_tracker_values(kind):
    snapshot = source(kind)
    before = snapshot.model_dump(mode="json")
    payload = record().model_dump(mode="json", by_alias=True)
    payload["draft"]["entities"][0].update(mechanics_snapshot=before,
        world_identity=identity() if kind == "associated" else None)
    parsed = decode_combat_record(payload)
    actor = parsed.draft.entities[0]
    assert actor.mechanics_snapshot.model_dump(mode="json") == before
    assert actor.values.stats == {"position": "Exposed"}
    assert actor.values.resources["stress"].current == 2
    assert snapshot.model_dump(mode="json") == before


@pytest.mark.parametrize("kind", ["associated", "accepted", "saved", "conversation"])
def test_all_exact_source_origins_refuse_cross_world_references(kind):
    snapshot = source(kind, "other-world")
    payload = record().model_dump(mode="json", by_alias=True)
    payload["draft"]["entities"][0].update(mechanics_snapshot=snapshot.model_dump(mode="json"),
        world_identity=identity("other-world") if kind == "associated" else None)
    with pytest.raises(ValidationError, match="another World"):
        decode_combat_record(payload)


def test_associated_and_conversation_sources_keep_their_own_identity_contracts():
    with pytest.raises(ValidationError, match="exact World identity"):
        participant(world_identity=identity(node="different"), mechanics_snapshot=source())
    with pytest.raises(ValidationError, match="cannot claim"):
        participant(world_identity=identity(), mechanics_snapshot=source("conversation"))
    payload = record().model_dump(mode="json", by_alias=True)
    payload["draft"]["entities"][0]["world_identity"] = identity("other-world")
    with pytest.raises(ValidationError, match="another World"):
        decode_combat_record(payload)


def test_reference_model_instances_are_revalidated_after_nested_resource_tampering():
    snapshot = source()
    snapshot.resource["definition"]["identity"]["name"] = "Tampered"
    with pytest.raises(ValidationError):
        participant(world_identity=identity(), mechanics_snapshot=snapshot)


def test_raw_source_mappings_are_independent_for_each_actor_and_the_caller():
    shared = source().model_dump(mode="json")
    before = copy.deepcopy(shared)
    first = participant("crew-a", world_identity=identity(), mechanics_snapshot=shared)
    second = participant("crew-b", world_identity=identity(), mechanics_snapshot=shared)
    assert first.mechanics_snapshot.resource["definition"] is not second.mechanics_snapshot.resource["definition"]
    first.mechanics_snapshot.resource["definition"]["identity"]["name"] = "Changed only in the first object"
    assert second.mechanics_snapshot.resource == before["resource"]
    assert shared == before


def test_an_active_round_requires_an_explicit_existing_anchor():
    payload = record(True).model_dump(mode="json", by_alias=True)
    payload["draft"]["turn"]["active_actor_id"] = "crew-a"
    with pytest.raises(ValidationError, match="anchor"):
        decode_combat_record(payload)


def test_copies_keep_independent_values_and_source_objects_and_revalidation_detects_tampering():
    snapshot = source()
    shared_values = initial_actor_values(profile())
    first = ManualParticipant(id="crew-a", name="A", values=shared_values,
        world_identity=identity(), mechanics_snapshot=snapshot)
    second = ManualParticipant(id="crew-b", name="B", values=shared_values,
        world_identity=identity(), mechanics_snapshot=snapshot)
    payload = record().model_dump(mode="json", by_alias=True)
    payload["draft"]["entities"] = [first, second]
    parsed = ManualEncounterRecord.model_validate(payload)
    left, right = parsed.draft.entities
    left.values.stats["position"] = "Hidden"
    assert right.values.stats["position"] == shared_values.stats["position"] == "Exposed"
    left.mechanics_snapshot.resource["definition"]["identity"]["name"] = "Tampered"
    assert right.mechanics_snapshot.resource == snapshot.resource
    with pytest.raises(ValidationError): ManualEncounterRecord.model_validate(parsed)


@pytest.mark.parametrize("mutation", ["digest", "values", "session", "world", "revision", "naive-time"])
def test_record_profile_metadata_and_actor_values_are_validated(mutation):
    payload = record().model_dump(mode="json", by_alias=True)
    if mutation == "digest": payload["ruleset_digest"] = "0" * 64
    elif mutation == "values": payload["draft"]["entities"][0]["values"]["stats"]["position"] = 12
    elif mutation == "session": payload["session"] = 1
    elif mutation == "world": payload["world_id"] = "Bad World"
    elif mutation == "revision": payload["revision"] = True
    else: payload["created_at"] = "2026-11-18T00:00:00"
    with pytest.raises((ValidationError, ValueError)): decode_combat_record(payload)


def test_legacy_api_and_template_aliases_and_digest_preimages_dispatch_without_normalization():
    fixture = json.loads((FIXTURES / "combat/manual-profile-v1-compat.json").read_text())
    for key, alias in [("api", True), ("template", False)]:
        payload = copy.deepcopy(fixture[key])
        parsed = decode_combat_record(payload)
        assert type(parsed) is CombatEncounterRecord
        assert parsed.model_dump(mode="json", by_alias=alias) == fixture[key]
        assert payload == fixture[key]
        body = json.dumps(parsed.model_dump(mode="json", by_alias=alias), sort_keys=True,
            ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode()
        assert "sha256:" + hashlib.sha256(body).hexdigest() == fixture[f"{key}_digest"]


@pytest.mark.parametrize("mutation", ["unknown", "mixed", "missing", "ambiguous", "nonobject"])
def test_dispatch_refuses_unknown_mixed_missing_and_ambiguous_versions_without_mutation(mutation):
    payload = record().model_dump(mode="json", by_alias=True)
    if mutation == "unknown": payload["draft"]["schema"] = "future"
    elif mutation == "mixed": payload["draft"]["schema"] = "dmb_combat_encounter_draft_v1"
    elif mutation == "missing": del payload["ruleset"]["schema"]
    elif mutation == "ambiguous": payload["draft"]["schema_"] = payload["draft"]["schema"]
    else: payload["ruleset"] = []
    before = copy.deepcopy(payload)
    with pytest.raises(ValueError): decode_combat_record(payload)
    assert payload == before


def test_manual_aliases_round_trip_and_unvalidated_mutations_do_not_bypass_record_validation():
    current = record()
    named_payload = current.model_dump(mode="json")
    assert decode_combat_record(named_payload).model_dump(mode="json") == named_payload
    current.draft.entities[0].values.stats["position"] = True
    with pytest.raises(ValidationError): ManualEncounterRecord.model_validate(current)


def test_draft_utf8_budget_is_explicit_and_validation_does_not_mutate_the_input():
    actor = participant().model_dump(mode="json") | {"notes": "界" * 4096}
    payload = {"title": "Large", "entities": [actor | {"id": f"crew-{i}"} for i in range(100)]}
    before = copy.deepcopy(payload)
    with pytest.raises(ValidationError, match="700 KiB"):
        ManualEncounterDraft.model_validate(payload)
    assert payload == before
