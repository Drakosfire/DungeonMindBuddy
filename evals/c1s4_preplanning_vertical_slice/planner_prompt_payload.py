from __future__ import annotations

from typing import Any

from evals.c1s4_preplanning_vertical_slice.beat_question_answer_harness import (
    TARGET_PATH,
    expected_known_context_gaps_eval_only,
)
from evals.c1s4_preplanning_vertical_slice.context_renderer import render_context_packet

PLANNER_PROMPT_PAYLOAD_SCHEMA = "dmb_c1s4_planner_prompt_payload_v1"
EVALUATOR_CONTROL_METADATA_SCHEMA = "dmb_c1s4_evaluator_control_metadata_v1"

FORBIDDEN_PROMPT_KEYS = frozenset(
    {
        "authority_label",
        "oracle_risk",
        "expected_mode_behavior",
        "answer_product",
        "must_not_include_unless_sourced",
        "expected_known_context_gaps_eval_only",
        "known_context_gaps",
        "expected_retrieval_context_eval_only",
        "expected_retrieval_modes",
        "required_context_groups",
        "forbidden_context_groups",
        "expectations_by_mode",
        "target_artifact",
        "target_artifact_visibility",
        "source_target_artifact",
        "gold_path",
    }
)

FORBIDDEN_PROMPT_VALUE_TOKENS = (
    "c1s4_expected_context_gold.json",
    "c1s4_beat_question_targets.json",
    "evals/c1s4_preplanning_vertical_slice/gold",
)

GENERIC_GROUNDING_INSTRUCTIONS = (
    "Use only the provided context.",
    "If the provided context does not establish a fact, say it is not established.",
    "Do not invent named locations, route details, NPCs, encounter facts, or source-specific lore.",
    "Separate sourced facts from suggested GM extrapolation.",
    "Do not include facts, named entities, route details, encounter details, or source-specific lore unless they are supported by the provided context.",
)


def find_forbidden_prompt_material(value: Any, *, path: str = "$") -> list[str]:
    hits: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if str(key) in FORBIDDEN_PROMPT_KEYS:
                hits.append(f"{child_path}: forbidden key {key!r}")
            hits.extend(find_forbidden_prompt_material(child, path=child_path))
        return hits
    if isinstance(value, list):
        for idx, child in enumerate(value):
            hits.extend(find_forbidden_prompt_material(child, path=f"{path}[{idx}]"))
        return hits
    if isinstance(value, str):
        for token in FORBIDDEN_PROMPT_VALUE_TOKENS:
            if token in value:
                hits.append(f"{path}: forbidden value token {token!r}")
    return hits


def _sanitize_for_prompt(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _sanitize_for_prompt(v) for k, v in value.items() if k not in FORBIDDEN_PROMPT_KEYS}
    if isinstance(value, list):
        return [_sanitize_for_prompt(v) for v in value]
    if isinstance(value, str):
        for token in FORBIDDEN_PROMPT_VALUE_TOKENS:
            if token in value:
                return value.replace(token, "[redacted-eval-artifact-path]")
        return value
    return value


def _support_knowledge_allowed(retrieval_mode: str) -> bool:
    return retrieval_mode != "prior_only"


def _build_instructions(*, support_knowledge_allowed: bool, rendered_context: dict[str, Any]) -> list[str]:
    instructions = list(GENERIC_GROUNDING_INSTRUCTIONS)
    if not support_knowledge_allowed:
        instructions.append("Do not use adaptation or support-only material.")
    else:
        support_refs = []
        for section in rendered_context.get("sections") or []:
            if section.get("section_id") == "support_knowledge" and section.get("refs"):
                support_refs = list(section.get("refs") or [])
                break
        if support_refs:
            instructions.append(
                "Support knowledge appears in the rendered context; you may use it but must keep it distinguishable from prior campaign memory."
            )
        else:
            instructions.append(
                "Support knowledge is allowed for this mode, but none appears in the rendered context; do not invent support-only material."
            )
    return instructions


