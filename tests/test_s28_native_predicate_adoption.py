"""Existing native protection survives the real producer and qualification seams."""
import copy
import pytest
from apps.live_control_server.integrations.dungeonmind.assertion_qualification import (
    CURRENT_V5_TARGET, edge_endpoint_kind_admission_reason, resolve_buddy_predicate_mapping_v4,
)
from src.graph_memory.extraction.category_candidate_graph_extractor import consolidate_category_outputs


@pytest.mark.parametrize("other", ["attacks", "threatens"])
@pytest.mark.parametrize("protect_first", [True, False])
def test_real_producer_keeps_protection_and_hostility_distinct(other, protect_first):
    nodes = [{"node_id": "a", "label": "Alina", "node_type": "character", "description": "actor"},
             {"node_id": "b", "label": "Brin", "node_type": "character", "description": "actor"}]
    protect = {"edge_id": "p", "from_node_id": "a", "to_node_id": "b", "relationship_type": "protects", "label": "protects"}
    hostile = {**protect, "edge_id": "h", "relationship_type": other, "label": other}
    reverse = {**protect, "edge_id": "reverse", "from_node_id": "b", "to_node_id": "a"}
    duplicate = {**protect, "edge_id": "repeat"}
    edges = [protect, hostile] if protect_first else [hostile, protect]
    original = copy.deepcopy(edges + [duplicate, reverse])
    result = consolidate_category_outputs({"actor_pass": {"observation_nodes": nodes},
                                         "edge_pass": {"observation_edges": original}},
                                        campaign_id="protects-boundary-test", session=None)
    kept = result["edges"]
    assert len(kept) == 3
    assert {(e["relationship_type"], e["from_node_id"], e["to_node_id"]) for e in kept} == {
        ("protects", "a", "b"), ("protects", "b", "a"), (other, "a", "b")}
    assert next(e for e in kept if e["edge_id"] == "p")["predicate_family"] == "threat_relation"
    assert all("predicate_validation:unknown_relationship_type" not in e.get("warnings", []) for e in kept)
    assert original == edges + [duplicate, reverse]


@pytest.mark.parametrize("actor", ["npc", "pc"])
@pytest.mark.parametrize("target", ["npc", "pc", "location", "item"])
def test_existing_native_protects_transport_admits_actor_direction(actor, target):
    assert resolve_buddy_predicate_mapping_v4("protects") == ("dnd5e:protects", False)
    assert edge_endpoint_kind_admission_reason(buddy_predicate="protects", from_buddy_kind=actor,
        to_buddy_kind=target, vocabulary=CURRENT_V5_TARGET.world_object_loader()) is None


def test_protection_does_not_invent_predicates_or_accept_wrong_subject_kind():
    assert resolve_buddy_predicate_mapping_v4("defends_weakened_location") is None
    assert resolve_buddy_predicate_mapping_v4("made_up_protects") is None
    assert edge_endpoint_kind_admission_reason(buddy_predicate="protects", from_buddy_kind="item", to_buddy_kind="npc") == "endpoint_kind_not_admitted"
    assert edge_endpoint_kind_admission_reason(buddy_predicate="protects", from_buddy_kind="npc", to_buddy_kind="event") == "endpoint_kind_not_admitted"
