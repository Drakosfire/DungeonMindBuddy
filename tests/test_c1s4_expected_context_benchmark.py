from evals.c1s4_preplanning_vertical_slice.expected_context_benchmark import (
    EXPECTED_CONTEXT_REPORT_SCHEMA,
    build_expected_context_report,
    build_multimode_expected_context_report,
    grade_question_packet,
    load_expected_context_gold,
    match_context_group,
    validate_expected_context_gold,
    validate_expected_context_report,
)
from evals.c1s4_preplanning_vertical_slice.step2_build_question_context_packets import build_summary
from evals.c1s4_preplanning_vertical_slice.step2c_expected_context_benchmark import _assert_no_retrieved_context_leakage


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
    packet = {"question_number": 999, "question_id": "q999", "retrieved_context": [], "known_context_gaps": [], "authority_summary": {}}
    gq = {"expectations_by_mode": {"prior_only": {"required_context_groups": [{"group_id": "x", "match": {"text_contains_any": ["token"]}}], "forbidden_context_groups": [], "expected_known_gaps_contains_any": []}}}
    row = grade_question_packet(packet=packet, gold_question=gq, retrieval_mode="prior_only", top_k=9)
    assert row["ok"] is False
    assert "missing_required_context_group" in row["violations"]


def test_required_context_group_hit_passes_row():
    packet = {"question_number": 999, "question_id": "q999", "retrieved_context": [{"unit_id": "u1", "text": "Hempholm metallic tree"}], "known_context_gaps": [], "authority_summary": {}}
    gq = {"expectations_by_mode": {"prior_only": {"required_context_groups": [{"group_id": "x", "match": {"text_contains_any": ["metallic tree"]}}], "forbidden_context_groups": [], "expected_known_gaps_contains_any": []}}}
    row = grade_question_packet(packet=packet, gold_question=gq, retrieval_mode="prior_only", top_k=9)
    assert row["ok"] is True
    assert row["retrieved_context_preview"][0]["rank"] == 1
    assert row["retrieved_context_preview"][0]["matched_required_groups"] == ["x"]


def test_retrieved_context_preview_includes_planner_visible_fields():
    packet = {
        "question_number": 1,
        "question_id": "q01",
        "retrieved_context": [
            {
                "unit_id": "u-1",
                "source_kind": "support_knowledge_card",
                "source_layer": "source_module",
                "title": "Hempholm",
                "snippet": "metal leaves on a tree",
                "source_reference": {"document": "Of Conks & Cons"},
            }
        ],
        "known_context_gaps": [],
        "authority_summary": {},
    }
    gq = {"expectations_by_mode": {"prior_plus_support_content_only": {"required_context_groups": [], "forbidden_context_groups": [], "expected_known_gaps_contains_any": []}}}
    row = grade_question_packet(packet=packet, gold_question=gq, retrieval_mode="prior_plus_support_content_only", top_k=9)
    preview = row["retrieved_context_preview"][0]
    assert preview["ref"] == "u-1"
    assert preview["source_kind"] == "support_knowledge_card"
    assert "Of Conks & Cons" in preview["source_reference"]


def test_text_contains_any_matches_even_when_text_field_missing():
    packet = {"question_number": 1, "question_id": "q01", "retrieved_context": [{"unit_id": "u1", "snippet": "Ride to StoneBridge with Pippa."}], "known_context_gaps": [], "authority_summary": {}}
    gq = {"expectations_by_mode": {"prior_only": {"required_context_groups": [{"group_id": "g1", "match": {"text_contains_any": ["pippa"]}}], "forbidden_context_groups": [], "expected_known_gaps_contains_any": []}}}
    row = grade_question_packet(packet=packet, gold_question=gq, retrieval_mode="prior_only", top_k=9)
    assert row["required_context_groups_hit"] == 1


