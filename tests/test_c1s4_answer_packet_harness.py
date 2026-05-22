from __future__ import annotations

from evals.c1s4_preplanning_vertical_slice.answer_packet_harness import (
    ANSWER_PACKET_SCHEMA,
    build_stub_answer_packet,
    validate_answer_packet,
)
from evals.c1s4_preplanning_vertical_slice.planner_prompt_payload import (
    build_evaluator_control_metadata,
    build_planner_prompt_payload,
)
from evals.c1s4_preplanning_vertical_slice.step2_build_question_context_packets import build_summary as build_step2_summary
from evals.c1s4_preplanning_vertical_slice.step3_build_stub_answer_packets import build_summary as build_step3_summary


def _step2_packet(*, mode: str = "prior_only", question_number: int = 1) -> dict:
    return build_step2_summary(mode=mode, question_number=question_number)["packets"][0]


def test_builds_stub_answer_packet_from_context_packet() -> None:
    context = _step2_packet(mode="prior_plus_support_content_only", question_number=5)
    packet = build_stub_answer_packet(context_packet=context)
    assert packet["schema"] == ANSWER_PACKET_SCHEMA
    assert packet["question_id"]
    assert packet["question_number"] == 5
    assert packet["retrieval_mode"] == "prior_plus_support_content_only"
    meta = packet["evaluator_control_metadata"]
    assert meta["authority_label"] == "support_knowledge_required"
    assert meta["oracle_risk"]


def test_stub_answer_packet_does_not_generate_answer() -> None:
    packet = build_stub_answer_packet(context_packet=_step2_packet())
    assert packet["answer_generation_status"] == "stubbed_not_generated"
    assert packet["answer_text"] is None
    assert packet["structured_answer"] is None
    assert packet["used_context_refs"] == []
    assert packet["unused_context_refs"] == []


def test_stub_answer_packet_no_longer_copies_expected_mode_behavior() -> None:
    packet = build_stub_answer_packet(context_packet=_step2_packet(question_number=5))
    assert "expected_mode_behavior" not in packet
    assert packet["evaluator_control_metadata"]["expected_mode_behavior"]


def test_stub_answer_packet_no_longer_copies_authority_label() -> None:
    packet = build_stub_answer_packet(context_packet=_step2_packet(question_number=5))
    assert "authority_label" not in packet
    assert packet["evaluator_control_metadata"]["authority_label"]


def test_stub_answer_packet_no_longer_copies_oracle_risk() -> None:
    packet = build_stub_answer_packet(context_packet=_step2_packet())
    assert "oracle_risk" not in packet
    assert packet["evaluator_control_metadata"]["oracle_risk"]


def test_answer_packet_rejects_eval_only_fields_at_top_level() -> None:
    packet = build_stub_answer_packet(context_packet=_step2_packet())
    packet["expected_retrieval_context_eval_only"] = ["bad"]
    packet["expected_retrieval_modes"] = {"prior_only": "bad"}
    errs = validate_answer_packet(packet)
    assert any("expected_retrieval_context_eval_only" in e for e in errs)
    assert any("expected_retrieval_modes" in e for e in errs)


def test_answer_packet_does_not_embed_retrieved_context() -> None:
    packet = build_stub_answer_packet(context_packet=_step2_packet())
    assert "retrieved_context" not in packet


def test_answer_packet_keeps_evaluator_metadata_out_of_answer_text() -> None:
    packet = build_stub_answer_packet(context_packet=_step2_packet(question_number=5))
    assert packet["answer_text"] is None
    assert "expected_mode_behavior" not in packet
    assert packet["evaluator_control_metadata"]["must_not_include_unless_sourced"]


def test_answer_packet_preserves_oracle_diagnostics_in_evaluator_metadata() -> None:
    context = _step2_packet()
    packet = build_stub_answer_packet(context_packet=context)
    meta = packet["evaluator_control_metadata"]
    assert meta["oracle_leakage_check"]["forbidden_path_hits"] == context["oracle_leakage_check"]["forbidden_path_hits"]
    assert meta["oracle_leakage_check"]["forbidden_session_hits"] == context["oracle_leakage_check"]["forbidden_session_hits"]


def test_answer_packet_validator_allows_oracle_diagnostics_in_evaluator_metadata() -> None:
    context = _step2_packet()
    prompt = build_planner_prompt_payload(context_packet=context)
    meta = build_evaluator_control_metadata(context_packet=context)
    meta["oracle_leakage_check"] = {
        "forbidden_path_hits": ["bad/path"],
        "forbidden_session_hits": [],
    }
    packet = build_stub_answer_packet(planner_prompt_payload=prompt, evaluator_control_metadata=meta)
    errs = validate_answer_packet(packet)
    assert not any("forbidden_path_hits" in e for e in errs)
    assert packet["safety_checks"]["no_oracle_context_detected"] is False


def test_step3_skips_q35() -> None:
    summary = build_step3_summary(mode="prior_only")
    assert any(row["question_number"] == 35 for row in summary["skipped_questions"])
    assert all(p["question_number"] != 35 for p in summary["answer_packets"])


def test_prior_only_support_required_packet_keeps_missing_support_expectation_in_evaluator_metadata() -> None:
    summary = build_step3_summary(mode="prior_only", question_number=5)
    packet = summary["answer_packets"][0]
    meta = packet["evaluator_control_metadata"]
    assert meta["authority_label"] == "support_knowledge_required"
    assert meta["expected_mode_behavior"] == "should_generate_generic_and_admit_missing_support"
    assert packet["answer_generation_status"] == "stubbed_not_generated"


def test_step3_summary_reports_no_generated_answers() -> None:
    summary = build_step3_summary(mode="prior_plus_support_content_only", limit=5)
    assert summary["answer_generation_status"] == "stubbed_not_generated"
    assert all(p["answer_text"] is None for p in summary["answer_packets"])
    assert all(p["structured_answer"] is None for p in summary["answer_packets"])


def test_stub_answer_uses_explicit_prompt_payload_and_metadata() -> None:
    context = _step2_packet(question_number=1)
    prompt = build_planner_prompt_payload(context_packet=context)
    meta = build_evaluator_control_metadata(context_packet=context)
    packet = build_stub_answer_packet(planner_prompt_payload=prompt, evaluator_control_metadata=meta)
    assert validate_answer_packet(packet) == []
