from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from evals.c1s4_preplanning_vertical_slice.beat_question_answer_harness import (
    QuestionRetrievalMode,
    is_planner_facing_question,
    iter_target_questions,
    load_beat_question_targets,
    validate_packet,
)
from evals.c1s4_preplanning_vertical_slice.context_renderer import render_context_packet
from evals.c1s4_preplanning_vertical_slice.expected_context_benchmark import (
    grade_question_packet,
    load_expected_context_gold,
)
from evals.c1s4_preplanning_vertical_slice.generated_answer_harness import (
    generate_answer_packet,
    validate_generated_answer_packet,
)
from evals.c1s4_preplanning_vertical_slice.planner_prompt_payload import (
    build_evaluator_control_metadata,
    build_planner_prompt_payload,
    find_forbidden_prompt_material,
    validate_planner_prompt_payload,
)
from evals.c1s4_preplanning_vertical_slice.source_derived_context_gaps import gap_text_contains_forbidden_gold_phrase
from evals.c1s4_preplanning_vertical_slice.step2_build_question_context_packets import build_summary as build_step2_summary

PLANNER_SURFACE_COVERAGE_SCHEMA = "dmb_c1s4_planner_surface_coverage_v1"
PLANNER_SURFACE_ROW_SCHEMA = "dmb_c1s4_planner_surface_coverage_row_v1"

RETRIEVAL_MODES: tuple[QuestionRetrievalMode, ...] = (
    "prior_only",
    "prior_plus_support_content_only",
    "prior_plus_support_content_plus_lexical_hints",
)

TIER_A_QUESTIONS = frozenset({1, 3, 5})
_CONTROL_LEAK_PHRASES = ("expected behavior:", "authority requirement:", "oracle_risk")


def _norm(text: Any) -> str:
    return " ".join(str(text or "").lower().split())


def _question_beat_map(targets: dict[str, Any]) -> dict[int, dict[str, Any]]:
    out: dict[int, dict[str, Any]] = {}
    for beat in targets.get("beats", []):
        for question in beat.get("questions", []):
            qn = int(question.get("question_number", 0))
            out[qn] = {"beat_id": beat.get("beat_id"), "beat_number": beat.get("beat_number")}
    for question in targets.get("meta_questions", []):
        qn = int(question.get("question_number", 0))
        out[qn] = {"beat_id": "meta", "beat_number": None}
    return out


@lru_cache(maxsize=8)
def _packets_by_mode_and_hits(mode: str, max_hits: int) -> dict[int, dict[str, Any]]:
    summary = build_step2_summary(mode=mode, max_hits=max_hits)  # type: ignore[arg-type]
    return {int(p["question_number"]): p for p in summary["packets"] if p.get("question_number") is not None}


def lookup_step2_packet(*, mode: str, question_number: int, max_hits: int = 50) -> dict[str, Any] | None:
    """Return the Step 2 context packet for one question/mode (cached with surface rows)."""
    return _packets_by_mode_and_hits(mode, max_hits).get(int(question_number))


def _gold_by_question_number() -> dict[int, dict[str, Any]]:
    gold = load_expected_context_gold()
    return {int(q["question_number"]): q for q in gold.get("questions", []) if q.get("question_number") is not None}


def _first_support_rank(items: list[dict[str, Any]]) -> int | None:
    for idx, item in enumerate(items, start=1):
        unit_id = str(item.get("unit_id") or "")
        if str(item.get("source_kind") or "") == "support_knowledge_card" or unit_id.startswith("support:"):
            return idx
    return None


def _section_has_visible_content(section: dict[str, Any]) -> bool:
    refs = section.get("refs") or []
    text = str(section.get("text") or section.get("rendered_text") or "").strip()
    if text.lower() in {"", "- (none)", "(none)", "- none"}:
        text = ""
    return bool(refs or text)


def _support_section_rendered(rendered: dict[str, Any]) -> bool:
    for section in rendered.get("sections") or []:
        if not isinstance(section, dict):
            continue
        if section.get("section_id") != "support_knowledge":
            continue
        if _section_has_visible_content(section):
            return True
    return False


