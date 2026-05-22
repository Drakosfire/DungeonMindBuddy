from __future__ import annotations

import json
from typing import Any

from evals.c1s4_preplanning_vertical_slice.context_admission import render_context_item_for_budget
from evals.c1s4_preplanning_vertical_slice.context_classification import infer_context_subject_class
from evals.c1s4_preplanning_vertical_slice.context_renderer import render_context_packet
from evals.c1s4_preplanning_vertical_slice.expected_context_benchmark import (
    RETRIEVAL_MODES,
    context_item_satisfies_lane_aware_group,
    grade_question_packet,
    load_expected_context_gold,
    match_context_item,
)
from evals.c1s4_preplanning_vertical_slice.step2_build_question_context_packets import build_summary
from evals.c1s4_preplanning_vertical_slice.visibility_provenance import is_planner_visible_for_c1s4_preplanning

ROW_SCHEMA = "dmb_pr67_required_group_admission_row_v1"
DIAGNOSTICS_SCHEMA = "dmb_pr67_required_group_admission_diagnostics_v1"

Q3_DISTANCE_MATCH = {"text_contains_all": ["mirathorn", "week"]}
TIER_A_QUESTIONS = frozenset({1, 3, 5})


def _norm(text: Any) -> str:
    return " ".join(str(text or "").lower().split())


def _context_item_ref(item: dict[str, Any]) -> str:
    return str(item.get("unit_id") or item.get("source_path") or item.get("source_recap_path") or "unknown")


def _first_match_rank(items: list[dict[str, Any]], match: dict[str, Any]) -> tuple[int | None, dict[str, Any] | None]:
    for idx, item in enumerate(items, start=1):
        if match_context_item(item, match):
            return idx, item
    return None, None


def _rendered_section_for_ref(rendered: dict[str, Any], ref: str) -> str | None:
    for section in rendered.get("sections") or []:
        if not isinstance(section, dict):
            continue
        refs = [str(r) for r in (section.get("refs") or [])]
        if ref in refs:
            return str(section.get("section_id") or section.get("title") or "")
    return None


def _admission_rejection_for_ref(
    *,
    ref: str,
    candidate_rank: int | None,
    admission_decision_diagnostics: dict[str, Any] | None,
    visibility_excluded: bool,
) -> str:
    if visibility_excluded:
        return "visibility_excluded"
    if candidate_rank is None:
        return "not_matched"
    if not admission_decision_diagnostics:
        return "not_admittable"
    for attempt in admission_decision_diagnostics.get("attempts") or []:
        if int(attempt.get("candidate_rank") or -1) != candidate_rank:
            continue
        if attempt.get("admitted"):
            return "admitted"
        return str(attempt.get("reason") or "not_admitted")
    return "outside_candidate_depth"


def _miss_root_cause(
    *,
    candidate_rank: int | None,
    admitted: bool,
    rendered: bool,
    lane_aware_accepted: bool,
    legacy_match: bool,
    visibility_excluded: bool,
    admission_rejection: str,
) -> str:
    if visibility_excluded:
        return "visibility_exclusion"
    if candidate_rank is None:
        return "retrieval_rank"
    if not legacy_match:
        return "retrieval_rank"
    if not admitted:
        if admission_rejection in {"lane_remaining_too_small", "lane_max_exhausted", "total_spillover_exhausted", "no_lane_state"}:
            return "lane_budget"
        if admission_rejection in {"not_admittable_planner_evidence", "prior_only_support_suppressed"}:
            return "source_kind_mismatch"
        return "admission_budget"
    if not rendered:
        return "render"
    if not lane_aware_accepted:
        return "strict_gold_lane_mismatch"
    return "ok"


