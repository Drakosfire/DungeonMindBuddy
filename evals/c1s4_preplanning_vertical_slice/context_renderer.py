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


def render_context_packet(packet: dict[str, Any]) -> dict[str, Any]:
    admitted = packet.get("admitted_context") or []
    mode = str(packet.get("retrieval_mode") or "")
    known_gaps = [str(x) for x in (packet.get("known_context_gaps") or [])]

    by_section: dict[str, list[dict[str, Any]]] = {k: [] for k, _ in SECTION_DEFS}
    for item in admitted:
        lane = str(item.get("presentation_lane") or "")
        kind = str(item.get("source_kind") or "")
        if lane in {"known_gap", "safety_constraint"}:
            by_section["known_gaps_and_safety_constraints"].append(item)
        elif lane == "support_knowledge" or kind == "support_knowledge_card":
            if mode != "prior_only":
                by_section["support_knowledge"].append(item)
        elif lane == "prior_campaign_memory" or kind == "session_memory":
            by_section["prior_campaign_memory"].append(item)
        elif lane in {"pc_timeline", "party_timeline"}:
            by_section["character_party_behavior"].append(item)
        elif lane in {"location_context", "worldbuilding"}:
            by_section["location_worldbuilding"].append(item)

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
            ref = str(i.get("ref") or i.get("unit_id") or "unknown")
            refs.append(ref)
            lines.append(f"- [{ref}] {_item_text(i)}")
            provenance_map[ref] = {
                "source_kind": i.get("source_kind"),
                "source_layer": i.get("source_layer"),
                "candidate_rank": i.get("candidate_rank"),
                "admitted_rank": i.get("admitted_rank"),
                "presentation_lane": i.get("presentation_lane"),
                "admission_reason": i.get("admission_reason"),
            }
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
    }