def _tier_a_row_ok(*, packet: dict[str, Any], gold_question: dict[str, Any], mode: QuestionRetrievalMode) -> bool:
    row = grade_question_packet(packet=packet, gold_question=gold_question, retrieval_mode=mode, top_k=9)
    qn = int(packet.get("question_number") or 0)
    if qn == 3:
        route_results = (row.get("lane_aware_diagnostics") or {}).get("required_group_results") or []
        route_gap = next((r for r in route_results if r.get("group_id") == "mirathorn_exact_route_gap"), None)
        if route_gap and route_gap.get("ok"):
            return "missing_expected_known_gap" not in (row.get("violations") or [])
        return False
    return bool(row.get("ok"))


def _terms_in_blob(terms: list[str], blob: str) -> list[str]:
    hay = _norm(blob)
    hits: list[str] = []
    for term in terms:
        needle = _norm(term)
        if needle and needle in hay:
            hits.append(str(term))
    return hits


def _generated_answer_control_leak(answer: dict[str, Any], meta: dict[str, Any]) -> bool:
    answer_lower = str(answer.get("answer_text") or "").lower()
    for phrase in _CONTROL_LEAK_PHRASES:
        if phrase in answer_lower:
            return True
    risk = str(meta.get("oracle_risk") or "").lower()
    return bool(risk and risk in answer_lower)


def _classify_support_policy(
    *,
    mode: str,
    authority_label: str,
    support_allowed: bool,
    support_required: bool,
    support_context_rendered: bool,
    support_in_admitted: bool,
    support_in_candidate: bool,
) -> str:
    if not support_required:
        if support_context_rendered:
            return "support_present_incidental"
        return "support_not_required"
    if mode == "prior_only":
        if support_context_rendered:
            return "support_leaked_in_prior_only"
        if support_in_admitted or support_in_candidate:
            return "support_leaked_in_prior_only"
        return "support_required_policy_suppressed_expected"
    if support_context_rendered:
        return "support_allowed_and_present"
    if support_in_admitted:
        return "support_present_but_not_rendered"
    if support_in_candidate:
        return "support_allowed_but_missing"
    if support_allowed:
        return "support_expected_but_missing"
    return "support_not_required"


def _classify_retrieval_sufficiency(
    *,
    question: dict[str, Any],
    mode: str,
    authority_label: str,
    prompt_payload_valid: bool,
    forbidden_key_hits: int,
    forbidden_value_hits: int,
    known_context_gaps_leaked: bool,
    generated_control_leak: bool,
    support_policy_status: str,
    support_context_rendered: bool,
    source_derived_gap_count: int,
    admitted_context_count: int,
    rendered_context_present: bool,
    tier_a_grade_ok: bool | None,
) -> tuple[str, str]:
    if not question.get("planner_facing", True):
        return "evaluator_only", "evaluator_only_not_planner_facing"
    if not prompt_payload_valid:
        return "prompt_boundary_failure", "prompt_boundary_failure"
    if forbidden_key_hits:
        return "prompt_boundary_failure", "prompt_payload_forbidden_key_leak"
    if forbidden_value_hits:
        return "prompt_boundary_failure", "prompt_payload_forbidden_value_leak"
    if known_context_gaps_leaked:
        return "prompt_boundary_failure", "gold_known_gap_leak"
    if generated_control_leak:
        return "prompt_boundary_failure", "generated_answer_control_metadata_leak"
    if support_policy_status == "support_leaked_in_prior_only":
        return "prompt_boundary_failure", "support_leaked_in_prior_only"

    qn = int(question.get("question_number") or 0)
    if qn in TIER_A_QUESTIONS and tier_a_grade_ok is False:
        return "tier_a_regression", "tier_a_gold_regression"

    if qn in TIER_A_QUESTIONS and tier_a_grade_ok is True:
        return "ok_or_later_stage", "ok_or_later_stage"

    if authority_label == "creative_generation":
        return "creative_generation_no_strict_context_required", "ok_or_later_stage"
    if authority_label == "oracle_only":
        return "evaluator_only", "evaluator_only_not_planner_facing"

    if authority_label == "support_knowledge_required":
        if support_policy_status == "support_required_policy_suppressed_expected":
            return "policy_correct", "support_required_policy_suppressed_expected"
        if support_policy_status in {
            "support_allowed_and_present",
            "support_present_incidental",
        }:
            return "ok_or_later_stage", "ok_or_later_stage"
        if support_policy_status in {"support_expected_but_missing", "support_allowed_but_missing"}:
            return "support_expected_but_missing", "support_expected_but_missing"
        if support_policy_status == "support_present_but_not_rendered":
            return "context_present_but_low_signal", "support_present_but_not_rendered"
        return "needs_manual_review", support_policy_status

    if authority_label == "worldbuilding_required":
        known_gaps = list(question.get("known_context_gaps") or [])
        if known_gaps and source_derived_gap_count == 0:
            return "source_gap_expected_but_missing", "source_gap_expected_but_missing"
        if rendered_context_present or source_derived_gap_count > 0:
            return "ok_or_later_stage", "ok_or_later_stage"
        return "context_present_but_low_signal", "context_present_but_low_signal"

    if authority_label == "prior_recap_supported":
        if admitted_context_count > 0 and rendered_context_present:
            return "ok_or_later_stage", "ok_or_later_stage"
        if rendered_context_present:
            return "context_present_but_low_signal", "context_present_but_low_signal"
        return "context_present_but_low_signal", "context_present_but_low_signal"

    if authority_label == "mixed":
        if rendered_context_present and admitted_context_count > 0:
            return "needs_manual_review", "ok_or_later_stage"
        return "needs_manual_review", "needs_manual_review"

    if tier_a_grade_ok is True:
        return "ok_or_later_stage", "ok_or_later_stage"
    if rendered_context_present:
        return "ok_or_later_stage", "ok_or_later_stage"
    return "needs_manual_review", "needs_manual_review"