def test_depth_diagnostics_report_first_match_beyond_top_k():
    packet_top = {"question_number": 5, "question_id": "q05", "retrieved_context": [{"unit_id": "u1", "source_kind": "session_memory", "snippet": "session"}], "known_context_gaps": [], "authority_summary": {}}
    packet_diag = {"question_number": 5, "question_id": "q05", "retrieved_context": [{"unit_id": "u1", "source_kind": "session_memory", "snippet": "session"}, {"unit_id": "support:hempholm", "source_kind": "support_knowledge_card", "source_layer": "source_module", "snippet": "Hempholm metallic tree"}], "known_context_gaps": [], "authority_summary": {}}
    gold = {
        "schema": "dmb_c1s4_expected_context_gold_v1",
        "campaign_id": "longmont-c1",
        "questions": [
            {"question_number": 5, "question_id": "q05", "expectations_by_mode": {"prior_plus_support_content_only": {"required_context_groups": [{"group_id": "hempholm_tree_visible_threat", "match": {"source_kind": "support_knowledge_card", "text_contains_any": ["Hempholm"]}}], "forbidden_context_groups": [], "expected_known_gaps_contains_any": []}}}
        ],
    }
    report = build_expected_context_report(packets=[packet_top], diagnostic_packets=[packet_diag], gold=gold, retrieval_mode="prior_plus_support_content_only", top_k=1)
    diag = report["results"][0]["retrieval_depth_diagnostics"]["required_groups"]["hempholm_tree_visible_threat"]
    assert diag["matched_at_top_k"] is False
    assert diag["matched_at_top_20"] is True
    assert diag["first_matching_rank"] == 2


def test_known_gap_expectation_is_checked_against_packet_gaps():
    packet = {"question_number": 3, "question_id": "q03", "retrieved_context": [], "known_context_gaps": ["exact Stone Bridge-to-Mirathorn route gazetteer"], "authority_summary": {}}
    gq = {"expectations_by_mode": {"prior_only": {"required_context_groups": [], "forbidden_context_groups": [], "expected_known_gaps_contains_any": ["exact Stone Bridge-to-Mirathorn route gazetteer", "route-specific ecology"]}}}
    row = grade_question_packet(packet=packet, gold_question=gq, retrieval_mode="prior_only", top_k=9)
    assert "missing_expected_known_gap" in row["violations"]
    assert row["known_gap_expectations_hit"] == ["exact Stone Bridge-to-Mirathorn route gazetteer"]


def test_forbidden_context_group_causes_row_violation():
    packet = {"question_number": 5, "question_id": "q05", "retrieved_context": [{"source_kind": "support_knowledge_card", "text": "Hempholm grotesque tree"}], "known_context_gaps": [], "authority_summary": {}}
    gq = {"expectations_by_mode": {"prior_only": {"required_context_groups": [], "forbidden_context_groups": [{"group_id": "forbid", "match": {"source_kind": "support_knowledge_card", "text_contains_any": ["hempholm"]}}], "expected_known_gaps_contains_any": []}}}
    row = grade_question_packet(packet=packet, gold_question=gq, retrieval_mode="prior_only", top_k=9)
    assert row["ok"] is False
    assert "forbidden_context_group_hit" in row["violations"]


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


def test_report_validation_catches_gold_path_leakage():
    report = {
        "schema": "dmb_c1s4_expected_context_benchmark_report_v1",
        "planner_visibility": "forbidden_gold_eval_only",
        "source_packet_schema": "dmb_c1s4_question_context_packet_v1",
        "retrieval_mode": "prior_only",
        "gold_path": "evals/c1s4_preplanning_vertical_slice/gold/c1s4_expected_context_gold.json",
        "results": [{"question_number": 1, "matched_groups": [{"matched_context_refs": ["support:c1s4_beat_question_targets.json"]}]}],
    }
    errs = validate_expected_context_report(report)
    assert any("leakage token" in e for e in errs)


def test_q35_not_benchmarked_as_planner_context():
    gold = load_expected_context_gold()
    report = build_expected_context_report(packets=build_summary(mode="prior_only")["packets"], gold=gold, retrieval_mode="prior_only")
    assert all(row["question_number"] != 35 for row in report["results"])


def test_packet_level_retrieved_context_leakage_is_rejected_even_without_group_match():
    packets = [
        {
            "question_number": 99,
            "question_id": "q99",
            "retrieved_context": [
                {"source_kind": "session_memory", "text": "unrelated"},
                {"source_kind": "session_memory", "source_reference": "tmp/c1s4_beat_question_targets.json"},
            ],
        }
    ]
    try:
        _assert_no_retrieved_context_leakage(packets)
        assert False, "expected leakage RuntimeError"
    except RuntimeError as exc:
        assert "retrieved_context leakage detected" in str(exc)
