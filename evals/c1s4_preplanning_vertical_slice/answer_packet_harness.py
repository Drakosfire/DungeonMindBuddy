from __future__ import annotations

from typing import Any

ANSWER_PACKET_SCHEMA = "dmb_c1s4_answer_packet_v1"


def build_stub_answer_packet(*, context_packet: dict[str, Any]) -> dict[str, Any]:
    oracle_check = context_packet.get("oracle_leakage_check") or {
        "forbidden_path_hits": [],
        "forbidden_session_hits": [],
    }
    known_gaps: list[str] = []
    packet = {
        "schema": ANSWER_PACKET_SCHEMA,
        "campaign_id": context_packet.get("campaign_id", "longmont-c1"),
        "question_number": context_packet.get("question_number"),
        "question_id": context_packet.get("question_id"),
        "question": context_packet.get("question"),
        "retrieval_mode": context_packet.get("retrieval_mode"),
        "source_context_packet_schema": context_packet.get("schema"),
        "answer_generation_status": "stubbed_not_generated",
        "answer_text": None,
        "structured_answer": None,
        "answer_product": list(context_packet.get("answer_product") or []),
        "authority_label": context_packet.get("authority_label"),
        "oracle_risk": context_packet.get("oracle_risk"),
        "expected_mode_behavior": context_packet.get("expected_mode_behavior"),
        "used_context_refs": [],
        "unused_context_refs": [],
        "known_context_gaps": known_gaps,
        "must_not_include_unless_sourced": list(context_packet.get("must_not_include_unless_sourced") or []),
        "authority_notes": {
            "retrieved_prior_recap_facts": [],
            "support_derived_suggestions": [],
            "creative_extrapolations": [],
            "known_gaps": list(known_gaps),
            "manual_gm_decisions_needed": [],
        },
        "safety_checks": {
            "answer_slot_was_empty_on_input": context_packet.get("answer_slot") is None,
            "no_oracle_context_detected": not (oracle_check.get("forbidden_path_hits") or oracle_check.get("forbidden_session_hits")),
            "must_not_include_terms_present": [],
            "unsupported_claim_warnings": [],
            "eval_only_fields_absent": all(
                field not in context_packet
                for field in [
                    "expected_retrieval_context_eval_only",
                    "expected_retrieval_modes",
                    "known_context_gaps",
                ]
            ),
        },
        "oracle_leakage_check": {
            "forbidden_path_hits": list(oracle_check.get("forbidden_path_hits") or []),
            "forbidden_session_hits": list(oracle_check.get("forbidden_session_hits") or []),
        },
    }
    return packet


def validate_answer_packet(packet: dict[str, Any]) -> list[str]:
    errs: list[str] = []
    if packet.get("schema") != ANSWER_PACKET_SCHEMA:
        errs.append("invalid schema")
    if packet.get("answer_generation_status") != "stubbed_not_generated":
        errs.append("answer_generation_status must be stubbed_not_generated")
    if packet.get("answer_text") is not None:
        errs.append("answer_text must be null")
    if packet.get("structured_answer") is not None:
        errs.append("structured_answer must be null")
    for required in ["question_id", "question_number", "retrieval_mode", "authority_label", "oracle_risk", "authority_notes", "safety_checks", "oracle_leakage_check"]:
        if packet.get(required) in (None, ""):
            errs.append(f"{required} is missing")
    if not isinstance(packet.get("used_context_refs"), list):
        errs.append("used_context_refs must be a list")
    if not isinstance(packet.get("unused_context_refs"), list):
        errs.append("unused_context_refs must be a list")
    leak = packet.get("oracle_leakage_check") or {}
    if leak.get("forbidden_path_hits"):
        errs.append("forbidden_path_hits must be empty")
    if leak.get("forbidden_session_hits"):
        errs.append("forbidden_session_hits must be empty")
    for forbidden_field in ["expected_retrieval_context_eval_only", "expected_retrieval_modes", "retrieved_context"]:
        if forbidden_field in packet:
            errs.append(f"{forbidden_field} must be absent")
    return errs


def summarize_answer_packets(*, answer_packets: list[dict[str, Any]], skipped_questions: list[dict[str, Any]], retrieval_mode: str) -> dict[str, Any]:
    oracle_path_hits = sorted({h for p in answer_packets for h in (p.get("oracle_leakage_check") or {}).get("forbidden_path_hits", [])})
    oracle_session_hits = sorted({h for p in answer_packets for h in (p.get("oracle_leakage_check") or {}).get("forbidden_session_hits", [])})
    return {
        "schema": "dmb_c1s4_step3_stub_answer_packet_summary_v1",
        "campaign_id": "longmont-c1",
        "retrieval_mode": retrieval_mode,
        "answer_generation_status": "stubbed_not_generated",
        "counts": {
            "context_packets_seen": len(answer_packets) + len(skipped_questions),
            "answer_packets_built": len(answer_packets),
            "questions_skipped": len(skipped_questions),
            "packets_with_oracle_leakage": sum(1 for p in answer_packets if (p.get("oracle_leakage_check") or {}).get("forbidden_path_hits") or (p.get("oracle_leakage_check") or {}).get("forbidden_session_hits")),
            "packets_with_forbidden_terms_present": sum(1 for p in answer_packets if (p.get("safety_checks") or {}).get("must_not_include_terms_present")),
        },
        "skipped_questions": skipped_questions,
        "oracle_leakage_check": {"forbidden_path_hits": oracle_path_hits, "forbidden_session_hits": oracle_session_hits},
        "answer_packets": answer_packets,
    }