def _build_row(
    *,
    question: dict[str, Any],
    mode: QuestionRetrievalMode,
    beat_meta: dict[str, Any],
    packet: dict[str, Any] | None,
    max_hits: int,
    gold_question: dict[str, Any] | None,
    include_generated_answer: bool,
) -> dict[str, Any]:
    qn = int(question.get("question_number") or 0)
    planner_facing = is_planner_facing_question(question, retrieval_mode=mode)
    authority_label = str(question.get("authority_label") or "")
    must_not_terms = list(question.get("must_not_include_unless_sourced") or [])

    if not planner_facing:
        return {
            "schema": PLANNER_SURFACE_ROW_SCHEMA,
            "question_number": qn,
            "question_id": question.get("question_id"),
            "beat_id": beat_meta.get("beat_id"),
            "beat_number": beat_meta.get("beat_number"),
            "mode": mode,
            "planner_facing": False,
            "authority_label": authority_label,
            "oracle_risk": question.get("oracle_risk"),
            "expected_mode_behavior": (question.get("expected_retrieval_modes") or {}).get(mode),
            "prompt_payload_valid": None,
            "forbidden_prompt_key_hits": 0,
            "forbidden_prompt_value_hits": 0,
            "rendered_context_present": False,
            "support_knowledge_allowed": mode != "prior_only",
            "support_required": authority_label == "support_knowledge_required",
            "support_context_rendered": False,
            "support_policy_status": "evaluator_only_not_planner_facing",
            "source_derived_gap_count": 0,
            "known_context_gaps_leaked": False,
            "admitted_context_count": 0,
            "rendered_section_count": 0,
            "estimated_rendered_tokens": 0,
            "forbidden_terms_in_prompt_payload": [],
            "must_not_include_terms": must_not_terms,
            "must_not_include_term_count": len(must_not_terms),
            "must_not_include_terms_in_prompt_payload": [],
            "must_not_include_terms_in_generated_stub": [],
            "first_support_candidate_rank": None,
            "first_support_admitted_rank": None,
            "support_token_share": 0.0,
            "generated_answer_control_leak": False,
            "oracle_boundary_status": "evaluator_only",
            "required_context_heuristic_status": "skipped_evaluator_only",
            "retrieval_sufficiency_class": "evaluator_only",
            "next_failure_surface": "evaluator_only_not_planner_facing",
        }

    if packet is None:
        raise ValueError(f"missing Step2 packet for planner-facing q{qn} mode={mode}")

    validate_packet(packet)
    prompt = build_planner_prompt_payload(context_packet=packet)
    meta = build_evaluator_control_metadata(context_packet=packet, question=question)
    rendered = render_context_packet(packet)
    prompt_errs = validate_planner_prompt_payload(prompt)
    material_hits = find_forbidden_prompt_material(prompt)
    key_hits = [h for h in material_hits if "forbidden key" in h]
    value_hits = [h for h in material_hits if "forbidden value token" in h]

    admitted = list(packet.get("admitted_context") or packet.get("retrieved_context") or [])
    candidate = list(packet.get("candidate_context") or [])
    sections = list((prompt.get("rendered_context") or {}).get("sections") or [])
    estimated_tokens = sum(int(s.get("estimated_tokens") or 0) for s in sections if isinstance(s, dict))
    total_tokens = estimated_tokens or int((prompt.get("context_summary") or {}).get("estimated_rendered_tokens") or 0)
    support_tokens = sum(
        int(s.get("estimated_tokens") or 0) for s in sections if isinstance(s, dict) and s.get("section_id") == "support_knowledge"
    )
    support_share = round(support_tokens / total_tokens, 4) if total_tokens else 0.0

    prompt_blob = json.dumps(prompt.get("instructions") or [], sort_keys=True)
    terms_in_prompt = _terms_in_blob(must_not_terms, prompt_blob)
    known_gaps_leaked = "known_context_gaps" in packet
    gap_blob = json.dumps(prompt.get("source_derived_context_gaps") or [], sort_keys=True)
    known_gaps_leaked = known_gaps_leaked or gap_text_contains_forbidden_gold_phrase(gap_blob)

    support_rendered = _support_section_rendered(rendered)
    support_in_admitted = _first_support_rank(admitted) is not None
    support_in_candidate = _first_support_rank(candidate) is not None
    support_allowed = mode != "prior_only"
    support_required = authority_label == "support_knowledge_required"
    support_policy = _classify_support_policy(
        mode=mode,
        authority_label=authority_label,
        support_allowed=support_allowed,
        support_required=support_required,
        support_context_rendered=support_rendered,
        support_in_admitted=support_in_admitted,
        support_in_candidate=support_in_candidate,
    )

    generated_control_leak = False
    terms_in_answer: list[str] = []
    if include_generated_answer:
        answer = generate_answer_packet(
            planner_prompt_payload=prompt,
            evaluator_control_metadata=meta,
            retrieval_mode=mode,
        )
        generated_control_leak = _generated_answer_control_leak(answer, meta) or bool(validate_generated_answer_packet(answer))
        terms_in_answer = _terms_in_blob(must_not_terms, str(answer.get("answer_text") or ""))

    tier_a_ok: bool | None = None
    if qn in TIER_A_QUESTIONS and gold_question is not None:
        tier_a_ok = _tier_a_row_ok(packet=packet, gold_question=gold_question, mode=mode)

    rendered_context_present = bool(str((prompt.get("rendered_context") or {}).get("rendered_text") or "").strip())
    sufficiency_class, next_surface = _classify_retrieval_sufficiency(
        question={"question_number": qn, "planner_facing": True, "known_context_gaps": question.get("known_context_gaps")},
        mode=mode,
        authority_label=authority_label,
        prompt_payload_valid=not prompt_errs,
        forbidden_key_hits=len(key_hits),
        forbidden_value_hits=len(value_hits),
        known_context_gaps_leaked=known_gaps_leaked,
        generated_control_leak=generated_control_leak,
        support_policy_status=support_policy,
        support_context_rendered=support_rendered,
        source_derived_gap_count=len(prompt.get("source_derived_context_gaps") or []),
        admitted_context_count=len(admitted),
        rendered_context_present=rendered_context_present,
        tier_a_grade_ok=tier_a_ok,
    )

    heuristic_status = "ok"
    if len(admitted) == 0:
        heuristic_status = "no_admitted_context"
    elif not rendered_context_present:
        heuristic_status = "missing_rendered_context"
    elif support_required and support_policy.startswith("support_expected"):
        heuristic_status = "support_gap"

    oracle_boundary_status = "ok"
    if known_gaps_leaked or key_hits or value_hits:
        oracle_boundary_status = "prompt_boundary_violation"

    return {
        "schema": PLANNER_SURFACE_ROW_SCHEMA,
        "question_number": qn,
        "question_id": question.get("question_id"),
        "beat_id": beat_meta.get("beat_id"),
        "beat_number": beat_meta.get("beat_number"),
        "mode": mode,
        "planner_facing": True,
        "authority_label": authority_label,
        "oracle_risk": question.get("oracle_risk"),
        "expected_mode_behavior": (question.get("expected_retrieval_modes") or {}).get(mode),
        "prompt_payload_valid": not bool(prompt_errs),
        "forbidden_prompt_key_hits": len(key_hits),
        "forbidden_prompt_value_hits": len(value_hits),
        "rendered_context_present": rendered_context_present,
        "support_knowledge_allowed": support_allowed,
        "support_required": support_required,
        "support_context_rendered": support_rendered,
        "support_policy_status": support_policy,
        "source_derived_gap_count": len(prompt.get("source_derived_context_gaps") or []),
        "known_context_gaps_leaked": known_gaps_leaked,
        "admitted_context_count": len(admitted),
        "rendered_section_count": len(sections),
        "estimated_rendered_tokens": total_tokens,
        "forbidden_terms_in_prompt_payload": terms_in_prompt,
        "must_not_include_terms": must_not_terms,
        "must_not_include_term_count": len(must_not_terms),
        "must_not_include_terms_in_prompt_payload": terms_in_prompt,
        "must_not_include_terms_in_generated_stub": terms_in_answer,
        "first_support_candidate_rank": _first_support_rank(candidate),
        "first_support_admitted_rank": _first_support_rank(admitted),
        "support_token_share": support_share,
        "generated_answer_control_leak": generated_control_leak,
        "oracle_boundary_status": oracle_boundary_status,
        "required_context_heuristic_status": heuristic_status,
        "retrieval_sufficiency_class": sufficiency_class,
        "next_failure_surface": next_surface,
    }


