from __future__ import annotations

from collections import Counter
from typing import Any

SYNTHETIC_PREP_PACKET_SCHEMA = "dmb_c1s4_synthetic_prep_packet_v1"

SECTION_QUESTION_MAP: dict[str, list[int]] = {
    "stone_bridge_aftermath": [1, 2, 3],
    "road_toward_mirathorn": [7, 8, 9],
    "hempholm_hook": [4, 5, 6],
    "arrival_at_crisis_site": [10, 11, 12],
    "visible_tree_investigation": [13, 14, 15],
    "local_social_pressure": [16, 17, 18],
    "tree_set_piece": [19, 20, 21],
    "first_victory_and_remains": [22, 23, 24],
    "celebration_and_decompression": [25, 26, 27],
    "deeper_horror_reveal": [28, 29, 30],
    "next_session_emergency": [31, 32, 33],
    "meta_and_safety": [34, 36, 37, 38],
}

SECTION_TITLES = {"stone_bridge_aftermath": "Stone Bridge Aftermath", "road_toward_mirathorn": "Road Toward Mirathorn", "hempholm_hook": "Hempholm Hook", "arrival_at_crisis_site": "Arrival at Crisis Site", "visible_tree_investigation": "Visible Tree Investigation", "local_social_pressure": "Local Social Pressure", "tree_set_piece": "Tree Set Piece", "first_victory_and_remains": "First Victory and Remains", "celebration_and_decompression": "Celebration and Decompression", "deeper_horror_reveal": "Deeper Horror Reveal", "next_session_emergency": "Next Session Emergency", "meta_and_safety": "Meta and Safety"}

FORBIDDEN_GRADING_FIELDS = {"oracle_score", "passed_oracle_grading", "matches_c1s4", "c1s4_recap_match", "observed_c1s4"}


def _as_list(v: Any) -> list[Any]:
    return list(v) if isinstance(v, list) else []


def summarize_authority_from_answer_packets(answer_packets: list[dict[str, Any]]) -> dict[str, Any]:
    labels = Counter(str(p.get("authority_label") or "unknown") for p in answer_packets)
    risks = Counter(str(p.get("oracle_risk") or "unknown") for p in answer_packets)
    return {"authority_label_counts": dict(sorted(labels.items())), "oracle_risk_counts": dict(sorted(risks.items()))}


def summarize_safety_from_answer_packets(answer_packets: list[dict[str, Any]]) -> dict[str, Any]:
    unsupported_claim_warnings = sum(1 for p in answer_packets if not (p.get("safety_checks") or {}).get("oracle_sensitive_terms_supported_or_absent", True))
    terms_present = [t for p in answer_packets for t in _as_list((p.get("safety_checks") or {}).get("must_not_include_terms_present"))]
    return {
        "unsupported_claim_warnings": unsupported_claim_warnings,
        "must_not_include_terms_present": terms_present,
        "packets_with_oracle_leakage": sum(1 for p in answer_packets if _as_list((p.get("oracle_leakage_check") or {}).get("forbidden_path_hits")) or _as_list((p.get("oracle_leakage_check") or {}).get("forbidden_session_hits"))),
    }


