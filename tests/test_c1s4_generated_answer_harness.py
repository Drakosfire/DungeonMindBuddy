from __future__ import annotations

from evals.c1s4_preplanning_vertical_slice.generated_answer_harness import (
    _apply_must_not_include_safety,
    generate_answer_packet,
    validate_generated_answer_packet,
)
from evals.c1s4_preplanning_vertical_slice.step2_build_question_context_packets import build_summary as build_step2_summary
from evals.c1s4_preplanning_vertical_slice.step4_generate_answer_packets import build_summary as build_step4_summary


def _context_packet(mode: str, question_number: int) -> dict:
    summary = build_step2_summary(mode=mode, question_number=question_number)
    return summary["packets"][0]


def test_template_generator_populates_answer_fields() -> None:
    packet = generate_answer_packet(context_packet=_context_packet("prior_only", 5), retrieval_mode="prior_only")
    assert packet["answer_generation_status"] == "generated"
    assert packet["answer_text"]
    assert isinstance(packet["structured_answer"], dict)


def test_generated_answer_packet_does_not_embed_retrieved_context() -> None:
    packet = generate_answer_packet(context_packet=_context_packet("prior_only", 5), retrieval_mode="prior_only")
    assert "retrieved_context" not in packet
    assert "expected_retrieval_context_eval_only" not in packet
    assert "expected_retrieval_modes" not in packet


def test_q35_remains_skipped() -> None:
    summary = build_step4_summary(mode="prior_only")
    assert any(s.get("question_number") == 35 for s in summary["skipped_questions"])
    assert all(p["question_number"] != 35 for p in summary["answer_packets"])


def test_prior_only_support_required_answer_admits_missing_support() -> None:
    packet = generate_answer_packet(context_packet=_context_packet("prior_only", 5), retrieval_mode="prior_only")
    assert "generic" in packet["answer_text"].lower() or "missing support" in packet["answer_text"].lower()
    assert packet["authority_label"] == "support_knowledge_required"
    assert packet["expected_mode_behavior"] == "should_generate_generic_and_admit_missing_support"


def test_prior_plus_support_answer_can_use_support_context() -> None:
    packet = generate_answer_packet(context_packet=_context_packet("prior_plus_support_content_only", 5), retrieval_mode="prior_plus_support_content_only")
    assert packet["used_context_refs"] or packet["authority_notes"]["support_derived_suggestions"]


def test_generated_packet_does_not_copy_gold_known_gaps_from_planner_context() -> None:
    source = _context_packet("prior_only", 5)
    packet = generate_answer_packet(context_packet=source, retrieval_mode="prior_only")
    assert "known_context_gaps" not in source
    assert packet["known_context_gaps"] == []
    assert packet["must_not_include_unless_sourced"] == source["must_not_include_unless_sourced"]


def test_generated_packet_rejects_oracle_leakage() -> None:
    source = _context_packet("prior_only", 5)
    source["oracle_leakage_check"] = {"forbidden_path_hits": ["x"], "forbidden_session_hits": []}
    packet = generate_answer_packet(context_packet=source, retrieval_mode="prior_only")
    errs = validate_generated_answer_packet(packet)
    assert any("oracle leakage" in e for e in errs)


def test_unsupported_forbidden_term_check_fails() -> None:
    source = _context_packet("prior_only", 5)
    term = "ZZZ Unsupported Eval Term"
    source["must_not_include_unless_sourced"] = [term]
    source["retrieved_context"] = list(source.get("retrieved_context") or [])
    source["oracle_leakage_check"] = {"forbidden_path_hits": [], "forbidden_session_hits": []}

    packet = generate_answer_packet(context_packet=source, retrieval_mode="prior_only")
    packet["answer_text"] = f"{packet['answer_text']} {term}"
    packet["structured_answer"]["summary"] = packet["answer_text"]
    _apply_must_not_include_safety(packet=packet, context_packet=source)

    assert packet["safety_checks"]["must_not_include_terms_present"] == [
        {
            "term": term,
            "supported": False,
            "reason": "term appears in generated answer but not retrieved context",
        }
    ]
    assert packet["safety_checks"]["oracle_sensitive_terms_supported_or_absent"] is False
    errs = validate_generated_answer_packet(packet)
    assert any("unsupported forbidden terms present" in e for e in errs)


def test_supported_forbidden_term_can_pass() -> None:
    term = "ZZZ Supported Eval Term"
    source = _context_packet("prior_only", 5)
    source["must_not_include_unless_sourced"] = [term]
    source["retrieved_context"] = [
        {"unit_id": "corpus:test:1", "title": term, "snippet": f"Canonical mention of {term}."},
    ]
    source["oracle_leakage_check"] = {"forbidden_path_hits": [], "forbidden_session_hits": []}

    packet = generate_answer_packet(context_packet=source, retrieval_mode="prior_only")
    packet["answer_text"] = f"{packet['answer_text']} {term}"
    packet["structured_answer"]["summary"] = packet["answer_text"]
    _apply_must_not_include_safety(packet=packet, context_packet=source)

    assert packet["safety_checks"]["must_not_include_terms_present"] == [
        {
            "term": term,
            "supported": True,
            "reason": "term appears in generated answer and is supported by retrieved context",
        }
    ]
    assert packet["safety_checks"]["oracle_sensitive_terms_supported_or_absent"] is True
    assert validate_generated_answer_packet(packet) == []


def test_template_generator_does_not_claim_oracle_quality() -> None:
    summary = build_step4_summary(mode="prior_only", question_number=5)
    dumped = str(summary)
    assert "oracle_score" not in dumped
    assert "passed_oracle_grading" not in dumped
    assert "matches_c1s4" not in dumped
