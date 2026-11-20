import pytest

from graph_memory.predicate_catalog import predicate_family_for_type, prompt_markdown, validate_edge_predicate
from apps.live_control_server.integrations.dungeonmind.assertion_qualification import (
    CURRENT_V5_TARGET, edge_endpoint_kind_admission_reason,
)
from apps.live_control_server.services.recap_semantic_candidate_correction import _plan_edge_tuple_replacements
from apps.live_control_server.services.extract_promote import ExtractPromoteError


def parent():
    return {"nodes": [{"node_id": "event:opening", "node_type": "event"}, {"node_id": "loc:gate", "node_type": "location"}],
            "edges": [{"edge_id": "edge:opening", "from_node_id": "event:opening", "relationship_type": "located_in", "to_node_id": "loc:gate", "label": "Opening occurs at the gate"}]}


def operation(g, predicate="occurred_at", reverse=False):
    old = dict(g["edges"][0])
    old.pop("edge_id")
    new = {**old, "relationship_type": predicate}
    if reverse:
        new["from_node_id"], new["to_node_id"] = new["to_node_id"], new["from_node_id"]
    return {"edge_id": "edge:opening", "expected_tuple": old, "replacement_tuple": new}


def test_catalog_and_prompt_admit_existing_adapter_spelling():
    assert predicate_family_for_type("occurred_at") == "participation"
    assert validate_edge_predicate("occurred_at", "participation") == []
    assert "occurred_at" in prompt_markdown()
    assert validate_edge_predicate("invented_occurrence", None) == ["unknown_relationship_type"]


def test_owning_tuple_planner_accepts_event_location_correction():
    g = parent()
    plans = _plan_edge_tuple_replacements(g, [operation(g)])
    assert plans["edge:opening"]["relationship_type"] == "occurred_at"
    assert g["edges"][0]["relationship_type"] == "located_in"
    assert edge_endpoint_kind_admission_reason(
        buddy_predicate="occurred_at", from_buddy_kind="event", to_buddy_kind="location",
        vocabulary=CURRENT_V5_TARGET.world_object_loader(),
    ) is None


@pytest.mark.parametrize("predicate,reverse", [("occurred_at", True), ("invented_occurrence", False)])
def test_tuple_planner_rejects_inverse_or_unknown_predicate(predicate, reverse):
    g = parent()
    with pytest.raises(ExtractPromoteError):
        _plan_edge_tuple_replacements(g, [operation(g, predicate, reverse)])
