from __future__ import annotations

import pytest

from evals.c1s4_preplanning_vertical_slice.generated_answer_harness import (
    _apply_must_not_include_safety,
    generate_answer_packet,
    validate_generated_answer_packet,
)
from evals.c1s4_preplanning_vertical_slice.planner_prompt_payload import (
    build_evaluator_control_metadata,
    build_planner_prompt_payload,
    validate_planner_prompt_payload,
)
from evals.c1s4_preplanning_vertical_slice.step2_build_question_context_packets import build_summary as build_step2_summary
from evals.c1s4_preplanning_vertical_slice.step4_generate_answer_packets import build_summary as build_step4_summary


def _context_packet(mode: str, question_number: int) -> dict:
    return build_step2_summary(mode=mode, question_number=question_number)["packets"][0]


def _prompt_and_meta(context: dict) -> tuple[dict, dict]:
    return build_planner_prompt_payload(context_packet=context), build_evaluator_control_metadata(context_packet=context)


def test_generated_answer_uses_planner_prompt_payload_not_context_packet() -> None:
    ctx = _context_packet("prior_only", 5)
    prompt, meta = _prompt_and_meta(ctx)
    packet = generate_answer_packet(planner_prompt_payload=prompt, evaluator_control_metadata=meta, retrieval_mode="prior_only")
    assert packet["source_planner_prompt_payload_schema"] == prompt["schema"]
    assert "authority_label" not in packet
    assert packet["evaluator_control_metadata"]["authority_label"]


def test_generated_answer_text_does_not_include_expected_behavior() -> None:
    packet = generate_answer_packet(context_packet=_context_packet("prior_only", 5))
    assert "expected behavior:" not in packet["answer_text"].lower()


def test_generated_answer_text_does_not_include_authority_requirement_label() -> None:
    packet = generate_answer_packet(context_packet=_context_packet("prior_plus_support_content_only", 5))
    assert "authority requirement:" not in packet["answer_text"].lower()


def test_generated_answer_text_does_not_include_oracle_risk() -> None:
    ctx = _context_packet("prior_only", 3)
    packet = generate_answer_packet(context_packet=ctx)
    risk = str((packet.get("evaluator_control_metadata") or {}).get("oracle_risk") or "").lower()
    if risk:
        assert risk not in packet["answer_text"].lower()


def test_generated_answer_can_still_report_source_derived_gaps() -> None:
    packet = generate_answer_packet(context_packet=_context_packet("prior_only", 3))
    assert packet["source_derived_context_gaps_used"] or "source-derived" in packet["answer_text"].lower()


def test_generated_answer_validation_rejects_prompt_payload_with_control_metadata() -> None:
    ctx = _context_packet("prior_only", 5)
    prompt, meta = _prompt_and_meta(ctx)
    prompt["expected_mode_behavior"] = "leak"
    assert validate_planner_prompt_payload(prompt)
    with pytest.raises(ValueError):
        generate_answer_packet(planner_prompt_payload=prompt, evaluator_control_metadata=meta, retrieval_mode="prior_only")


def test_generated_packet_allows_oracle_diagnostics_in_evaluator_metadata() -> None:
    ctx = _context_packet("prior_only", 5)
    prompt, meta = _prompt_and_meta(ctx)
    meta["oracle_leakage_check"] = {"forbidden_path_hits": ["x"], "forbidden_session_hits": []}
    packet = generate_answer_packet(planner_prompt_payload=prompt, evaluator_control_metadata=meta, retrieval_mode="prior_only")
    errs = validate_generated_answer_packet(packet)
    assert not any("oracle leakage" in e for e in errs)
    assert packet["safety_checks"]["no_oracle_context_detected"] is False


def test_step4_builds_generated_packets_for_all_questions() -> None:
    summary = build_step4_summary(mode="prior_only", limit=3)
    assert summary["answer_generation_status"] == "generated"
    assert summary["counts"]["answer_packets_built"] == 3
    assert all(p["answer_text"] for p in summary["answer_packets"])


def test_must_not_include_safety_uses_evaluator_metadata_not_prompt() -> None:
    ctx = _context_packet("prior_only", 5)
    prompt, meta = _prompt_and_meta(ctx)
    packet = generate_answer_packet(planner_prompt_payload=prompt, evaluator_control_metadata=meta, retrieval_mode="prior_only")
    packet["answer_text"] = "contains hempholm detail"
    _apply_must_not_include_safety(packet=packet, planner_prompt_payload=prompt, evaluator_control_metadata=meta)
    assert packet["safety_checks"]["forbidden_terms_checked"] is True
