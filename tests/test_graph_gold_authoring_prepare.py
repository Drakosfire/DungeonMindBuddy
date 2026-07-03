from pathlib import Path

import pytest

from apps.live_control_server.services.graph_gold_authoring_prepare import (
    GraphGoldAuthoringPrepareRequest,
    prepare_graph_gold_authoring_preview,
)
from apps.live_control_server.services.graph_gold_review import GraphGoldReviewError
from evals.graph_memory_layer.session_1_candidate_graph_gold_fixture import gold_graph_path


def base_request(proposals):
    return GraphGoldAuthoringPrepareRequest(campaign_id="longmont-c1", session_id="session-1", proposals=proposals)


def node_span(**overrides):
    data = {"proposal_id":"local-1","proposal_type":"node_from_span","created_at_iso":"2026-07-03T00:00:00Z","status":"accepted_local","lane_role":"live","source_text":"Tripod Null-Calf","source_offsets":{"start":1,"end":17},"suggested_label":"Tripod Null-Calf","suggested_kind":None}
    data.update(overrides); return data


def node_assert(**overrides):
    data = {"proposal_id":"local-2","proposal_type":"node_assertion","created_at_iso":"2026-07-03T00:00:00Z","status":"accepted_local","lane_role":"live","node_id":"n1","label":"North Gate","kind":"location","role":None}
    data.update(overrides); return data


def relationship(**overrides):
    data = {"proposal_id":"local-3","proposal_type":"relationship_assertion","created_at_iso":"2026-07-03T00:00:00Z","status":"accepted_local","lane_role":"live","source_node":{"lane_role":"live","node_id":"n1","label":"Tripod Null-Calf"},"target_node":{"lane_role":"live","node_id":"n2","label":"North Gate"},"predicate":"threatens"}
    data.update(overrides); return data


def link_intent(**overrides):
    data = {"proposal_id":"local-4","proposal_type":"existing_object_link_intent","created_at_iso":"2026-07-03T00:00:00Z","status":"accepted_local","selected_node":{"lane_role":"live","node_id":"n1","label":"Tripod Null-Calf"},"candidate":{"candidate_id":"g1","label":"Tripod Null-Calf","source":"gold_fixture","confidence":"high","score":0.95}}
    data.update(overrides); return data


def prepare(proposals):
    return prepare_graph_gold_authoring_preview(base_request(proposals))


def test_empty_proposals_blocked_and_write_false():
    response = prepare([])
    assert response.validation_status == "blocked"
    assert response.write_performed is False
    assert response.blocking_errors


def test_accepted_node_from_span_returns_add_node():
    response = prepare([node_span()])
    assert response.validation_status == "ready"
    assert response.write_performed is False
    assert response.proposed_operations[0].operation_type == "add_node"


def test_node_from_span_null_offsets_warns_not_blocked():
    response = prepare([node_span(source_offsets=None)])
    assert response.validation_status == "ready_with_warnings"
    assert any(w.code == "unanchored_source" for w in response.warnings)


def test_live_node_assertion_requires_manual_review():
    op = prepare([node_assert()]).proposed_operations[0]
    assert op.operation_type == "assert_node"
    assert op.requires_manual_review is True
    assert any(d.code == "live_lane_manual_review" for d in op.diagnostics)


def test_relationship_returns_add_edge():
    op = prepare([relationship()]).proposed_operations[0]
    assert op.operation_type == "add_edge"


def test_mixed_lane_relationship_manual_warning():
    response = prepare([relationship(lane_role="mixed", target_node={"lane_role":"gold","node_id":"n2","label":"North Gate"})])
    assert response.validation_status == "ready_with_warnings"
    assert response.proposed_operations[0].requires_manual_review is True


def test_self_relationship_blocked():
    response = prepare([relationship(target_node={"lane_role":"live","node_id":"n1","label":"Tripod Null-Calf"})])
    assert response.validation_status == "blocked"
    assert response.proposed_operations[0].operation_type == "blocked"


def test_unknown_predicate_blocked():
    response = prepare([relationship(predicate="canonizes")])
    assert response.validation_status == "blocked"
    assert any(e.code == "unknown_predicate" for e in response.blocking_errors)


def test_existing_object_link_intent_preview_not_completed_link():
    op = prepare([link_intent()]).proposed_operations[0]
    assert op.operation_type == "link_existing_intent"
    assert op.requires_manual_review is True


def test_staged_proposal_ignored_and_warned():
    response = prepare([node_span(status="staged")])
    assert response.validation_status == "blocked"
    assert response.proposed_operations[0].operation_type == "ignored"
    assert any(w.code == "proposal_staged" for w in response.warnings)


def test_rejected_proposal_ignored():
    response = prepare([node_span(status="rejected_local")])
    assert response.proposal_counts.ignored == 1
    assert response.proposed_operations == []


def test_fixture_file_bytes_unchanged_after_prepare():
    path = Path(gold_graph_path())
    before = path.read_bytes()
    response = prepare([node_span(), relationship(), link_intent()])
    assert response.write_performed is False
    assert path.read_bytes() == before


def test_unsupported_campaign_session_raises_clear_422():
    request = GraphGoldAuthoringPrepareRequest(campaign_id="wrong", session_id="session-1", proposals=[])
    with pytest.raises(GraphGoldReviewError) as exc:
        prepare_graph_gold_authoring_preview(request)
    assert exc.value.status_code == 422


def test_response_always_includes_write_performed_false():
    assert prepare([relationship()]).model_dump(mode="json")["write_performed"] is False
