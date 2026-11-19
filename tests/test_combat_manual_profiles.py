"""Pure manual-profile invariants; no providers, services or databases."""

import hashlib
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from application_state.combat_encounters.manual_profiles import (
    ManualActorValues,
    ManualCombatProfile,
    ResourceValue,
    adjust_resource,
    canonical_manual_profile,
    initial_actor_values,
    manual_profile_digest,
    validate_actor_values,
)
from application_state.combat_encounters.rulesets import ruleset_digest
from application_state.combat_encounters.types import (
    CombatEncounterRecord,
    CreateCombatEncounterRequest,
    SaveCombatEncounterRequest,
)


def crossing():
    return ManualCombatProfile(
        profile_id="crossing-pressure", name="Crossing under pressure", system_id="synthetic-crossing",
        stats=[
            {"field_id": "position", "label": "Position", "value_type": "text", "initial": "Exposed"},
            {"field_id": "resolve", "label": "Resolve", "value_type": "integer", "initial": 3},
        ],
        resources=[
            {"field_id": "stress", "label": "Stress", "initial": {"current": 0, "minimum": 0, "maximum": 6}},
            {"field_id": "momentum", "label": "Momentum", "initial": {"current": 2, "minimum": 0, "maximum": 4}},
        ],
        pacing={"mode": "ordered", "rounds": False},
    )


def test_synthetic_profile_has_independent_named_stats_and_resources_without_dnd_requirements():
    profile = crossing()
    values = initial_actor_values(profile)
    assert values.stats == {"position": "Exposed", "resolve": 3}
    assert values.resources["stress"] == ResourceValue(current=0, minimum=0, maximum=6)
    assert values.resources["momentum"].current == 2
    assert not profile.pacing.rounds
    assert set(values.model_dump()) == {"stats", "resources"}
    values.stats["resolve"] = None
    values.resources["momentum"] = ResourceValue(current=None)
    assert validate_actor_values(profile, values).stats["resolve"] is None


def test_profile_and_nested_defaults_are_immutable_and_do_not_alias_actor_maps():
    profile = crossing()
    with pytest.raises(ValidationError):
        profile.name = "Changed"
    with pytest.raises(ValidationError):
        profile.stats[0].label = "Changed"
    with pytest.raises(ValidationError):
        profile.resources[0].initial.current = 4
    assert isinstance(profile.stats, tuple) and isinstance(profile.resources, tuple)
    first, second = initial_actor_values(profile), initial_actor_values(profile)
    first.stats["position"] = "Hidden"
    first.resources["stress"] = ResourceValue(current=5, minimum=0, maximum=6)
    assert second.stats["position"] == "Exposed"
    assert second.resources["stress"].current == profile.resources[0].initial.current == 0
    copied = validate_actor_values(profile, second)
    copied.stats["position"] = "Covered"
    assert second.stats["position"] == "Exposed"


@pytest.mark.parametrize("patch", [
    {"schema": "dmb_combat_ruleset_v1"},
    {"pacing": {"mode": "unknown"}},
    {"pacing": {"mode": "sides"}},
    {"pacing": {"rounds": "false"}},
    {"revision": True},
    {"name": "   "},
    {"unknown": 1},
    {"stats": [{"field_id": "bad id", "label": "Bad", "value_type": "text"}]},
    {"stats": [{"field_id": "a", "label": " ", "value_type": "text"}]},
    {"stats": [{"field_id": "a", "label": "A", "value_type": "integer", "initial": "3"}]},
    {"stats": [{"field_id": "a", "label": "A", "value_type": "text", "initial": 3}]},
])
def test_profile_rejects_unknown_versions_modes_and_ambiguous_definitions(patch):
    payload = canonical_manual_profile(crossing()) | patch
    with pytest.raises(ValidationError):
        ManualCombatProfile.model_validate(payload)


def test_duplicate_ids_cannot_rebind_a_stat_to_another_stat_or_resource():
    payload = canonical_manual_profile(crossing())
    payload["stats"].append(dict(payload["stats"][0]))
    with pytest.raises(ValidationError, match="unique"):
        ManualCombatProfile.model_validate(payload)
    payload = canonical_manual_profile(crossing())
    payload["resources"][0]["field_id"] = "position"
    with pytest.raises(ValidationError, match="unique"):
        ManualCombatProfile.model_validate(payload)


@pytest.mark.parametrize("bad", [True, 1.5, float("nan"), float("inf"), 1000000, -1000000, []])
def test_numeric_stats_and_resources_reject_noninteger_or_out_of_range_values(bad):
    values = initial_actor_values(crossing()).model_dump()
    values["stats"]["resolve"] = bad
    with pytest.raises((ValidationError, ValueError)):
        validate_actor_values(crossing(), values)
    with pytest.raises(ValidationError):
        ResourceValue(current=bad)