def build_planner_surface_rows(
    *,
    modes: tuple[str, ...] = RETRIEVAL_MODES,
    include_evaluator_only: bool = False,
    max_hits: int = 50,
    include_generated_answer: bool = True,
) -> list[dict[str, Any]]:
    targets = load_beat_question_targets()
    beat_map = _question_beat_map(targets)
    gold_by_qn = _gold_by_question_number()
    rows: list[dict[str, Any]] = []

    for mode in modes:
        packets_by_qn = _packets_by_mode_and_hits(mode, max_hits)
        for question in iter_target_questions(targets):
            qn = int(question.get("question_number") or 0)
            planner_facing = is_planner_facing_question(question, retrieval_mode=mode)  # type: ignore[arg-type]
            if not planner_facing and not include_evaluator_only:
                continue
            packet = packets_by_qn.get(qn) if planner_facing else None
            rows.append(
                _build_row(
                    question=question,
                    mode=mode,  # type: ignore[arg-type]
                    beat_meta=beat_map.get(qn, {"beat_id": None, "beat_number": None}),
                    packet=packet,
                    max_hits=max_hits,
                    gold_question=gold_by_qn.get(qn),
                    include_generated_answer=include_generated_answer and planner_facing,
                )
            )
    return rows


def summarize_planner_surface_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    planner_rows = [r for r in rows if r.get("planner_facing")]
    evaluator_rows = [r for r in rows if not r.get("planner_facing")]
    coverage_counts: dict[str, int] = {}
    failure_counts: dict[str, int] = {}
    for row in planner_rows:
        cls = str(row.get("retrieval_sufficiency_class") or "unknown")
        coverage_counts[cls] = coverage_counts.get(cls, 0) + 1
        surface = str(row.get("next_failure_surface") or "unknown")
        failure_counts[surface] = failure_counts.get(surface, 0) + 1

    hard = {
        "prompt_payload_invalid": sum(1 for r in planner_rows if not r.get("prompt_payload_valid")),
        "forbidden_prompt_key_hits": sum(int(r.get("forbidden_prompt_key_hits") or 0) for r in planner_rows),
        "forbidden_prompt_value_hits": sum(int(r.get("forbidden_prompt_value_hits") or 0) for r in planner_rows),
        "known_context_gaps_leaked": sum(1 for r in planner_rows if r.get("known_context_gaps_leaked")),
        "generated_answer_control_leaks": sum(1 for r in planner_rows if r.get("generated_answer_control_leak")),
        "prior_only_support_leaks": sum(
            1
            for r in planner_rows
            if r.get("mode") == "prior_only" and r.get("support_context_rendered")
        ),
        "must_not_include_terms_in_prompt_payload": sum(
            1 for r in planner_rows if r.get("must_not_include_terms_in_prompt_payload")
        ),
    }

    support_required_rows = [r for r in planner_rows if r.get("support_required")]
    support_required_support_mode_rows = [r for r in support_required_rows if r.get("support_knowledge_allowed")]
    support_required_prior_only_rows = [r for r in support_required_rows if r.get("mode") == "prior_only"]

    next_pr = _recommend_next_pr(coverage_counts, failure_counts, hard)

    return {
        "schema": "dmb_pr65_planner_surface_summary_v1",
        "target_questions_total": 38,
        "planner_facing_questions": 37,
        "evaluator_only_questions": 1,
        "retrieval_modes": len(RETRIEVAL_MODES),
        "planner_surface_rows": len(planner_rows),
        "evaluator_only_rows": len(evaluator_rows),
        "hard_boundary_failures": hard,
        "coverage_by_class": coverage_counts,
        "failure_surface_counts": failure_counts,
        "support_required_rows": len(support_required_rows),
        "support_required_support_mode_rows": len(support_required_support_mode_rows),
        "support_required_prior_only_rows": len(support_required_prior_only_rows),
        "tier_a_ok_rows": sum(
            1
            for r in planner_rows
            if int(r.get("question_number") or 0) in TIER_A_QUESTIONS and r.get("next_failure_surface") == "ok_or_later_stage"
        ),
        "next_recommended_pr": next_pr,
    }


