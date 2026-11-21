"""Release-local graph projection is closed and does not copy host metadata."""
import json

import pytest

from apps.live_control_server.services.guest_release_projection import (
    GuestReleaseProjectionError, project_selected_graph,
)
from apps.live_control_server.services import guest_release_projection as adapter
from graph_memory.projection.world_projection import WorldGraphProjection


def _projection():
    return WorldGraphProjection.model_validate({
        "schema": "dmb_world_graph_projection_v1",
        "snapshot": {"world_id": "private-world", "campaign_id": "", "revision_id": "private-revision",
                     "head_revision_id": "private-head", "is_head": False, "focus": {},
                     "admissibility": "player", "scope_mode": "world"},
        "summary": {"node_count": 2, "relationship_count": 1, "attribute_count": 0,
                    "evidence_count": 0, "source_artifact_count": 0},
        "nodes": [{"node_id": "private-node-a", "label": "Sizzek", "kind": "character", "role": "node",
                   "summary": "private summary", "source_artifact_ids": ["private-source"]},
                  {"node_id": "private-node-b", "label": "Carnival", "kind": "place", "role": "node"}],
        "relationships": [{"edge_id": "private-edge", "source_node_id": "private-node-a",
                           "target_node_id": "private-node-b", "predicate": "visits", "label": "visits",
                           "direction": "outgoing"}],
        "trust_boundary": {},
    })


def test_projection_copies_only_selected_closed_fields(monkeypatch):
    monkeypatch.setattr(adapter, "verify_relationship_citation", lambda **_: "release-excerpt")
    result = project_selected_graph(_projection(), expected_world_id="private-world", expected_revision="private-revision",
                                    selected_node_ids={"private-node-a", "private-node-b"},
                                    selected_edge_ids={"private-edge"},
                                    citation_selections={"private-edge": ("evidence", {}, ())}, source_access=object())
    encoded = json.dumps(result)
    assert "private-" not in encoded
    assert len(result["nodes"]) == 2 and len(result["edges"]) == 1
    assert result["edges"][0]["citations"] == ["release-excerpt"]
    assert {result["edges"][0]["source"], result["edges"][0]["target"]} == {n["id"] for n in result["nodes"]}


def test_projection_rejects_open_relationship_and_wrong_revision():
    with pytest.raises(GuestReleaseProjectionError):
        project_selected_graph(_projection(), expected_world_id="private-world", expected_revision="private-revision",
                               selected_node_ids={"private-node-a"}, selected_edge_ids={"private-edge"},
                               citation_selections={"private-edge": ("evidence", {}, ())}, source_access=object())
    with pytest.raises(GuestReleaseProjectionError):
        project_selected_graph(_projection(), expected_world_id="private-world", expected_revision="other",
                               selected_node_ids=set(), selected_edge_ids=set())


def test_projection_rejects_relationship_without_support_selection():
    with pytest.raises(GuestReleaseProjectionError):
        project_selected_graph(_projection(), expected_world_id="private-world", expected_revision="private-revision",
            selected_node_ids={"private-node-a", "private-node-b"}, selected_edge_ids={"private-edge"})


def test_projection_rejects_native_id_fallback_as_a_name():
    projection = _projection()
    projection.nodes[0].label = projection.nodes[0].node_id
    with pytest.raises(GuestReleaseProjectionError):
        project_selected_graph(projection, expected_world_id="private-world", expected_revision="private-revision",
            selected_node_ids={"private-node-a"}, selected_edge_ids=set())


@pytest.mark.parametrize("field", ["node", "edge"])
def test_projection_rejects_private_destinations_in_labels(field):
    projection = _projection()
    if field == "node":
        projection.nodes[0].label = "https://private.example/doc"
    else:
        projection.relationships[0].label = "[secret](/private/doc)"
    with pytest.raises(GuestReleaseProjectionError):
        project_selected_graph(projection, expected_world_id="private-world", expected_revision="private-revision",
            selected_node_ids={"private-node-a", "private-node-b"}, selected_edge_ids={"private-edge"},
            citation_selections={"private-edge": ("evidence", {}, ())}, source_access=object())


def test_projection_rejects_gm_or_truncated_snapshots():
    projection = _projection()
    gm = projection.model_copy(update={"snapshot": projection.snapshot.model_copy(update={"admissibility": "gm"})})
    truncated = projection.model_copy(update={"summary": projection.summary.model_copy(update={"projection_truncated": True})})
    for invalid in (gm, truncated):
        with pytest.raises(GuestReleaseProjectionError):
            project_selected_graph(invalid, expected_world_id="private-world", expected_revision="private-revision",
                                   selected_node_ids=set(), selected_edge_ids=set())
