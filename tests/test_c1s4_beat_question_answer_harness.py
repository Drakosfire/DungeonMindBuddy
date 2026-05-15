from __future__ import annotations

from evals.c1s4_preplanning_vertical_slice.beat_question_answer_harness import (
    build_question_context_packet,
    is_planner_facing_question,
    iter_target_questions,
    load_beat_question_targets,
    validate_packet,
)
from evals.c1s4_preplanning_vertical_slice.step2_build_question_context_packets import build_summary


def _find_question(n: int) -> dict:
    return next(q for q in iter_target_questions(load_beat_question_targets()) if q["question_number"] == n)


def test_target_artifact_not_loaded_as_retrieval_record() -> None:
    summary = build_summary(mode="prior_plus_support_content_only", question_number=1)
    item_paths = [str(i.get("source_recap_path") or i.get("source_reference") or "") for i in summary["packets"][0]["retrieved_context"]]
    assert not any("c1s4_beat_question_targets.json" in p for p in item_paths)


def test_expected_retrieval_context_eval_only_not_in_packet() -> None:
    summary = build_summary(mode="prior_only", question_number=1)
    packet = summary["packets"][0]
    assert "expected_retrieval_context_eval_only" not in packet
    assert "expected_retrieval_modes" not in packet
    assert "expected_mode_behavior" in packet


def test_q35_skipped_for_planner_modes() -> None:
    for mode in ["prior_only", "prior_plus_support_content_only", "prior_plus_support_content_plus_lexical_hints"]:
        summary = build_summary(mode=mode)
        assert any(row["question_number"] == 35 for row in summary["skipped_questions"])
        assert all(p["question_number"] != 35 for p in summary["packets"])


def test_support_required_prior_only_packet_admits_missing_support() -> None:
    summary = build_summary(mode="prior_only", question_number=5)
    packet = summary["packets"][0]
    assert packet["authority_label"] == "support_knowledge_required"
    assert packet["expected_mode_behavior"] == "should_generate_generic_and_admit_missing_support"
    assert packet["retrieval_mode"] == "prior_only"


def test_prior_plus_support_packet_contains_authority_summary() -> None:
    summary = build_summary(mode="prior_plus_support_content_only", question_number=5)
    packet = summary["packets"][0]
    assert "authority_summary" in packet
    for item in packet["retrieved_context"]:
        if item.get("source_kind") == "support_knowledge_card":
            assert "source_layer" in item
            assert "authority_role" in item
            assert "canon_status" in item


def test_packet_answer_slot_is_null() -> None:
    summary = build_summary(mode="prior_only", question_number=1)
    assert summary["packets"][0]["answer_slot"] is None


def test_oracle_forbidden_paths_still_empty() -> None:
    summary = build_summary(mode="prior_plus_support_content_plus_lexical_hints", question_number=1)
    assert summary["oracle_leakage_check"]["forbidden_path_hits"] == []
    assert summary["oracle_leakage_check"]["forbidden_session_hits"] == []


def test_packet_validator_rejects_eval_only_target_hints() -> None:
    q = _find_question(1)
    packet = build_question_context_packet(
        question=q,
        retrieval_mode="prior_only",
        retrieved_context=[],
        oracle_leakage_check={"forbidden_path_hits": [], "forbidden_session_hits": []},
    )
    packet["expected_retrieval_context_eval_only"] = ["bad"]
    assert any("expected_retrieval_context_eval_only" in e for e in validate_packet(packet))


def test_no_llm_or_answer_generation_side_effects() -> None:
    summary = build_summary(mode="prior_plus_support_content_only", limit=5)
    assert all(p["answer_slot"] is None for p in summary["packets"])


def test_step2_rejects_manifest_boundary_violations(monkeypatch) -> None:
    from evals.c1s4_preplanning_vertical_slice import step2_build_question_context_packets as step2

    bad_manifest = {
        "kb_id": "x",
        "campaign_id": "longmont-c1",
        "included_sessions": [1, 2, 3],
        "heldout_sessions": [4],
        "forbidden_path_hits": ["forbidden/path"],
        "forbidden_session_hits": [4],
        "unexpected_session_hits": [99],
    }

    monkeypatch.setattr(step2, "load_kb_manifest", lambda _path: (bad_manifest, []))

    try:
        step2.build_summary(mode="prior_only", question_number=1)
    except step2.C1S4BoundaryError:
        return
    raise AssertionError("Expected C1S4BoundaryError when manifest has boundary violations")
