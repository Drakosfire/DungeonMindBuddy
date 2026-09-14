"""Tests for assertion qualification and predicate/endpoint vocabulary mapping."""

from __future__ import annotations


from apps.live_control_server.integrations.dungeonmind.assertion_qualification import (
    _BUDDY_TO_DM_KIND_V5,
    check_edge_expressible,
    resolve_buddy_predicate_mapping_v4,
)


def test_buddy_to_dm_kind_v5_mappings():
    assert _BUDDY_TO_DM_KIND_V5["pc"] == "dnd5e:player_character"
    assert _BUDDY_TO_DM_KIND_V5["player_character"] == "dnd5e:player_character"
    assert _BUDDY_TO_DM_KIND_V5["character"] == "dnd5e:npc"
    assert _BUDDY_TO_DM_KIND_V5["npc"] == "dnd5e:npc"
    assert _BUDDY_TO_DM_KIND_V5["location"] == "dnd5e:location"
    assert _BUDDY_TO_DM_KIND_V5["item"] == "dnd5e:item"
    assert _BUDDY_TO_DM_KIND_V5["dnd5e:player_character"] == "dnd5e:player_character"
    assert _BUDDY_TO_DM_KIND_V5["dnd5e:npc"] == "dnd5e:npc"


def test_synonym_predicate_mappings():
    assert resolve_buddy_predicate_mapping_v4("part_of_group") == (
        "dnd5e:member_of",
        False,
    )
    assert resolve_buddy_predicate_mapping_v4("coordinates_with") == (
        "dnd5e:cooperates_with",
        False,
    )
    assert resolve_buddy_predicate_mapping_v4("defends_weakened_location") == (
        "dnd5e:protects",
        False,
    )
    assert resolve_buddy_predicate_mapping_v4("reports_to") == ("dnd5e:serves", False)
    assert resolve_buddy_predicate_mapping_v4("west_of") == ("dnd5e:near", False)
    assert resolve_buddy_predicate_mapping_v4("refers_to") == (
        "dnd5e:associated_with",
        False,
    )
    assert resolve_buddy_predicate_mapping_v4("hires") == ("dnd5e:commands", False)
    assert resolve_buddy_predicate_mapping_v4("governs") == ("dnd5e:owns", False)
    assert resolve_buddy_predicate_mapping_v4("attends") == (
        "dnd5e:participates_in",
        False,
    )


def test_reverse_endpoint_predicate_mappings():
    assert resolve_buddy_predicate_mapping_v4("child_of") == ("dnd5e:parent_of", True)
    assert resolve_buddy_predicate_mapping_v4("contained_by") == (
        "dnd5e:contains",
        True,
    )
    assert resolve_buddy_predicate_mapping_v4("caused_by") == ("dnd5e:causes", True)
    assert resolve_buddy_predicate_mapping_v4("belongs_to") == ("dnd5e:owns", True)


def test_intentionally_unresolved_predicates():
    for pred in [
        "same_as",
        "mission_targets",
        "mission_focus",
        "controls_comms_with",
        "reports_threat_in",
        "carries_report_to",
        "uses_statblock",
    ]:
        assert resolve_buddy_predicate_mapping_v4(pred) is None


def test_check_edge_expressible():
    # Valid: character located_in location
    ok, res = check_edge_expressible("located_in", "npc", "location")
    assert ok is True
    assert res == "dnd5e:located_in"

    # Valid: PC attacks threat
    ok, res = check_edge_expressible("attacks", "player_character", "threat")
    assert ok is True
    assert res == "dnd5e:attacks"

    # Valid with reverse endpoints: child_of (npc child_of pc -> parent_of pc -> npc)
    ok, res = check_edge_expressible("child_of", "npc", "player_character")
    assert ok is True
    assert res == "dnd5e:parent_of"

    # Invalid predicate
    ok, reason = check_edge_expressible("same_as", "npc", "npc")
    assert ok is False
    assert reason == "unmapped_predicate"

    # Invalid endpoint kind: works_with between NPC and location
    ok, reason = check_edge_expressible("works_with", "npc", "location")
    assert ok is False
    assert reason == "endpoint_kind_not_admitted"

    # Invalid endpoint kind: attacks from mystery to group
    ok, reason = check_edge_expressible("attacks", "mystery", "group")
    assert ok is False
    assert reason == "endpoint_kind_not_admitted"
