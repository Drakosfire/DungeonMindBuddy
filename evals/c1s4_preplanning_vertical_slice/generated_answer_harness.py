from __future__ import annotations

import json
from typing import Any

from evals.c1s4_preplanning_vertical_slice.answer_packet_harness import ANSWER_PACKET_SCHEMA, build_stub_answer_packet


def _context_refs(context_packet: dict[str, Any]) -> tuple[list[str], list[str]]:
    refs = [str(i.get("unit_id")) for i in (context_packet.get("retrieved_context") or []) if i.get("unit_id")]
    used = refs[:3] if refs else []
    unused = refs[3:] if len(refs) > 3 else []
    return used, unused


def _supports_term(term: str, context_packet: dict[str, Any]) -> bool:
    needle = term.lower()
    for item in context_packet.get("retrieved_context") or []:
        hay = " ".join(str(item.get(k, "")) for k in ["title", "snippet", "source", "source_layer", "unit_id"]).lower()
        if needle in hay:
            return True
    return False


def generate_answer_packet(*, context_packet: dict[str, Any], retrieval_mode: str, generator: str = "template_stub") -> dict[str, Any]:
    if generator != "template_stub":
        raise ValueError(f"unsupported generator: {generator}")

    packet = build_stub_answer_packet(context_packet=context_packet)
    used_refs, unused_refs = _context_refs(context_packet)
    known_gaps = list(packet.get("known_context_gaps") or [])
    guardrails = list(packet.get("must_not_include_unless_sourced") or [])
    authority = str(packet.get("authority_label") or "unknown")
    expected_behavior = str(packet.get("expected_mode_behavior") or "")
    support_missing = retrieval_mode == "prior_only" and authority == "support_knowledge_required"

    packet["answer_generation_status"] = "generated"
    packet["answer_text"] = (
        f"Generated with {generator} in {retrieval_mode} mode. "
        f"Authority requirement: {authority}. "
        f"Retrieved context refs used: {used_refs if used_refs else 'none'}. "
        f"Known gaps: {known_gaps if known_gaps else ['none listed']}. "
        + (
            "This is prior_only for a support-required question, so the answer remains generic and admits missing support. "
            if support_missing
            else "This answer may use planner-visible support context where available. "
        )
        + f"Expected behavior: {expected_behavior}. Guardrails preserved in packet metadata."
    )
    packet["structured_answer"] = {
        "summary": packet["answer_text"],
        "retrieved_facts_used": used_refs,
        "support_suggestions_used": [r for r in used_refs if r.startswith("support:")],
        "creative_extrapolations": ["generic/archetype-level framing applied"] if "generic" in expected_behavior or "archetype" in expected_behavior else [],
        "known_gaps": known_gaps,
        "manual_gm_decisions_needed": [g for g in known_gaps if any(k in g.lower() for k in ["route", "canon", "manual"])],
        "oracle_risk_notes": ["No C1S4 oracle context used; planner-visible context only."],
    }
    packet["used_context_refs"] = used_refs
    packet["unused_context_refs"] = unused_refs
    packet["authority_notes"]["retrieved_prior_recap_facts"] = ["session-memory context available"] if any(r.startswith("session:") for r in used_refs) else []
    packet["authority_notes"]["support_derived_suggestions"] = ["support knowledge context available"] if any(r.startswith("support:") for r in used_refs) else []
    packet["authority_notes"]["creative_extrapolations"] = packet["structured_answer"]["creative_extrapolations"]
    packet["authority_notes"]["known_gaps"] = known_gaps
    packet["authority_notes"]["manual_gm_decisions_needed"] = packet["structured_answer"]["manual_gm_decisions_needed"]

    must_not_include_terms_present: list[dict[str, Any]] = []
    composite = f"{packet['answer_text']} {json.dumps(packet['structured_answer'], sort_keys=True)}".lower()
    for term in guardrails:
        present = str(term).lower() in composite
        if not present:
            continue
        supported = _supports_term(str(term), context_packet)
        must_not_include_terms_present.append(
            {
                "term": term,
                "supported": supported,
                "reason": "term appears in generated answer and is supported by retrieved context" if supported else "term appears in generated answer but not retrieved context",
            }
        )

    packet["safety_checks"].update(
        {
            "must_not_include_terms_present": must_not_include_terms_present,
            "forbidden_terms_checked": True,
            "oracle_sensitive_terms_supported_or_absent": all(t.get("supported") for t in must_not_include_terms_present),
            "eval_only_fields_absent": all(
                field not in packet
                for field in ["expected_retrieval_context_eval_only", "expected_retrieval_modes", "retrieved_context"]
            ),
        }
    )
    return packet


def validate_generated_answer_packet(packet: dict[str, Any]) -> list[str]:
    errs: list[str] = []
    if packet.get("schema") != ANSWER_PACKET_SCHEMA:
        errs.append("invalid schema")
    if packet.get("answer_generation_status") != "generated":
        errs.append("answer_generation_status must be generated")
    if not isinstance(packet.get("answer_text"), str) or not packet.get("answer_text"):
        errs.append("answer_text must be populated")
    if not isinstance(packet.get("structured_answer"), dict):
        errs.append("structured_answer must be populated object")
    leak = packet.get("oracle_leakage_check") or {}
    if leak.get("forbidden_path_hits") or leak.get("forbidden_session_hits"):
        errs.append("oracle leakage detected")
    safety = packet.get("safety_checks") or {}
    if not safety.get("eval_only_fields_absent", False):
        errs.append("eval_only_fields_absent must be true")
    if not safety.get("oracle_sensitive_terms_supported_or_absent", False):
        errs.append("unsupported forbidden terms present")
    for forbidden_field in ["expected_retrieval_context_eval_only", "expected_retrieval_modes", "retrieved_context"]:
        if forbidden_field in packet:
            errs.append(f"{forbidden_field} must be absent")
    return errs
