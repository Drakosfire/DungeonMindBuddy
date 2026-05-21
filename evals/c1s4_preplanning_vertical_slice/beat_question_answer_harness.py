from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

QuestionRetrievalMode = Literal[
    "prior_only",
    "prior_plus_support_content_only",
    "prior_plus_support_content_plus_lexical_hints",
]

PACKET_SCHEMA = "dmb_c1s4_question_context_packet_v1"
TARGET_PATH = Path(__file__).resolve().parent / "gold/c1s4_beat_question_targets.json"


def load_beat_question_targets(path: Path | None = None) -> dict[str, Any]:
    return json.loads((path or TARGET_PATH).read_text(encoding="utf-8"))


def iter_target_questions(targets: dict[str, Any]) -> list[dict[str, Any]]:
    questions: list[dict[str, Any]] = []
    for beat in targets.get("beats", []):
        questions.extend(beat.get("questions", []))
    questions.extend(targets.get("meta_questions", []))
    return sorted(questions, key=lambda q: int(q.get("question_number", 0)))


def is_planner_facing_question(question: dict[str, Any], *, retrieval_mode: QuestionRetrievalMode) -> bool:
    mode_map = question.get("expected_retrieval_modes") or {}
    return mode_map.get(retrieval_mode) != "evaluator_only_not_planner_facing"


def expected_behavior_for_mode(question: dict[str, Any], retrieval_mode: QuestionRetrievalMode) -> str:
    mode_map = question.get("expected_retrieval_modes") or {}
    return str(mode_map.get(retrieval_mode) or "")


def summarize_authority(retrieved_context: list[dict[str, Any]]) -> dict[str, int]:
    counts = {
        "session_memory": 0,
        "source_module": 0,
        "adaptation_planning": 0,
        "world_canon": 0,
        "campaign_stateful_reference": 0,
        "support_gap": 0,
        "manual_support_synthesis": 0,
        "unknown": 0,
    }
    for item in retrieved_context:
        if item.get("source_kind") == "support_knowledge_card":
            layer = str(item.get("source_layer") or "unknown")
            counts[layer if layer in counts else "unknown"] += 1
        else:
            counts["session_memory"] += 1
    return counts


def expected_known_context_gaps_eval_only(question: dict[str, Any]) -> list[str]:
    """Gold/target known gaps for evaluator grading only — never planner-facing."""
    return list(question.get("known_context_gaps") or [])


def build_question_context_packet(*, question: dict[str, Any], retrieval_mode: QuestionRetrievalMode, retrieved_context: list[dict[str, Any]], oracle_leakage_check: dict[str, list[Any]]) -> dict[str, Any]:
    packet = {
        "schema": PACKET_SCHEMA,
        "campaign_id": "longmont-c1",
        "question_number": question.get("question_number"),
        "question_id": question.get("question_id"),
        "question": question.get("question"),
        "retrieval_mode": retrieval_mode,
        "planner_visibility": "allowed_packet",
        "target_artifact_visibility": "forbidden",
        "authority_label": question.get("authority_label"),
        "oracle_risk": question.get("oracle_risk"),
        "expected_mode_behavior": expected_behavior_for_mode(question, retrieval_mode),
        "answer_product": question.get("answer_product") or [],
        "must_not_include_unless_sourced": question.get("must_not_include_unless_sourced") or [],
        "retrieved_context": retrieved_context,
        "authority_summary": summarize_authority(retrieved_context),
        "oracle_leakage_check": oracle_leakage_check,
        "answer_slot": None,
    }
    return packet


def validate_packet(packet: dict[str, Any]) -> list[str]:
    errs: list[str] = []
    if packet.get("schema") != PACKET_SCHEMA:
        errs.append("invalid schema")
    if packet.get("planner_visibility") != "allowed_packet":
        errs.append("planner_visibility must be allowed_packet")
    if packet.get("target_artifact_visibility") != "forbidden":
        errs.append("target_artifact_visibility must be forbidden")
    if packet.get("answer_slot") is not None:
        errs.append("answer_slot must be null")
    if "expected_retrieval_context_eval_only" in packet:
        errs.append("expected_retrieval_context_eval_only must be absent")
    if "expected_retrieval_modes" in packet:
        errs.append("expected_retrieval_modes must be absent")
    if "known_context_gaps" in packet:
        errs.append("known_context_gaps is evaluator-only and must not appear in planner packet")
    if not isinstance(packet.get("retrieved_context"), list):
        errs.append("retrieved_context must be a list")
    if "oracle_leakage_check" not in packet:
        errs.append("oracle_leakage_check must be present")
    return errs