def build_planner_prompt_payload(
    *,
    context_packet: dict[str, Any],
    rendered_context_packet: dict[str, Any] | None = None,
) -> dict[str, Any]:
    rendered = rendered_context_packet or render_context_packet(context_packet)
    retrieval_mode = str(context_packet.get("retrieval_mode") or "")
    support_allowed = _support_knowledge_allowed(retrieval_mode)
    admitted = context_packet.get("admitted_context") or []
    safe_rendered = _sanitize_for_prompt(
        {
            "schema": rendered.get("schema"),
            "rendered_text": rendered.get("rendered_text"),
            "sections": rendered.get("sections"),
            "section_summary": rendered.get("section_summary"),
            "provenance_map": rendered.get("provenance_map"),
        }
    )
    section_counts = {
        str(k): int(v.get("items", 0) if isinstance(v, dict) else v)
        for k, v in (rendered.get("section_summary") or {}).items()
    }
    if not section_counts:
        section_counts = (rendered.get("render_diagnostics") or {}).get("section_route_counts") or {}

    payload = {
        "schema": PLANNER_PROMPT_PAYLOAD_SCHEMA,
        "campaign_id": context_packet.get("campaign_id", "longmont-c1"),
        "question_number": context_packet.get("question_number"),
        "question_id": context_packet.get("question_id"),
        "question": context_packet.get("question"),
        "retrieval_mode": retrieval_mode,
        "support_knowledge_allowed": support_allowed,
        "oracle_material_allowed": False,
        "instructions": _build_instructions(support_knowledge_allowed=support_allowed, rendered_context=rendered),
        "rendered_context": safe_rendered,
        "source_derived_context_gaps": _sanitize_for_prompt(list(context_packet.get("source_derived_context_gaps") or [])),
        "context_summary": {
            "admitted_context_items": len(admitted),
            "estimated_rendered_tokens": sum(
                int(s.get("estimated_tokens") or 0) for s in (rendered.get("sections") or []) if isinstance(s, dict)
            ),
            "section_counts": section_counts,
        },
    }
    return payload


def build_evaluator_control_metadata(
    *,
    context_packet: dict[str, Any],
    question: dict[str, Any] | None = None,
) -> dict[str, Any]:
    question = question or {}
    return {
        "schema": EVALUATOR_CONTROL_METADATA_SCHEMA,
        "campaign_id": context_packet.get("campaign_id", "longmont-c1"),
        "question_number": context_packet.get("question_number"),
        "question_id": context_packet.get("question_id"),
        "target_artifact_visibility": context_packet.get("target_artifact_visibility", "forbidden"),
        "source_target_artifact": str(TARGET_PATH),
        "authority_label": context_packet.get("authority_label") or question.get("authority_label"),
        "oracle_risk": context_packet.get("oracle_risk") or question.get("oracle_risk"),
        "expected_mode_behavior": context_packet.get("expected_mode_behavior")
        or question.get("expected_mode_behavior"),
        "answer_product": list(context_packet.get("answer_product") or question.get("answer_product") or []),
        "must_not_include_unless_sourced": list(
            context_packet.get("must_not_include_unless_sourced") or question.get("must_not_include_unless_sourced") or []
        ),
        "expected_known_context_gaps_eval_only": expected_known_context_gaps_eval_only(question)
        if question
        else [],
        "oracle_leakage_check": {
            "forbidden_path_hits": list(
                (context_packet.get("oracle_leakage_check") or {}).get("forbidden_path_hits") or []
            ),
            "forbidden_session_hits": list(
                (context_packet.get("oracle_leakage_check") or {}).get("forbidden_session_hits") or []
            ),
        },
    }


def validate_planner_prompt_payload(payload: dict[str, Any]) -> list[str]:
    errs: list[str] = []
    if payload.get("schema") != PLANNER_PROMPT_PAYLOAD_SCHEMA:
        errs.append("invalid schema")
    for required in ("question_id", "question", "retrieval_mode", "rendered_context", "instructions"):
        if payload.get(required) in (None, ""):
            errs.append(f"{required} is missing")
    rendered = payload.get("rendered_context")
    if not isinstance(rendered, dict) or not str(rendered.get("rendered_text") or "").strip():
        errs.append("rendered_context.rendered_text must be populated")
    errs.extend(find_forbidden_prompt_material(payload))
    return errs


def validate_evaluator_control_metadata(metadata: dict[str, Any]) -> list[str]:
    errs: list[str] = []
    if metadata.get("schema") != EVALUATOR_CONTROL_METADATA_SCHEMA:
        errs.append("invalid schema")
    for required in (
        "question_id",
        "authority_label",
        "oracle_risk",
        "expected_mode_behavior",
        "must_not_include_unless_sourced",
        "oracle_leakage_check",
    ):
        if metadata.get(required) is None and required != "must_not_include_unless_sourced":
            errs.append(f"{required} is missing")
    if not isinstance(metadata.get("must_not_include_unless_sourced"), list):
        errs.append("must_not_include_unless_sourced must be a list")
    return errs
