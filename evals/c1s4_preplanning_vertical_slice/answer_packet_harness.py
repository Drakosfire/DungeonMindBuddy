from __future__ import annotations

from typing import Any

from evals.c1s4_preplanning_vertical_slice.planner_prompt_payload import (
    EVALUATOR_CONTROL_METADATA_SCHEMA,
    PLANNER_PROMPT_PAYLOAD_SCHEMA,
    build_evaluator_control_metadata,
    build_planner_prompt_payload,
    find_forbidden_prompt_material,
    validate_evaluator_control_metadata,
    validate_planner_prompt_payload,
)

ANSWER_PACKET_SCHEMA = "dmb_c1s4_answer_packet_v1"

_FORBIDDEN_ANSWER_TOP_LEVEL_KEYS = frozenset(
    {
        "authority_label",
        "oracle_risk",
        "expected_mode_behavior",
        "answer_product",
        "must_not_include_unless_sourced",
        "known_context_gaps",
        "expected_retrieval_context_eval_only",
        "expected_retrieval_modes",
        "retrieved_context",
    }
)


def build_stub_answer_packet(
    *,
    context_packet: dict[str, Any] | None = None,
    planner_prompt_payload: dict[str, Any] | None = None,
    evaluator_control_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if context_packet is not None:
        if planner_prompt_payload is None:
            planner_prompt_payload = build_planner_prompt_payload(context_packet=context_packet)
        if evaluator_control_metadata is None:
            evaluator_control_metadata = build_evaluator_control_metadata(context_packet=context_packet)
    if planner_prompt_payload is None or evaluator_control_metadata is None:
        raise ValueError("planner_prompt_payload and evaluator_control_metadata are required")

    prompt_errs = validate_planner_prompt_payload(planner_prompt_payload)
    meta_errs = validate_evaluator_control_metadata(evaluator_control_metadata)
    oracle_check = evaluator_control_metadata.get("oracle_leakage_check") or {
        "forbidden_path_hits": [],
        "forbidden_session_hits": [],
    }

    return {
        "schema": ANSWER_PACKET_SCHEMA,
        "campaign_id": planner_prompt_payload.get("campaign_id", "longmont-c1"),
        "question_number": planner_prompt_payload.get("question_number"),
        "question_id": planner_prompt_payload.get("question_id"),
        "question": planner_prompt_payload.get("question"),
        "retrieval_mode": planner_prompt_payload.get("retrieval_mode"),
        "source_planner_prompt_payload_schema": planner_prompt_payload.get("schema"),
        "answer_generation_status": "stubbed_not_generated",
        "answer_text": None,
        "structured_answer": None,
        "used_context_refs": [],
        "unused_context_refs": [],
        "source_derived_context_gaps_used": [],
        "evaluator_control_metadata": evaluator_control_metadata,
        "evaluator_control_metadata_ref": {
            "schema": EVALUATOR_CONTROL_METADATA_SCHEMA,
            "present_for_scoring": True,
        },
        "authority_notes": {
            "retrieved_prior_recap_facts": [],
            "support_derived_suggestions": [],
            "creative_extrapolations": [],
            "known_gaps": [],
            "manual_gm_decisions_needed": [],
        },
        "safety_checks": {
            "answer_slot_was_empty_on_input": True,
            "planner_prompt_payload_valid": not prompt_errs,
            "evaluator_control_metadata_valid": not meta_errs,
            "no_control_metadata_in_prompt_payload": not find_forbidden_prompt_material(planner_prompt_payload),
            "no_gold_artifact_paths_in_prompt_payload": not any(
                "forbidden value token" in hit for hit in find_forbidden_prompt_material(planner_prompt_payload)
            ),
            "no_oracle_context_detected": not (
                oracle_check.get("forbidden_path_hits") or oracle_check.get("forbidden_session_hits")
            ),
            "must_not_include_terms_present": [],
            "unsupported_claim_warnings": [],
            "eval_only_fields_absent": True,
            "oracle_sensitive_terms_supported_or_absent": True,
        },
    }


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
    for forbidden in _FORBIDDEN_ANSWER_TOP_LEVEL_KEYS:
        if forbidden in packet:
            errs.append(f"{forbidden} must be absent from answer packet")
    for required in ["question_id", "question_number", "retrieval_mode", "evaluator_control_metadata", "safety_checks"]:
        if packet.get(required) in (None, ""):
            errs.append(f"{required} is missing")
    if not isinstance(packet.get("used_context_refs"), list):
        errs.append("used_context_refs must be a list")
    if not isinstance(packet.get("unused_context_refs"), list):
        errs.append("unused_context_refs must be a list")
    meta = packet.get("evaluator_control_metadata")
    if isinstance(meta, dict):
        errs.extend(validate_evaluator_control_metadata(meta))
    else:
        errs.append("evaluator_control_metadata must be an object")
    prompt_schema = packet.get("source_planner_prompt_payload_schema")
    if prompt_schema != PLANNER_PROMPT_PAYLOAD_SCHEMA:
        errs.append("source_planner_prompt_payload_schema must reference planner prompt payload")
    safety = packet.get("safety_checks") or {}
    if not safety.get("planner_prompt_payload_valid", False):
        errs.append("planner_prompt_payload_valid must be true")
    if not safety.get("no_control_metadata_in_prompt_payload", False):
        errs.append("no_control_metadata_in_prompt_payload must be true")
    return errs


def summarize_answer_packets(*, answer_packets: list[dict[str, Any]], skipped_questions: list[dict[str, Any]], retrieval_mode: str) -> dict[str, Any]:
    oracle_path_hits = sorted(
        {
            h
            for p in answer_packets
            for h in ((p.get("evaluator_control_metadata") or {}).get("oracle_leakage_check") or {}).get(
                "forbidden_path_hits", []
            )
        }
    )
    oracle_session_hits = sorted(
        {
            h
            for p in answer_packets
            for h in ((p.get("evaluator_control_metadata") or {}).get("oracle_leakage_check") or {}).get(
                "forbidden_session_hits", []
            )
        }
    )
    return {
        "schema": "dmb_c1s4_step3_stub_answer_packet_summary_v1",
        "campaign_id": "longmont-c1",
        "retrieval_mode": retrieval_mode,
        "answer_generation_status": "stubbed_not_generated",
        "counts": {
            "context_packets_seen": len(answer_packets) + len(skipped_questions),
            "answer_packets_built": len(answer_packets),
            "questions_skipped": len(skipped_questions),
            "packets_with_oracle_leakage": sum(
                1
                for p in answer_packets
                if ((p.get("evaluator_control_metadata") or {}).get("oracle_leakage_check") or {}).get(
                    "forbidden_path_hits"
                )
                or ((p.get("evaluator_control_metadata") or {}).get("oracle_leakage_check") or {}).get(
                    "forbidden_session_hits"
                )
            ),
            "packets_with_forbidden_terms_present": sum(
                1 for p in answer_packets if (p.get("safety_checks") or {}).get("must_not_include_terms_present")
            ),
        },
        "skipped_questions": skipped_questions,
        "oracle_leakage_check": {"forbidden_path_hits": oracle_path_hits, "forbidden_session_hits": oracle_session_hits},
        "answer_packets": answer_packets,
    }
