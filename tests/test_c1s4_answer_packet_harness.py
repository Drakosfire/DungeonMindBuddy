from __future__ import annotations

from evals.c1s4_preplanning_vertical_slice.answer_packet_harness import (
    ANSWER_PACKET_SCHEMA,
    build_stub_answer_packet,
    validate_answer_packet,
)
from evals.c1s4_preplanning_vertical_slice.step2_build_question_context_packets import build_summary as build_step2_summary
from evals.c1s4_preplanning_vertical_slice.step3_build_stub_answer_packets import build_summary as build_step3_summary


def _step2_packet(*, mode: str = "prior_only", question_number: int = 1) -> dict:
    return build_step2_summary(mode=mode, question_number=question_number)["packets"][0]


def test_builds_stub_answer_packet_from_context_packet() -> None:
    packet = build_stub_answer_packet(context_packet=_step2_packet(mode="prior_plus_support_content_only", question_number=5))
    assert packet["schema"] == ANSWER_PACKET_SCHEMA
    assert packet["question_id"]
    assert packet["question_number"] == 5
    assert packet["retrieval_mode"] == "prior_plus_support_content_only"
    assert packet["authority_label"] == "support_knowledge_required"
    assert packet["oracle_risk"]


def test_stub_answer_packet_does_not_generate_answer() -> None:
    packet = build_stub_answer_packet(context_packet=_step2_packet())
    assert packet["answer_generation_status"] == "stubbed_not_generated"
    assert packet["answer_text"] is None
    assert packet["structured_answer"] is None
    assert packet["used_context_refs"] == []
    assert packet["unused_context_refs"] == []


def test_answer_packet_rejects_eval_only_fields() -> None:
    packet = build_stub_answer_packet(context_packet=_step2_packet())
    packet["expected_retrieval_context_eval_only"] = ["bad"]
    packet["expected_retrieval_modes"] = {"prior_only": "bad"}
    errs = validate_answer_packet(packet)
    assert any("expected_retrieval_context_eval_only" in e for e in errs)
    assert any("expected_retrieval_modes" in e for e in errs)


def test_answer_packet_does_not_embed_retrieved_context() -> None:
    packet = build_stub_answer_packet(context_packet=_step2_packet())
    assert "retrieved_context" not in packet


def test_answer_packet_preserves_guardrails_without_gold_known_gaps() -> None:
    context = _step2_packet(mode="prior_only", question_number=5)
    packet = build_stub_answer_packet(context_packet=context)
    assert "known_context_gaps" not in context
    assert packet["known_context_gaps"] == []
    assert packet["must_not_include_unless_sourced"] == context["must_not_include_unless_sourced"]
    assert packet["expected_mode_behavior"] == context["expected_mode_behavior"]


def test_answer_packet_preserves_oracle_leakage_check() -> None:
    context = _step2_packet()
    packet = build_stub_answer_packet(context_packet=context)
    assert packet["oracle_leakage_check"]["forbidden_path_hits"] == context["oracle_leakage_check"]["forbidden_path_hits"]
    assert packet["oracle_leakage_check"]["forbidden_session_hits"] == context["oracle_leakage_check"]["forbidden_session_hits"]


def test_answer_packet_validator_rejects_oracle_leakage() -> None:
    packet = build_stub_answer_packet(context_packet=_step2_packet())
    packet["oracle_leakage_check"] = {"forbidden_path_hits": ["bad/path"], "forbidden_session_hits": []}
    errs = validate_answer_packet(packet)
    assert any("forbidden_path_hits" in e for e in errs)


def test_step3_skips_q35() -> None:
    summary = build_step3_summary(mode="prior_only")
    assert any(row["question_number"] == 35 for row in summary["skipped_questions"])
    assert all(p["question_number"] != 35 for p in summary["answer_packets"])


def test_prior_only_support_required_packet_keeps_missing_support_expectation() -> None:
    summary = build_step3_summary(mode="prior_only", question_number=5)
    packet = summary["answer_packets"][0]
    assert packet["authority_label"] == "support_knowledge_required"
    assert packet["expected_mode_behavior"] == "should_generate_generic_and_admit_missing_support"
    assert packet["answer_generation_status"] == "stubbed_not_generated"


def test_step3_summary_reports_no_generated_answers() -> None:
    summary = build_step3_summary(mode="prior_plus_support_content_only", limit=5)
    assert summary["answer_generation_status"] == "stubbed_not_generated"
    assert all(p["answer_text"] is None for p in summary["answer_packets"])
    assert all(p["structured_answer"] is None for p in summary["answer_packets"])
