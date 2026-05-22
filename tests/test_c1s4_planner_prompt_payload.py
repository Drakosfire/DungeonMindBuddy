from __future__ import annotations

from evals.c1s4_preplanning_vertical_slice.planner_prompt_payload import (
    EVALUATOR_CONTROL_METADATA_SCHEMA,
    FORBIDDEN_PROMPT_KEYS,
    PLANNER_PROMPT_PAYLOAD_SCHEMA,
    build_evaluator_control_metadata,
    build_planner_prompt_payload,
    find_forbidden_prompt_material,
    validate_evaluator_control_metadata,
    validate_planner_prompt_payload,
)
from evals.c1s4_preplanning_vertical_slice.step2_build_question_context_packets import build_summary


def _context_packet(*, mode: str = "prior_only", question_number: int = 3) -> dict:
    return build_summary(mode=mode, question_number=question_number, max_hits=50)["packets"][0]


def test_build_planner_prompt_payload_excludes_control_metadata() -> None:
    packet = _context_packet(question_number=5, mode="prior_plus_support_content_only")
    payload = build_planner_prompt_payload(context_packet=packet)
    for key in (
        "authority_label",
        "oracle_risk",
        "expected_mode_behavior",
        "answer_product",
        "must_not_include_unless_sourced",
    ):
        assert key not in payload
    assert not find_forbidden_prompt_material(payload)


def test_build_planner_prompt_payload_includes_rendered_context() -> None:
    payload = build_planner_prompt_payload(context_packet=_context_packet())
    rendered = payload.get("rendered_context") or {}
    assert rendered.get("rendered_text")
    assert rendered.get("sections")
    assert rendered.get("provenance_map")


def test_build_planner_prompt_payload_includes_source_derived_context_gaps() -> None:
    payload = build_planner_prompt_payload(context_packet=_context_packet(question_number=3))
    assert payload.get("source_derived_context_gaps")


def test_build_planner_prompt_payload_includes_generic_grounding_instructions() -> None:
    payload = build_planner_prompt_payload(context_packet=_context_packet())
    instructions = " ".join(payload.get("instructions") or []).lower()
    assert "use only the provided context" in instructions
    assert "does not establish" in instructions
    assert "must_not_include" not in instructions


def test_validate_planner_prompt_payload_rejects_expected_mode_behavior() -> None:
    payload = build_planner_prompt_payload(context_packet=_context_packet())
    payload["expected_mode_behavior"] = "admit gaps"
    errs = validate_planner_prompt_payload(payload)
    assert any("expected_mode_behavior" in e for e in errs)


def test_validate_planner_prompt_payload_rejects_authority_label() -> None:
    payload = build_planner_prompt_payload(context_packet=_context_packet())
    payload["authority_label"] = "support_knowledge_required"
    errs = validate_planner_prompt_payload(payload)
    assert any("authority_label" in e for e in errs)


def test_validate_planner_prompt_payload_rejects_oracle_risk() -> None:
    payload = build_planner_prompt_payload(context_packet=_context_packet())
    payload["oracle_risk"] = "medium"
    errs = validate_planner_prompt_payload(payload)
    assert any("oracle_risk" in e for e in errs)


def test_validate_planner_prompt_payload_rejects_must_not_include_unless_sourced() -> None:
    payload = build_planner_prompt_payload(context_packet=_context_packet())
    payload["must_not_include_unless_sourced"] = ["secret benchmark term"]
    errs = validate_planner_prompt_payload(payload)
    assert any("must_not_include_unless_sourced" in e for e in errs)


def test_validate_planner_prompt_payload_rejects_gold_paths_recursively() -> None:
    payload = build_planner_prompt_payload(context_packet=_context_packet())
    payload["rendered_context"]["sections"][0]["text"] = "see evals/c1s4_preplanning_vertical_slice/gold/c1s4_expected_context_gold.json"
    hits = find_forbidden_prompt_material(payload)
    assert hits
    assert validate_planner_prompt_payload(payload)


def test_build_evaluator_control_metadata_contains_expected_behavior_fields() -> None:
    packet = _context_packet(question_number=5, mode="prior_only")
    meta = build_evaluator_control_metadata(context_packet=packet)
    assert meta["schema"] == EVALUATOR_CONTROL_METADATA_SCHEMA
    assert meta.get("authority_label")
    assert meta.get("oracle_risk")
    assert meta.get("expected_mode_behavior")
    assert isinstance(meta.get("must_not_include_unless_sourced"), list)
    assert validate_evaluator_control_metadata(meta) == []


def test_prompt_payload_and_evaluator_metadata_have_disjoint_forbidden_fields() -> None:
    packet = _context_packet(question_number=5)
    payload = build_planner_prompt_payload(context_packet=packet)
    meta = build_evaluator_control_metadata(context_packet=packet)
    assert not any(key in payload for key in FORBIDDEN_PROMPT_KEYS)
    assert meta.get("authority_label")
    assert payload.get("schema") == PLANNER_PROMPT_PAYLOAD_SCHEMA
