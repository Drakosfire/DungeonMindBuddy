from evals.c1s4_preplanning_vertical_slice.expected_context_benchmark import (
    EXPECTED_CONTEXT_REPORT_SCHEMA,
    build_expected_context_report,
    build_multimode_expected_context_report,
    grade_question_packet,
    load_expected_context_gold,
    match_context_group,
    validate_expected_context_gold,
)
from evals.c1s4_preplanning_vertical_slice.step2_build_question_context_packets import build_summary


def test_expected_context_gold_is_eval_only():
    gold = load_expected_context_gold()
    assert gold["planner_visibility"] == "forbidden"
    assert gold["artifact_role"] == "eval_only_expected_context_gold"
    assert validate_expected_context_gold(gold) == []


def test_step2_packets_do_not_contain_expected_context_gold_fields():
    summary = build_summary(mode="prior_only", question_number=5)
    packet = summary["packets"][0]
    for key in ["expected_retrieval_context_eval_only", "expected_retrieval_modes", "required_context_groups", "forbidden_context_groups", "expectations_by_mode"]:
        assert key not in packet


def test_required_context_group_missing_fails_row():
    packet = {"question_number": 999, "question_id": "q999", "retrieval_mode": "prior_only", "retrieved_context": [], "known_context_gaps": [], "authority_summary": {}}
    gq = {"expectations_by_mode": {"prior_only": {"required_context_groups": [{"group_id": "x", "match": {"text_contains_any": ["token"]}}], "forbidden_context_groups": [], "expected_known_gaps_contains_any": []}}}
    row = grade_question_packet(packet=packet, gold_question=gq, retrieval_mode="prior_only", top_k=9)
    assert row["ok"] is False
    assert "missing_required_context_group" in row["violations"]


def test_required_context_group_hit_passes_row():
    packet = {"question_number": 999, "question_id": "q999", "retrieval_mode": "prior_only", "retrieved_context": [{"unit_id": "u1", "text": "Hempholm metallic tree"}], "known_context_gaps": [], "authority_summary": {}}
    gq = {"expectations_by_mode": {"prior_only": {"required_context_groups": [{"group_id": "x", "match": {"text_contains_any": ["metallic tree"]}}], "forbidden_context_groups": [], "expected_known_gaps_contains_any": []}}}
    row = grade_question_packet(packet=packet, gold_question=gq, retrieval_mode="prior_only", top_k=9)
    assert row["ok"] is True


def test_all_modes_report_mode_deltas():
    gold = load_expected_context_gold()
    reports = {}
    for mode in ["prior_only", "prior_plus_support_content_only", "prior_plus_support_content_plus_lexical_hints"]:
        reports[mode] = build_expected_context_report(packets=build_summary(mode=mode)["packets"], gold=gold, retrieval_mode=mode)
    mm = build_multimode_expected_context_report(reports_by_mode=reports)
    assert "mode_deltas" in mm


def test_expected_context_benchmark_prior_only_runs():
    gold = load_expected_context_gold()
    report = build_expected_context_report(packets=build_summary(mode="prior_only")["packets"], gold=gold, retrieval_mode="prior_only")
    assert report["retrieval_mode"] == "prior_only"
    assert report["schema"] == EXPECTED_CONTEXT_REPORT_SCHEMA
    assert "results" in report


def test_expected_context_benchmark_support_content_runs():
    gold = load_expected_context_gold()
    report = build_expected_context_report(packets=build_summary(mode="prior_plus_support_content_only")["packets"], gold=gold, retrieval_mode="prior_plus_support_content_only")
    assert report["retrieval_mode"] == "prior_plus_support_content_only"


def test_expected_context_benchmark_lexical_hints_runs():
    gold = load_expected_context_gold()
    report = build_expected_context_report(packets=build_summary(mode="prior_plus_support_content_plus_lexical_hints")["packets"], gold=gold, retrieval_mode="prior_plus_support_content_plus_lexical_hints")
    assert report["retrieval_mode"] == "prior_plus_support_content_plus_lexical_hints"


def test_prior_only_forbidden_support_groups_detected():
    group = {"group_id": "forbid", "match": {"source_kind": "support_knowledge_card", "text_contains_any": ["hempholm"]}}
    res = match_context_group(retrieved_context=[{"source_kind": "support_knowledge_card", "text": "Hempholm tree"}], group=group, top_k=9)
    assert res["ok"] is True
