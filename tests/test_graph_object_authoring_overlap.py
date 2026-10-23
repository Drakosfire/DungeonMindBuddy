"""Current native prepare duplicate guidance only inspects the submitted batch."""
from apps.live_control_server.services.graph_object_authoring_overlap import detect_prepare_overlap_warnings
from tests.test_graph_object_authoring_prepare import object_proposal, prepare_request


def test_batch_duplicates_are_still_visible_without_any_overlay():
    request = prepare_request(proposals=[object_proposal(), object_proposal(localProposalId="second")])
    warnings = detect_prepare_overlap_warnings(request)
    assert warnings and all(row.code == "staged_proposal_possible_duplicate" for row in warnings)


def test_distinct_batch_has_no_overlay_duplicate_claim():
    request = prepare_request(proposals=[object_proposal()])
    assert detect_prepare_overlap_warnings(request) == []