@pytest.mark.parametrize("mutation", ["missing-stat", "unknown-stat", "missing-resource", "unknown-resource", "wrong-stat-type"])
def test_actor_membership_and_types_match_the_pinned_profile_exactly(mutation):
    values = initial_actor_values(crossing()).model_dump()
    if mutation == "missing-stat":
        del values["stats"]["position"]
    elif mutation == "unknown-stat":
        values["stats"]["armor-class"] = 12
    elif mutation == "missing-resource":
        del values["resources"]["stress"]
    elif mutation == "unknown-resource":
        values["resources"]["hp"] = {"current": 10}
    else:
        values["stats"]["position"] = 3
    with pytest.raises((ValidationError, ValueError)):
        validate_actor_values(crossing(), values)


def test_revalidation_does_not_trust_mutated_actor_maps_or_unvalidated_resources():
    values = initial_actor_values(crossing())
    values.stats["resolve"] = True
    with pytest.raises(ValidationError):
        validate_actor_values(crossing(), values)
    forged = ResourceValue.model_construct(current=True)
    with pytest.raises(ValidationError):
        adjust_resource(forged, "increase", 1)


@pytest.mark.parametrize("current,direction,amount,expected", [
    (3, "increase", 2, 5), (5, "increase", 3, 6), (6, "increase", 1, 6),
    (8, "increase", 2, 8), (8, "decrease", 1, 7), (8, "decrease", 3, 5),
    (1, "decrease", 4, 0), (0, "decrease", 1, 0), (-2, "decrease", 1, -2),
    (-2, "increase", 1, -1), (-2, "increase", 3, 1),
])
def test_adjustment_preserves_direction_and_edited_out_of_range_values(current, direction, amount, expected):
    original = ResourceValue(current=current, minimum=0, maximum=6)
    result = adjust_resource(original, direction, amount)
    assert result.current == expected
    assert (result.minimum, result.maximum) == (0, 6)
    assert original.current == current


@pytest.mark.parametrize("amount", [0, -1, True, 1.5, "1", 1000000])
def test_adjustment_refuses_invalid_amounts_without_mutation(amount):
    value = ResourceValue(current=3)
    with pytest.raises(ValueError, match="amount"):
        adjust_resource(value, "increase", amount)
    assert value.current == 3


def test_unset_overflow_and_incoherent_bounds_are_refused_without_implied_state_changes():
    with pytest.raises(ValueError, match="current value"):
        adjust_resource(ResourceValue(), "increase", 1)
    for value, direction in [(999999, "increase"), (-999999, "decrease")]:
        with pytest.raises(ValueError, match="numeric range"):
            adjust_resource(ResourceValue(current=value), direction, 1)
    with pytest.raises(ValidationError, match="minimum"):
        ResourceValue(current=3, minimum=5, maximum=2)
    with pytest.raises(ValueError, match="direction"):
        adjust_resource(ResourceValue(current=3), "damage", 1)
    assert adjust_resource(ResourceValue(current=-3), "increase", 1).current == -2


def test_canonical_profile_digest_is_deterministic_and_descriptor_order_is_meaningful():
    profile = crossing()
    payload = canonical_manual_profile(profile)
    assert payload["schema"] == "dmb_combat_profile_v2" and "schema_" not in payload
    digest = manual_profile_digest(profile)
    assert len(digest) == 64
    reordered_keys = dict(reversed(list(payload.items())))
    assert manual_profile_digest(ManualCombatProfile.model_validate(reordered_keys)) == digest
    payload["stats"].reverse()
    assert manual_profile_digest(ManualCombatProfile.model_validate(payload)) != digest


def test_utf8_profile_budget_is_enforced_without_changing_legacy_limits():
    fields = [{"field_id": f"field-{i}", "label": "名" * 80, "value_type": "text", "initial": "界" * 256} for i in range(32)]
    with pytest.raises(ValidationError, match="32 KiB"):
        ManualCombatProfile(profile_id="large", name="Large", system_id="manual", stats=fields)


def test_importing_manual_profiles_preserves_retained_v1_aliases_requests_and_digest_preimages():
    fixture = json.loads((Path(__file__).parent / "fixtures/combat/manual-profile-v1-compat.json").read_text())
    record = CombatEncounterRecord.model_validate(fixture["api"])
    assert record.model_dump(mode="json", by_alias=True) == fixture["api"]
    assert record.model_dump(mode="json") == fixture["template"]
    assert ruleset_digest(record.ruleset) == record.ruleset_digest
    for key in ("api", "template"):
        body = json.dumps(fixture[key], sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode()
        assert "sha256:" + hashlib.sha256(body).hexdigest() == fixture[f"{key}_digest"]
    create = CreateCombatEncounterRequest.model_validate(fixture["create_request"])
    assert create.model_dump(mode="json") == fixture["create_request"]
    pending = SaveCombatEncounterRequest.model_validate(fixture["pending_save"])
    assert pending.model_dump(mode="json", by_alias=True) == fixture["pending_save"]


def test_values_require_declared_maps_and_refuse_additional_runtime_fields():
    with pytest.raises(ValidationError):
        ManualActorValues(stats={}, resources={}, defeated=True)
