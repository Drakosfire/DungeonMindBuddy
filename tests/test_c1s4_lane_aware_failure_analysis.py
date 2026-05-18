from evals.c1s4_preplanning_vertical_slice.analyze_lane_aware_failures import _classify


def test_retrieval_miss_no_candidate_or_matches():
    klass, reason = _classify({"group_id":"x","accepted_matches":[],"rejected_matches":[]}, {"candidate_context":[],"admitted_context":[]}, "prior_only")
    assert klass == "retrieval_miss"


def test_candidate_present_admission_miss():
    klass, _ = _classify({"group_id":"x","accepted_matches":[],"rejected_matches":[]}, {"candidate_context":[{"a":1}],"admitted_context":[]}, "prior_only")
    assert klass == "candidate_present_admission_miss"


def test_admitted_not_rendered_when_accepted_no_provenance():
    klass, _ = _classify({"group_id":"x","accepted_matches":[{"admitted_rank":1}],"rejected_matches":[]}, {"candidate_context":[{}],"admitted_context":[{}],"rendered_context_packet":{"provenance_map":{}}}, "prior_only")
    assert klass == "admitted_not_rendered"


def test_wrong_rendered_section():
    klass, _ = _classify({"group_id":"x","accepted_matches":[],"rejected_matches":[{"reason":"wrong_rendered_section"}]}, {"candidate_context":[],"admitted_context":[]}, "prior_only")
    assert klass == "wrong_rendered_section"


def test_navigation_only_rejected():
    klass, _ = _classify({"group_id":"x","accepted_matches":[],"rejected_matches":[{"reason":"navigation_only_context"}]}, {"candidate_context":[],"admitted_context":[]}, "prior_only")
    assert klass == "navigation_only_rejected"