def build_required_group_row(
    *,
    packet: dict[str, Any],
    gold_question: dict[str, Any],
    mode: str,
    group: dict[str, Any],
) -> dict[str, Any]:
    qn = int(packet.get("question_number") or 0)
    group_id = str(group.get("group_id") or "")
    match_spec = group.get("match") or {}
    candidates = packet.get("candidate_context") or []
    admitted = packet.get("admitted_context") or []
    admission_diag = packet.get("admission_decision_diagnostics") or {}

    cand_rank, cand_item = _first_match_rank(candidates, match_spec)
    cand_matches = [item for item in candidates if match_context_item(item, match_spec)]
    visibility_excluded = False
    if cand_item is not None and not is_planner_visible_for_c1s4_preplanning(cand_item):
        visibility_excluded = True

    adm_rank, adm_item = _first_match_rank(admitted, match_spec)
    admitted_flag = adm_item is not None

    rendered_packet = render_context_packet(packet)
    render_ref = _context_item_ref(adm_item) if adm_item else (_context_item_ref(cand_item) if cand_item else None)
    rendered_section = _rendered_section_for_ref(rendered_packet, render_ref) if render_ref else None
    rendered_flag = rendered_section is not None

    grade = grade_question_packet(packet=packet, gold_question=gold_question, retrieval_mode=mode, top_k=9)  # type: ignore[arg-type]
    lane_results = (grade.get("lane_aware_diagnostics") or {}).get("required_group_results") or []
    lane_row = next((r for r in lane_results if r.get("group_id") == group_id), {})
    lane_aware_accepted = bool(lane_row.get("ok"))
    rejected = (lane_row.get("rejected_matches") or [])[:1]
    lane_rejection = str(rejected[0].get("reason")) if rejected else None

    legacy_matches = [m for m in (grade.get("matched_groups") or []) if m.get("group_id") == group_id]
    legacy_match = bool(legacy_matches and legacy_matches[0].get("ok"))

    admission_rejection = _admission_rejection_for_ref(
        ref=_context_item_ref(cand_item) if cand_item else "",
        candidate_rank=cand_rank,
        admission_decision_diagnostics=admission_diag,
        visibility_excluded=visibility_excluded,
    )

    first_item = cand_item or {}
    return {
        "schema": ROW_SCHEMA,
        "question_number": qn,
        "question_id": packet.get("question_id"),
        "mode": mode,
        "group_id": group_id,
        "required_lane": group.get("required_lane"),
        "expected_rendered_section": group.get("expected_rendered_section"),
        "match_surface": {
            "candidate_match_count": len(cand_matches),
            "first_candidate_rank": cand_rank,
            "first_candidate_ref": _context_item_ref(first_item) if first_item else None,
            "first_candidate_source_kind": first_item.get("source_kind"),
            "first_candidate_subject_class": infer_context_subject_class(first_item) if first_item else None,
            "first_candidate_presentation_lane": first_item.get("presentation_lane"),
            "visibility_excluded": visibility_excluded,
        },
        "admission_surface": {
            "admitted": admitted_flag,
            "first_admitted_rank": adm_rank,
            "admission_rejection_reason": admission_rejection,
            "admission_policy": packet.get("admission_policy"),
        },
        "render_surface": {
            "rendered": rendered_flag,
            "rendered_section": rendered_section,
        },
        "grading_surface": {
            "legacy_match": legacy_match,
            "lane_aware_accepted": lane_aware_accepted,
            "lane_aware_rejection_reason": lane_rejection,
            "grading_context_kind": grade.get("grading_context_kind"),
            "effective_grading_surface": grade.get("grading_surface_labels", {}).get("effective_grading_surface"),
        },
        "miss_root_cause": _miss_root_cause(
            candidate_rank=cand_rank,
            admitted=admitted_flag,
            rendered=rendered_flag,
            lane_aware_accepted=lane_aware_accepted,
            legacy_match=legacy_match,
            visibility_excluded=visibility_excluded,
            admission_rejection=admission_rejection,
        ),
    }