def _recommend_next_pr(
    coverage_counts: dict[str, int],
    failure_counts: dict[str, int],
    hard: dict[str, int],
) -> str:
    if any(hard.get(k, 0) for k in ("prompt_payload_invalid", "forbidden_prompt_key_hits", "forbidden_prompt_value_hits", "known_context_gaps_leaked", "generated_answer_control_leaks", "prior_only_support_leaks")):
        return "PR66 prompt/control boundary fix before retrieval expansion"
    support_missing = coverage_counts.get("support_expected_but_missing", 0)
    low_signal = coverage_counts.get("context_present_but_low_signal", 0)
    if support_missing >= low_signal and support_missing > 0:
        return "PR66 support-required retrieval/admission expansion"
    if low_signal > 0:
        return "PR66 prior-recap / entity continuity coverage expansion"
    if coverage_counts.get("needs_manual_review", 0) > 0:
        return "PR66 mixed-authority benchmark authoring and manual-review triage"
    return "PR66 targeted retrieval repair from pr65_failure_surface_counts.csv"


def build_next_pr_recommendations_markdown(summary: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    hard = summary.get("hard_boundary_failures") or {}
    coverage = summary.get("coverage_by_class") or {}
    lines = [
        "# Post-PR65 Planning Recommendations",
        "",
        f"Generated from `{summary.get('planner_surface_rows', 0)}` planner-facing mode rows.",
        "",
        "## Hard boundary status",
        "",
    ]
    for key, value in hard.items():
        lines.append(f"- `{key}`: {value}")
    lines.extend(["", "## Coverage classes (Tier B diagnostics)", ""])
    for key, value in sorted(coverage.items(), key=lambda kv: (-kv[1], kv[0])):
        lines.append(f"- `{key}`: {value}")
    lines.extend(["", "## Recommended next PR", "", f"**{summary.get('next_recommended_pr')}**", ""])

    support_missing = [r for r in rows if r.get("retrieval_sufficiency_class") == "support_expected_but_missing"]
    if support_missing:
        sample = sorted({int(r["question_number"]) for r in support_missing})[:12]
        lines.append(f"- Support-required gaps cluster on questions: {sample}")
    low_signal = [r for r in rows if r.get("retrieval_sufficiency_class") == "context_present_but_low_signal"]
    if low_signal:
        sample = sorted({int(r["question_number"]) for r in low_signal})[:12]
        lines.append(f"- Low-signal context rows include questions: {sample}")
    creative = coverage.get("creative_generation_no_strict_context_required", 0)
    if creative:
        lines.append(f"- `{creative}` creative-generation rows are boundary-clean; do not overfit strict retrieval there.")
    lines.append("")
    lines.append("PR65 is a baseline expansion PR. Unresolved retrieval insufficiency is expected and classified, not repaired here.")
    return "\n".join(lines)
