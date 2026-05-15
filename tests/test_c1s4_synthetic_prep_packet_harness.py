from __future__ import annotations

import json

from evals.c1s4_preplanning_vertical_slice.step5_build_synthetic_prep_packet import build_summary
from evals.c1s4_preplanning_vertical_slice.synthetic_prep_packet_harness import (
    SECTION_QUESTION_MAP,
    SYNTHETIC_PREP_PACKET_SCHEMA,
    build_synthetic_prep_packet,
    validate_synthetic_prep_packet,
)


def _packet(mode: str = "prior_only") -> dict:
    return build_summary(mode=mode, generator="template_stub")["prep_packet"]


def test_builds_synthetic_prep_packet_from_step4() -> None:
    packet = _packet("prior_only")
    assert packet["schema"] == SYNTHETIC_PREP_PACKET_SCHEMA
    assert packet["sections"]
    assert packet["source_answer_packet_refs"]
    assert packet["does_not_claim_observed_c1s4_match"] is True


def test_q35_remains_skipped_and_absent_from_sections() -> None:
    summary = build_summary(mode="prior_only", generator="template_stub")
    packet = summary["prep_packet"]
    assert any(row["question_number"] == 35 for row in summary["skipped_questions"])
    assert all(35 not in section["question_numbers"] for section in packet["sections"])


def test_required_sections_exist() -> None:
    section_ids = {s["section_id"] for s in _packet()["sections"]}
    assert section_ids == set(SECTION_QUESTION_MAP)


def test_mode_is_preserved() -> None:
    for mode in ["prior_only", "prior_plus_support_content_only", "prior_plus_support_content_plus_lexical_hints"]:
        assert _packet(mode)["retrieval_mode"] == mode


def test_step5_summaries_are_valid_for_all_modes() -> None:
    for mode in ["prior_only", "prior_plus_support_content_only", "prior_plus_support_content_plus_lexical_hints"]:
        summary = build_summary(mode=mode, generator="template_stub")
        assert summary["prep_packet_built"] is True
        assert summary["validation_errors"] == []
        assert summary["counts"]["packets_with_unsupported_forbidden_terms"] == 0


def test_prior_only_and_prior_plus_support_are_not_collapsed() -> None:
    p1 = _packet("prior_only")
    p2 = _packet("prior_plus_support_content_only")
    assert p1["retrieval_mode"] == "prior_only"
    assert p2["retrieval_mode"] == "prior_plus_support_content_only"
    assert p1 != p2


def test_known_gaps_and_guardrails_are_aggregated() -> None:
    packet = _packet("prior_only")
    from_sections_gaps = {g for s in packet["sections"] for g in s["section_known_gaps"]}
    from_sections_guardrails = {g for s in packet["sections"] for g in s["section_guardrails"]}
    assert from_sections_gaps.issubset(set(packet["known_gaps"]))
    assert from_sections_guardrails.issubset(set(packet["must_not_include_unless_sourced"]))


def test_oracle_leakage_rejected() -> None:
    bad = build_synthetic_prep_packet(answer_packets=[{"question_number": 1, "question_id": "q01", "answer_text": "x", "authority_label": "a", "oracle_risk": "high", "known_context_gaps": [], "must_not_include_unless_sourced": [], "safety_checks": {"must_not_include_terms_present": [], "oracle_sensitive_terms_supported_or_absent": True}, "expected_mode_behavior": "x", "oracle_leakage_check": {"forbidden_path_hits": ["bad"], "forbidden_session_hits": []}}], skipped_questions=[{"question_number": 35}], retrieval_mode="prior_only", generator="template_stub")
    assert any("oracle leakage" in e for e in validate_synthetic_prep_packet(bad))


def test_unsupported_forbidden_terms_rejected() -> None:
    bad = build_synthetic_prep_packet(answer_packets=[{"question_number": 1, "question_id": "q01", "answer_text": "x", "authority_label": "a", "oracle_risk": "high", "known_context_gaps": [], "must_not_include_unless_sourced": [], "safety_checks": {"must_not_include_terms_present": [{"term": "foo", "supported": False}], "oracle_sensitive_terms_supported_or_absent": False}, "expected_mode_behavior": "x", "oracle_leakage_check": {"forbidden_path_hits": [], "forbidden_session_hits": []}}], skipped_questions=[{"question_number": 35}], retrieval_mode="prior_only", generator="template_stub")
    assert any("unsupported forbidden terms" in e for e in validate_synthetic_prep_packet(bad))


def test_no_oracle_grading_claims() -> None:
    dumped = json.dumps(_packet("prior_only"), sort_keys=True)
    for forbidden in ["\"oracle_score\"", "\"passed_oracle_grading\"", "\"matches_c1s4\"", "\"c1s4_recap_match\"", "\"observed_c1s4\":"]:
        assert forbidden not in dumped


def test_section_question_mapping_is_complete_for_planner_questions() -> None:
    packet = _packet("prior_only")
    seen = [entry["question_number"] for s in packet["sections"] for entry in s["prep_entries"]]
    expected = [q for nums in SECTION_QUESTION_MAP.values() for q in nums]
    assert sorted(seen) == sorted(expected)
    assert len(seen) == len(set(seen))
