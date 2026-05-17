from __future__ import annotations

import math
from typing import Any

from evals.c1s4_preplanning_vertical_slice.context_admission import estimate_context_item_size

SCHEMA = "dmb_packet_quality_metrics_v1"
SUPPORT_KIND = "support_knowledge_card"


def _token_count(item: dict[str, Any]) -> int:
    _, tokens = estimate_context_item_size(item)
    return int(tokens)


def _counts_by(items: list[dict[str, Any]], key: str, fallback: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for item in items:
        value = str(item.get(key) or fallback)
        out[value] = out.get(value, 0) + 1
    return out


def _token_share(items: list[dict[str, Any]], key: str, fallback: str) -> dict[str, float]:
    totals: dict[str, int] = {}
    total = 0
    for item in items:
        k = str(item.get(key) or fallback)
        t = _token_count(item)
        totals[k] = totals.get(k, 0) + t
        total += t
    if total <= 0:
        return {k: 0.0 for k in totals}
    return {k: round(v / total, 4) for k, v in totals.items()}


def compute_packet_quality_metrics(*, row: dict[str, Any], gold_question: dict[str, Any] | None = None) -> dict[str, Any]:
    retrieved = row.get("retrieved_context", []) or []
    candidate = row.get("candidate_context", []) or []
    admitted = row.get("admitted_context", []) or []
    rendered = row.get("rendered_context_packet") or {}
    sections = rendered.get("sections", []) if isinstance(rendered, dict) else []

    admitted_chars = sum(estimate_context_item_size(x)[0] for x in admitted)
    admitted_tokens = sum(_token_count(x) for x in admitted)
    rendered_chars = len(str(rendered))
    rendered_tokens = math.ceil(rendered_chars / 4)

    source_counts_admitted = _counts_by(admitted, "source_kind", "session_memory")
    lane_counts = _counts_by(admitted, "presentation_lane", "unknown")
    unknown_count = lane_counts.get("unknown", 0)
    unknown_ratio = round((unknown_count / len(admitted)), 4) if admitted else 0.0

    mode_expectations = {}
    if isinstance(gold_question, dict):
        mode_expectations = (gold_question.get("expectations_by_mode") or {}).get(str(row.get("retrieval_mode")), {})
    required_groups = mode_expectations.get("required_context_groups", [])
    known_gap_terms = mode_expectations.get("expected_known_gaps_contains_any", [])

    support_candidates = [i for i, x in enumerate(candidate, start=1) if str(x.get("source_kind")) == SUPPORT_KIND]
    support_admitted = [i for i, x in enumerate(admitted, start=1) if str(x.get("source_kind")) == SUPPORT_KIND]

    required_rendered_sections: list[str] = []
    required_refs_admitted: list[str] = []
    for grp in row.get("matched_groups", []) or []:
        if grp.get("ok"):
            required_refs_admitted.extend(grp.get("matched_context_refs", []))
    if required_refs_admitted:
        req_set = set(required_refs_admitted)
        for section in sections:
            sec_name = str(section.get("section") or "unknown")
            block = str(section)
            if any(ref in block for ref in req_set):
                required_rendered_sections.append(sec_name)

    known_gap_idx = None
    for idx, section in enumerate(sections):
        heading = str(section.get("heading") or section.get("section") or "").lower()
        if "known" in heading and "gap" in heading:
            known_gap_idx = idx
            break

    flags: list[str] = []
    if len(admitted) > 30:
        flags.append("high_admitted_count")
    if unknown_ratio > 0.50:
        flags.append("high_unknown_lane_ratio")
    if support_admitted and support_admitted[0] > 20:
        flags.append("support_buried_after_rank_20")
    if row.get("retrieval_mode") == "prior_only" and len(support_admitted) > 0:
        flags.append("prior_only_support_leakage")
    if known_gap_terms and known_gap_idx is not None and known_gap_idx > 0:
        flags.append("known_gaps_not_near_top")
    if rendered_tokens > 2500:
        flags.append("large_rendered_packet")

    score = 5
    if int(row.get("required_context_groups", 0)) > int(row.get("required_context_groups_hit", 0)):
        score -= 3
    if row.get("forbidden_context_groups_hit"):
        score -= 5
    for f in ["support_buried_after_rank_20", "high_unknown_lane_ratio", "high_admitted_count", "known_gaps_not_near_top", "large_rendered_packet"]:
        if f in flags:
            score -= 1
    score = min(5, max(1, score))

    return {
        "schema": SCHEMA,
        "context_surfaces": {
            "retrieved_context_count": len(retrieved),
            "candidate_context_count": len(candidate),
            "admitted_context_count": len(admitted),
            "rendered_section_count": len(sections),
        },
        "budget": {
            "admitted_estimated_chars": admitted_chars,
            "admitted_estimated_tokens": admitted_tokens,
            "rendered_estimated_chars": rendered_chars,
            "rendered_estimated_tokens": rendered_tokens,
            "average_admitted_item_chars": round(admitted_chars / len(admitted), 2) if admitted else 0,
            "average_admitted_item_tokens": round(admitted_tokens / len(admitted), 2) if admitted else 0,
        },
        "source_kind": {
            "source_kind_counts_in_candidate_context": _counts_by(candidate, "source_kind", "session_memory"),
            "source_kind_counts_in_admitted_context": source_counts_admitted,
            "source_kind_estimated_token_share": _token_share(admitted, "source_kind", "session_memory"),
            "support_knowledge_count": source_counts_admitted.get(SUPPORT_KIND, 0),
            "session_memory_count": source_counts_admitted.get("session_memory", 0),
            "known_gap_count": len(known_gap_terms),
        },
        "presentation_lanes": {
            "presentation_lane_counts": lane_counts,
            "presentation_lane_token_share": _token_share(admitted, "presentation_lane", "unknown"),
            "unknown_lane_count": unknown_count,
            "unknown_lane_ratio": unknown_ratio,
        },
        "required_context": {
            "required_groups_total": int(row.get("required_context_groups", 0)),
            "required_groups_hit": int(row.get("required_context_groups_hit", 0)),
            "first_required_candidate_rank": None,
            "first_required_admitted_rank": None,
            "required_refs_admitted": sorted(set(required_refs_admitted)),
            "required_refs_rendered": sorted(set(required_refs_admitted)),
            "rendered_sections_with_required_context": sorted(set(required_rendered_sections)),
        },
        "support": {
            "support_allowed": row.get("retrieval_mode") != "prior_only",
            "support_leakage_in_prior_only": row.get("retrieval_mode") == "prior_only" and len(support_admitted) > 0,
            "support_refs_in_candidate_context": len(support_candidates),
            "support_refs_admitted": len(support_admitted),
            "first_support_candidate_rank": support_candidates[0] if support_candidates else None,
            "first_support_admitted_rank": support_admitted[0] if support_admitted else None,
            "support_burial_depth": (support_admitted[0] - 1) if support_admitted else None,
            "support_token_share": _token_share(admitted, "source_kind", "session_memory").get(SUPPORT_KIND, 0.0),
            "support_rendered_sections": [str(s.get("section") or "unknown") for s in sections if "support" in str(s.get("section") or "").lower()],
        },
        "known_gaps": {
            "known_gap_expectations_total": len(known_gap_terms),
            "known_gap_expectations_hit": len(row.get("known_gap_expectations_hit", [])),
            "known_gap_rendered_section_index": known_gap_idx,
            "known_gaps_near_top": known_gap_idx == 0 if known_gap_idx is not None else False,
            "known_gap_token_share": _token_share(admitted, "source_kind", "session_memory").get("known_gap", 0.0),
        },
        "noise": {
            "meta_summary_count": sum(1 for x in admitted if "meta" in str(x.get("unit_id") or "").lower()),
            "likely_noise_refs": [str(x.get("unit_id") or x.get("source_reference") or "") for x in admitted if "meta" in str(x.get("unit_id") or "").lower()],
            "likely_noise_count": sum(1 for x in admitted if "meta" in str(x.get("unit_id") or "").lower()),
            "likely_noise_token_share": 0.0,
        },
        "flags": flags,
        "llm_usability": {"score_1_to_5": score, "notes": []},
    }
