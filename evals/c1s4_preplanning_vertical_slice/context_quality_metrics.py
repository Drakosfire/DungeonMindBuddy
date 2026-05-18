from __future__ import annotations

from typing import Any

from evals.c1s4_preplanning_vertical_slice.context_admission import estimate_context_item_size

SCHEMA = "dmb_packet_quality_metrics_v1"
SUPPORT_KIND = "support_knowledge_card"
LEAK_PATH_TOKENS = ("evals/", "docs/", "gold/", "canvas_templates/", "artifacts/", "pr")
NAV_ONLY_TOKENS = (
    "retrieval keywords",
    "suggested reads",
    "cross-references",
    "npcs anchored here",
    "npc and social anchors",
)


def _as_list(value: Any) -> list[dict[str, Any]]:
    return value if isinstance(value, list) else []


def _item_ref(item: dict[str, Any]) -> str:
    return str(item.get("unit_id") or item.get("ref") or item.get("source_reference") or item.get("title") or "unknown")


def _item_text(item: dict[str, Any]) -> str:
    return " ".join(str(item.get(k) or "") for k in ["title", "snippet", "text", "source_reference", "source_recap_path", "source"]).lower()


def compute_packet_quality_metrics(*, row: dict[str, Any], packet: dict[str, Any] | None = None, gold_question: dict[str, Any] | None = None, rendered_context_packet: dict[str, Any] | None = None) -> dict[str, Any]:
    del gold_question
    pkt = packet or {}
    retrieved = _as_list(row.get("retrieved_context") or pkt.get("retrieved_context"))
    candidate = _as_list(row.get("candidate_context") or pkt.get("candidate_context") or retrieved)
    admitted = _as_list(row.get("admitted_context") or pkt.get("admitted_context") or retrieved)
    rendered = rendered_context_packet or row.get("rendered_context_packet") or {}
    sections = _as_list(rendered.get("sections"))
    provenance = rendered.get("provenance_map") if isinstance(rendered.get("provenance_map"), dict) else {}

    admitted_sizes = [estimate_context_item_size(i) for i in admitted]
    admitted_chars = sum(x[0] for x in admitted_sizes)
    admitted_tokens = sum(x[1] for x in admitted_sizes)
    rendered_chars = sum(int(s.get("chars") or 0) for s in sections)
    rendered_tokens = sum(int(s.get("estimated_tokens") or 0) for s in sections)

    lane_counts: dict[str, int] = {}
    lane_tokens: dict[str, int] = {}
    kind_counts_candidate: dict[str, int] = {}
    kind_counts_admitted: dict[str, int] = {}
    kind_tokens: dict[str, int] = {}
    nav_refs: list[str] = []
    noise_refs: list[str] = []
    leakage_paths: list[str] = []
    continuity_refs: list[str] = []

    support_candidate_rank = None
    support_admitted_rank = None
    support_count = 0
    support_tokens = 0

    for idx, item in enumerate(candidate, start=1):
        kind = str(item.get("source_kind") or "unknown")
        kind_counts_candidate[kind] = kind_counts_candidate.get(kind, 0) + 1
        if kind == SUPPORT_KIND and support_candidate_rank is None:
            support_candidate_rank = idx

    for idx, item in enumerate(admitted, start=1):
        kind = str(item.get("source_kind") or "unknown")
        lane = str(item.get("presentation_lane") or "unknown")
        chars, tokens = estimate_context_item_size(item)
        kind_counts_admitted[kind] = kind_counts_admitted.get(kind, 0) + 1
        kind_tokens[kind] = kind_tokens.get(kind, 0) + tokens
        lane_counts[lane] = lane_counts.get(lane, 0) + 1
        lane_tokens[lane] = lane_tokens.get(lane, 0) + tokens
        text = _item_text(item)
        ref = _item_ref(item)
        if kind == SUPPORT_KIND:
            support_count += 1
            support_tokens += tokens
            if support_admitted_rank is None:
                support_admitted_rank = idx
        if any(t in text for t in NAV_ONLY_TOKENS):
            nav_refs.append(ref)
        if "meta-session" in ref or "meta summary" in text:
            noise_refs.append(ref)
        source_path = str(item.get("source") or item.get("source_recap_path") or item.get("source_reference") or "").lower()
        if any(tok in source_path for tok in LEAK_PATH_TOKENS) and ("pr" not in source_path or "pr" in source_path and ".md" in source_path):
            leakage_paths.append(source_path)
        if "location_hub" in text and "npc" in text:
            continuity_refs.append(ref)

    required_total = int(row.get("required_context_groups") or 0)
    required_hit = int(row.get("required_context_groups_hit") or 0)
    required_admitted = []
    for grp in row.get("matched_groups", []) or []:
        required_admitted.extend(grp.get("matched_context_refs", []) or [])
    required_admitted = sorted({str(x) for x in required_admitted})

    rendered_required = [r for r in required_admitted if r in provenance]
    rendered_required_sections = sorted({str((provenance.get(r) or {}).get("rendered_section_id")) for r in rendered_required if (provenance.get(r) or {}).get("rendered_section_id")})

    known_gaps = [str(x) for x in row.get("known_context_gaps", []) or []]
    kg_idx = next((i for i, s in enumerate(sections, start=1) if str(s.get("section_id")) == "known_gaps_and_safety_constraints" and (s.get("refs") or [])), None)
    mode = str(row.get("retrieval_mode") or pkt.get("retrieval_mode") or "")
    unknown_count = lane_counts.get("unknown", 0)
    unknown_ratio = (unknown_count / len(admitted)) if admitted else 0.0
    support_leak = mode == "prior_only" and support_count > 0

    flags: list[str] = []
    if len(admitted) > 30:
        flags.append("high_admitted_count")
    if unknown_ratio > 0.5:
        flags.append("high_unknown_lane_ratio")
    if support_admitted_rank and support_admitted_rank > 20:
        flags.append("support_buried_after_rank_20")
    if support_leak:
        flags.append("prior_only_support_leakage")
    if known_gaps and (kg_idx is None or kg_idx > 2):
        flags.append("known_gaps_not_near_top")
    if rendered_tokens > 3500:
        flags.append("large_rendered_packet")
    if leakage_paths:
        flags.append("eval_or_plan_source_leakage")
    if nav_refs:
        flags.append("navigation_only_evidence_used")
    if continuity_refs:
        flags.append("location_hub_npc_continuity_risk")

    score = max(1, min(5, 5 - len(flags)))
    notes = []
    if support_admitted_rank and support_admitted_rank > 20:
        notes.append("support evidence admitted but buried after rank 20")
    if unknown_ratio > 0.5:
        notes.append("unknown lane ratio above 0.50")

    return {
        "schema": SCHEMA,
        "context_surfaces": {
            "retrieved_context_count": len(retrieved),
            "candidate_context_count": len(candidate),
            "admitted_context_count": len(admitted),
            "rendered_section_count": len(sections),
            "rendered_provenance_ref_count": len(provenance),
        },
        "budget": {
            "admitted_estimated_chars": admitted_chars,
            "admitted_estimated_tokens": admitted_tokens,
            "rendered_estimated_chars": rendered_chars,
            "rendered_estimated_tokens": rendered_tokens,
            "average_admitted_item_chars": (admitted_chars / len(admitted)) if admitted else 0,
            "average_admitted_item_tokens": (admitted_tokens / len(admitted)) if admitted else 0,
        },
        "source_kind": {
            "candidate_counts": kind_counts_candidate,
            "admitted_counts": kind_counts_admitted,
            "token_share": {k: (v / admitted_tokens if admitted_tokens else 0.0) for k, v in kind_tokens.items()},
            "support_card_count": kind_counts_admitted.get(SUPPORT_KIND, 0),
            "session_memory_count": kind_counts_admitted.get("session_memory", 0),
            "location_hub_count": sum(1 for i in admitted if "location_hub" in _item_text(i)),
            "npc_hub_count": sum(1 for i in admitted if "npc_hub" in _item_text(i) or "npc" in _item_text(i) and "hub" in _item_text(i)),
            "known_gap_count": sum(1 for i in admitted if str(i.get("presentation_lane") or "") == "known_gap"),
        },
        "presentation_lanes": {
            "lane_counts": lane_counts,
            "lane_token_share": {k: (v / admitted_tokens if admitted_tokens else 0.0) for k, v in lane_tokens.items()},
            "unknown_lane_count": unknown_count,
            "unknown_lane_ratio": unknown_ratio,
        },
        "required_context": {
            "total_required_groups": required_total,
            "hit_required_groups": required_hit,
            "missing_required_groups": max(0, required_total - required_hit),
            "required_refs_admitted": required_admitted,
            "required_refs_rendered": rendered_required,
            "rendered_sections_containing_required_refs": rendered_required_sections,
        },
        "support": {
            "support_allowed_for_mode": mode != "prior_only",
            "support_leakage_in_prior_only": support_leak,
            "first_support_candidate_rank": support_candidate_rank,
            "first_support_admitted_rank": support_admitted_rank,
            "support_burial_depth": support_admitted_rank,
            "support_token_share": (support_tokens / admitted_tokens if admitted_tokens else 0.0),
            "support_rendered_sections": sorted({str(v.get("rendered_section_id")) for k, v in provenance.items() if str(v.get("source_kind") or "") == SUPPORT_KIND and v.get("rendered_section_id")}),
        },
        "known_gaps": {
            "expected_known_gap_count": len(known_gaps),
            "hit_known_gap_count": len(row.get("known_gap_expectations_hit", []) or []),
            "known_gap_rendered_section_index": kg_idx,
            "known_gaps_near_top": bool(kg_idx is not None and kg_idx <= 2),
            "known_gap_token_share": next((float(s.get("estimated_tokens") or 0) / rendered_tokens for s in sections if str(s.get("section_id")) == "known_gaps_and_safety_constraints" and rendered_tokens), 0.0),
        },
        "hygiene": {
            "eval_or_plan_source_leakage": bool(leakage_paths),
            "leaking_source_paths": sorted(set(leakage_paths)),
            "navigation_only_evidence_count": len(nav_refs),
            "navigation_only_evidence_refs": sorted(set(nav_refs)),
            "location_hub_npc_continuity_risk_count": len(continuity_refs),
            "location_hub_npc_continuity_risk_refs": sorted(set(continuity_refs)),
        },
        "noise": {
            "meta_summary_count": len(noise_refs),
            "likely_noise_refs": sorted(set(noise_refs)),
            "likely_noise_count": len(noise_refs),
            "likely_noise_token_share": 0.0,
        },
        "flags": flags,
        "llm_usability": {"score_1_to_5": score, "notes": notes},
    }
