from evals.c1s4_preplanning_vertical_slice.analyze_lane_aware_failures import _classify


def test_retrieval_miss_when_no_retrieved_match():
    klass, _ = _classify(mode="prior_only", reasons=[], retrieved=0, candidate=0, admitted=0, rendered=0)
    assert klass == "retrieval_miss"


def test_candidate_present_admission_miss_from_candidate_gap():
    klass, _ = _classify(mode="prior_only", reasons=[], retrieved=2, candidate=0, admitted=0, rendered=0)
    assert klass == "candidate_present_admission_miss"


def test_candidate_present_admission_miss_from_admitted_gap():
    klass, _ = _classify(mode="prior_only", reasons=[], retrieved=2, candidate=1, admitted=0, rendered=0)
    assert klass == "candidate_present_admission_miss"


def test_admitted_not_rendered():
    klass, _ = _classify(mode="prior_only", reasons=[], retrieved=2, candidate=1, admitted=1, rendered=0)
    assert klass == "admitted_not_rendered"


def test_wrong_rendered_section():
    klass, _ = _classify(mode="prior_only", reasons=["wrong_rendered_section"], retrieved=1, candidate=1, admitted=1, rendered=0)
    assert klass == "wrong_rendered_section"


def test_navigation_only_rejected():
    klass, _ = _classify(mode="prior_only", reasons=["navigation_only_context"], retrieved=1, candidate=1, admitted=1, rendered=1)
    assert klass == "navigation_only_rejected"