def build_synthetic_prep_packet(*, answer_packets: list[dict[str, Any]], skipped_questions: list[dict[str, Any]], retrieval_mode: str, generator: str) -> dict[str, Any]:
    packets_by_q = {int(p.get("question_number")): p for p in answer_packets if isinstance(p.get("question_number"), int)}
    sections = []
    packet_known_gaps: set[str] = set()
    packet_guardrails: set[str] = set()

    for section_id, qnums in SECTION_QUESTION_MAP.items():
        entries = []
        refs = []
        sec_gaps: set[str] = set()
        sec_guardrails: set[str] = set()
        sec_packets = []
        for qn in qnums:
            p = packets_by_q.get(qn)
            if not p:
                continue
            sec_packets.append(p)
            qid = str(p.get("question_id") or "")
            refs.append(qid)
            gaps = _as_list(p.get("known_context_gaps"))
            guardrails = _as_list(p.get("must_not_include_unless_sourced"))
            sec_gaps.update(str(g) for g in gaps)
            sec_guardrails.update(str(g) for g in guardrails)
            packet_known_gaps.update(str(g) for g in gaps)
            packet_guardrails.update(str(g) for g in guardrails)
            entries.append({
                "question_number": qn,
                "question_id": qid,
                "answer_text": p.get("answer_text"),
                "authority_label": p.get("authority_label"),
                "oracle_risk": p.get("oracle_risk"),
                "known_context_gaps": gaps,
                "must_not_include_unless_sourced": guardrails,
                "unsupported_claim_warnings": _as_list((p.get("safety_checks") or {}).get("must_not_include_terms_present")),
                "must_not_include_terms_present": _as_list((p.get("safety_checks") or {}).get("must_not_include_terms_present")),
                "expected_mode_behavior": p.get("expected_mode_behavior"),
            })

        sections.append({
            "section_id": section_id,
            "title": SECTION_TITLES[section_id],
            "question_numbers": qnums,
            "answer_packet_refs": refs,
            "summary": f"Generated from Q{qnums[0]}–Q{qnums[-1]} answer packets.",
            "prep_entries": entries,
            "section_known_gaps": sorted(sec_gaps),
            "section_guardrails": sorted(sec_guardrails),
            "section_authority_summary": summarize_authority_from_answer_packets(sec_packets),
        })

    oracle_path_hits = sorted({h for p in answer_packets for h in _as_list((p.get("oracle_leakage_check") or {}).get("forbidden_path_hits"))})
    oracle_session_hits = sorted({h for p in answer_packets for h in _as_list((p.get("oracle_leakage_check") or {}).get("forbidden_session_hits"))})

    return {
        "schema": SYNTHETIC_PREP_PACKET_SCHEMA,
        "campaign_id": "longmont-c1",
        "retrieval_mode": retrieval_mode,
        "generator": generator,
        "source_answer_packet_schema": "dmb_c1s4_answer_packet_v1",
        "prep_generation_status": "aggregated_from_generated_answer_packets",
        "oracle_visibility": "forbidden",
        "does_not_claim_observed_c1s4_match": True,
        "sections": sections,
        "known_gaps": sorted(packet_known_gaps),
        "must_not_include_unless_sourced": sorted(packet_guardrails),
        "authority_summary": summarize_authority_from_answer_packets(answer_packets),
        "safety_summary": summarize_safety_from_answer_packets(answer_packets),
        "skipped_questions": skipped_questions,
        "source_answer_packet_refs": [str(p.get("question_id")) for p in answer_packets if p.get("question_id")],
        "oracle_leakage_check": {"forbidden_path_hits": oracle_path_hits, "forbidden_session_hits": oracle_session_hits},
    }


def validate_synthetic_prep_packet(packet: dict[str, Any]) -> list[str]:
    errs: list[str] = []
    if packet.get("schema") != SYNTHETIC_PREP_PACKET_SCHEMA:
        errs.append("invalid schema")
    if not packet.get("retrieval_mode"):
        errs.append("retrieval_mode missing")
    if not packet.get("generator"):
        errs.append("generator missing")
    if packet.get("oracle_visibility") != "forbidden":
        errs.append("oracle_visibility must be forbidden")
    if packet.get("does_not_claim_observed_c1s4_match") is not True:
        errs.append("does_not_claim_observed_c1s4_match must be true")
    if not isinstance(packet.get("sections"), list) or not packet["sections"]:
        errs.append("sections missing")
    got_ids = {s.get("section_id") for s in _as_list(packet.get("sections"))}
    missing = set(SECTION_QUESTION_MAP) - got_ids
    if missing:
        errs.append(f"required sections missing: {sorted(missing)}")
    def _contains_forbidden_key(node: Any) -> bool:
        if isinstance(node, dict):
            if any(k in FORBIDDEN_GRADING_FIELDS for k in node):
                return True
            return any(_contains_forbidden_key(v) for v in node.values())
        if isinstance(node, list):
            return any(_contains_forbidden_key(v) for v in node)
        return False

    if _contains_forbidden_key(packet):
        errs.append("oracle grading fields must be absent")

    for section in _as_list(packet.get("sections")):
        qnums = _as_list(section.get("question_numbers"))
        if not qnums:
            errs.append(f"section {section.get('section_id')} missing question_numbers")
        if 35 in qnums:
            errs.append("Q35 must not appear in sections")
        entries = _as_list(section.get("prep_entries"))
        if not entries:
            errs.append(f"section {section.get('section_id')} missing prep_entries")
        for entry in entries:
            if int(entry.get("question_number", -1)) == 35:
                errs.append("Q35 must not appear in prep_entries")
            if _as_list(entry.get("must_not_include_terms_present")):
                if any(not row.get("supported", False) for row in _as_list(entry.get("must_not_include_terms_present"))):
                    errs.append("unsupported forbidden terms present")

    leak = packet.get("oracle_leakage_check") or {}
    if _as_list(leak.get("forbidden_path_hits")) or _as_list(leak.get("forbidden_session_hits")):
        errs.append("oracle leakage detected")
    if (packet.get("safety_summary") or {}).get("unsupported_claim_warnings", 0) > 0:
        errs.append("unsupported forbidden terms present")
    return errs
