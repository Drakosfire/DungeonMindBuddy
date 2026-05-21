from __future__ import annotations

import math
from typing import Any

SCHEMA = "dmb_planner_context_render_v1"


SECTION_DEFS = [
    ("known_gaps_and_safety_constraints", "Known Gaps and Safety Constraints"),
    ("support_knowledge", "Support / Adaptation Context"),
    ("prior_campaign_memory", "Prior Campaign Memory"),
    ("character_party_behavior", "Character / Party Behavior Context"),
    ("location_worldbuilding", "Location / Worldbuilding Context"),
]


def _estimate_tokens(chars: int) -> int:
    return math.ceil(chars / 4)


def _item_text(item: dict[str, Any]) -> str:
    return str(item.get("snippet") or item.get("text") or item.get("title") or item.get("source_reference") or "")


def _item_ref(item: dict[str, Any]) -> str:
    return str(item.get("ref") or item.get("unit_id") or "unknown")


def _is_prior_memory_fallback(item: dict[str, Any]) -> bool:
    unit_id = str(item.get("unit_id") or item.get("ref") or "")
    if unit_id.startswith("u-L") or unit_id.startswith("meta-session-"):
        return True
    if item.get("session_number") is not None or item.get("source_recap_path"):
        return True
    return False


def _route_item_to_section(item: dict[str, Any], *, mode: str) -> tuple[str | None, str]:
    lane = str(item.get("presentation_lane") or "")
    kind = str(item.get("source_kind") or "")

    if lane in {"known_gap", "safety_constraint"}:
        return "known_gaps_and_safety_constraints", f"presentation_lane_{lane}"

    if lane == "support_knowledge" or kind == "support_knowledge_card":
        if mode == "prior_only":
            return None, "support_suppressed_in_prior_only"
        return "support_knowledge", "support_knowledge_lane_or_kind"

    if lane in {"pc_timeline", "party_timeline", "character_party_behavior"}:
        return "character_party_behavior", f"presentation_lane_{lane}"

    if lane in {"location_context", "worldbuilding", "location_worldbuilding"}:
        return "location_worldbuilding", f"presentation_lane_{lane}"

    if lane == "prior_campaign_memory":
        return "prior_campaign_memory", "presentation_lane_prior_campaign_memory"

    if kind == "session_memory" or _is_prior_memory_fallback(item):
        return "prior_campaign_memory", "prior_memory_fallback"

    return "prior_campaign_memory", "unknown_fallback"


def _provenance_entry(*, item: dict[str, Any], ref: str, section_id: str, route_reason: str) -> dict[str, Any]:
    return {
        "ref": ref,
        "unit_id": item.get("unit_id"),
        "source_kind": item.get("source_kind"),
        "source_layer": item.get("source_layer"),
        "source_path": item.get("source_path"),
        "source_recap_path": item.get("source_recap_path"),
        "source_reference": item.get("source_reference"),
        "subject_class": item.get("subject_class"),
        "subject_id": item.get("subject_id"),
        "section_heading": item.get("section_heading"),
        "planner_lane_hint": item.get("planner_lane_hint"),
        "presentation_lane": item.get("presentation_lane"),
        "admission_budget_lane": item.get("admission_budget_lane"),
        "candidate_rank": item.get("candidate_rank"),
        "admitted_rank": item.get("admitted_rank"),
        "rendered_section_id": section_id,
        "admission_reason": item.get("admission_reason"),
        "merge_reason": item.get("merge_reason"),
        "merge_family": item.get("merge_family"),
        "route_reason": route_reason,
    }


def provenance_matches_expected(prov: dict[str, Any], expected_path_or_unit_id: str) -> bool:
    needle = expected_path_or_unit_id.lower()
    refs = [
        prov.get("source_path"),
        prov.get("source_recap_path"),
        prov.get("source_reference"),
        prov.get("unit_id"),
        prov.get("ref"),
    ]
    return any(needle in str(x or "").lower() for x in refs)


def render_context_packet(packet: dict[str, Any]) -> dict[str, Any]:
    admitted = packet.get("admitted_context") or []
    mode = str(packet.get("retrieval_mode") or "")
    known_gaps = [str(x) for x in (packet.get("known_context_gaps") or [])]

    by_section: dict[str, list[dict[str, Any]]] = {k: [] for k, _ in SECTION_DEFS}
    route_diagnostics: list[dict[str, Any]] = []

    for item in admitted:
        section_id, route_reason = _route_item_to_section(item, mode=mode)
        if section_id is None:
            continue
        by_section[section_id].append(item)
        route_diagnostics.append(
            {
                "unit_id": item.get("unit_id"),
                "source_path": item.get("source_path"),
                "presentation_lane": item.get("presentation_lane"),
                "admission_budget_lane": item.get("admission_budget_lane"),
                "rendered_section_id": section_id,
                "route_reason": route_reason,
            }
        )

    if known_gaps:
        for gap in known_gaps:
            by_section["known_gaps_and_safety_constraints"].append({"ref": f"known_gap:{gap}", "snippet": gap})

    sections = []
    provenance_map: dict[str, dict[str, Any]] = {}
    for sid, title in SECTION_DEFS:
        items = by_section[sid]
        lines = []
        refs: list[str] = []
        for i in items:
            ref = _item_ref(i)
            refs.append(ref)
            lines.append(f"- [{ref}] {_item_text(i)}")
            if str(ref).startswith("known_gap:"):
                route_reason = "known_gap"
            else:
                _, route_reason = _route_item_to_section(i, mode=mode)
            provenance_map[ref] = _provenance_entry(item=i, ref=ref, section_id=sid, route_reason=route_reason)
        text = "\n".join(lines) if lines else "- (none)"
        chars = len(text)
        sections.append({"section_id": sid, "title": title, "refs": refs, "chars": chars, "estimated_tokens": _estimate_tokens(chars), "text": text})

    summary = {s["section_id"]: {"items": len(s["refs"]), "chars": s["chars"], "estimated_tokens": s["estimated_tokens"]} for s in sections}
    est_tokens = sum(s["estimated_tokens"] for s in sections)
    rendered_text = "\n\n".join([
        "# Planning Question\n\n" + str(packet.get("question") or ""),
        "# Retrieval and Authority Summary\n\n" + "\n".join([
            f"- Retrieval mode: {packet.get('retrieval_mode')}",
            f"- Admission policy: {packet.get('admission_policy')}",
            "- Grading context: admitted_context",
            f"- Support knowledge allowed: {'yes' if mode != 'prior_only' else 'no'}",
            "- Oracle material allowed: no",
            f"- Candidate depth: {((packet.get('admission_budget') or {}).get('candidate_depth'))}",
            f"- Admitted context items: {len(admitted)}",
            f"- Estimated rendered tokens: {est_tokens}",
        ]),
    ] + [f"# {s['title']}\n\n{s['text']}" for s in sections] + [
        "# Provenance Map\n\n" + "\n".join([f"- {k}: {v}" for k, v in sorted(provenance_map.items())])
    ])

    section_route_counts = {sid: len(by_section[sid]) for sid, _ in SECTION_DEFS}

    return {
        "schema": SCHEMA,
        "question_number": packet.get("question_number"),
        "question_id": packet.get("question_id"),
        "retrieval_mode": packet.get("retrieval_mode"),
        "admission_policy": packet.get("admission_policy"),
        "rendered_text": rendered_text,
        "sections": sections,
        "section_summary": summary,
        "provenance_map": provenance_map,
        "render_diagnostics": {
            "schema": "dmb_context_render_diagnostics_v1",
            "section_route_counts": section_route_counts,
            "items": route_diagnostics,
        },
    }