def build_q3_prior_distance_probe(*, packet: dict[str, Any], query_variant_diagnostics: dict[str, Any] | None = None) -> dict[str, Any]:
    match = Q3_DISTANCE_MATCH
    candidates = packet.get("candidate_context") or []
    admitted = packet.get("admitted_context") or []
    rendered = render_context_packet(packet)
    rendered_refs: set[str] = set()
    rendered_section: str | None = None
    for section in rendered.get("sections") or []:
        if not isinstance(section, dict):
            continue
        for ref in section.get("refs") or []:
            rendered_refs.add(str(ref))
            if match_context_item({"unit_id": ref, "snippet": section.get("text") or ""}, match):
                rendered_section = str(section.get("section_id") or "")

    literal_rank, literal_item = None, None
    alias_rank, alias_item = None, None
    if query_variant_diagnostics:
        for variant in query_variant_diagnostics.get("variants") or []:
            hits = variant.get("hits") or []
            for idx, hit in enumerate(hits, start=1):
                if not match_context_item(hit, match):
                    continue
                variant_kind = str(variant.get("variant_kind") or variant.get("kind") or "")
                if variant_kind == "literal":
                    if literal_rank is None or idx < literal_rank:
                        literal_rank, literal_item = idx, hit
                elif "alias" in variant_kind or variant_kind == "route_distance_alias":
                    if alias_rank is None or idx < alias_rank:
                        alias_rank, alias_item = idx, hit

    merged_rank, merged_item = _first_match_rank(candidates, match)
    admitted_rank, admitted_item = _first_match_rank(admitted, match)

    failure_stage = "ok"
    if merged_rank is None:
        failure_stage = "retrieval"
    elif admitted_rank is None:
        failure_stage = "admission"
    elif not rendered_section:
        failure_stage = "render"
    else:
        grade_row = None
        failure_stage = "grading"

    first = admitted_item or merged_item or literal_item or alias_item
    snippet = render_context_item_for_budget(first)[:240] if first else None

    return {
        "literal_first_rank": literal_rank,
        "route_alias_first_rank": alias_rank,
        "merged_candidate_first_rank": merged_rank,
        "admitted_rank": admitted_rank,
        "rendered_section": rendered_section,
        "first_ref": _context_item_ref(first) if first else None,
        "first_snippet": snippet,
        "failure_stage": failure_stage if merged_rank is None or admitted_rank is None or not rendered_section else "ok",
    }


def build_pr67_required_group_diagnostics(*, max_hits: int = 50) -> dict[str, Any]:
    gold = load_expected_context_gold()
    gold_by_q = {int(q["question_number"]): q for q in gold.get("questions", []) if q.get("question_number") is not None}
    rows: list[dict[str, Any]] = []
    q3_probes: dict[str, Any] = {}

    for mode in RETRIEVAL_MODES:
        summary = build_summary(mode=mode, max_hits=max_hits)  # type: ignore[arg-type]
        for packet in summary.get("packets") or []:
            qn = int(packet.get("question_number") or 0)
            gold_q = gold_by_q.get(qn)
            if gold_q is None:
                continue
            exp = (gold_q.get("expectations_by_mode") or {}).get(mode) or {}
            for group in exp.get("required_context_groups") or []:
                rows.append(build_required_group_row(packet=packet, gold_question=gold_q, mode=mode, group=group))
            if qn == 3:
                q3_probes[mode] = build_q3_prior_distance_probe(
                    packet=packet,
                    query_variant_diagnostics=packet.get("query_variant_diagnostics"),
                )

    tier_a_rows = [r for r in rows if int(r.get("question_number") or 0) in TIER_A_QUESTIONS]
    miss_causes: dict[str, int] = {}
    for row in tier_a_rows:
        if row.get("grading_surface", {}).get("lane_aware_accepted"):
            continue
        cause = str(row.get("miss_root_cause") or "unknown")
        miss_causes[cause] = miss_causes.get(cause, 0) + 1

    return {
        "schema": DIAGNOSTICS_SCHEMA,
        "tier_a_questions": sorted(TIER_A_QUESTIONS),
        "row_count": len(rows),
        "tier_a_row_count": len(tier_a_rows),
        "tier_a_miss_root_causes": miss_causes,
        "q3_prior_distance_probe_by_mode": q3_probes,
        "rows": rows,
    }
