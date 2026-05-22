from __future__ import annotations

from typing import Any

from evals.c1s4_preplanning_vertical_slice.answer_packet_harness import ANSWER_PACKET_SCHEMA, build_stub_answer_packet
from evals.c1s4_preplanning_vertical_slice.planner_prompt_payload import (
    build_evaluator_control_metadata,
    build_planner_prompt_payload,
    find_forbidden_prompt_material,
    validate_planner_prompt_payload,
)

_CONTROL_LEAK_PHRASES = (
    "expected behavior:",
    "authority requirement:",
    "oracle_risk",
)


def _rendered_context_refs(planner_prompt_payload: dict[str, Any]) -> tuple[list[str], list[str]]:
    rendered = planner_prompt_payload.get("rendered_context") or {}
    refs: list[str] = []
    for section in rendered.get("sections") or []:
        if not isinstance(section, dict):
            continue
        if section.get("section_id") == "support_knowledge" and planner_prompt_payload.get("retrieval_mode") == "prior_only":
            continue
        refs.extend(str(r) for r in (section.get("refs") or []) if r)
    deduped: list[str] = []
    for ref in refs:
        if ref not in deduped:
            deduped.append(ref)
    used = deduped[:3]
    unused = deduped[3:]
    return used, unused


def _supports_term(term: str, planner_prompt_payload: dict[str, Any]) -> bool:
    needle = term.lower()
    rendered = planner_prompt_payload.get("rendered_context") or {}
    hay = str(rendered.get("rendered_text") or "").lower()
    if needle in hay:
        return True
    for prov in (rendered.get("provenance_map") or {}).values():
        if not isinstance(prov, dict):
            continue
        blob = " ".join(str(prov.get(k) or "") for k in ("snippet", "source_path", "unit_id", "title")).lower()
        if needle in blob:
            return True
    return False


def _apply_must_not_include_safety(
    *,
    packet: dict[str, Any],
    planner_prompt_payload: dict[str, Any],
    evaluator_control_metadata: dict[str, Any],
) -> None:
    guardrails = list(evaluator_control_metadata.get("must_not_include_unless_sourced") or [])
    composite = f"{packet['answer_text']} {packet['structured_answer'].get('summary', '')}".lower()
    must_not_include_terms_present: list[dict[str, Any]] = []
    for term in guardrails:
        present = str(term).lower() in composite
        if not present:
            continue
        supported = _supports_term(str(term), planner_prompt_payload)
        must_not_include_terms_present.append(
            {
                "term": term,
                "supported": supported,
                "reason": "term appears in generated answer and is supported by rendered context"
                if supported
                else "term appears in generated answer but not supported by rendered context",
            }
        )
    packet["safety_checks"].update(
        {
            "must_not_include_terms_present": must_not_include_terms_present,
            "forbidden_terms_checked": True,
            "oracle_sensitive_terms_supported_or_absent": all(t.get("supported") for t in must_not_include_terms_present),
        }
    )


def generate_answer_packet(
    *,
    planner_prompt_payload: dict[str, Any] | None = None,
    evaluator_control_metadata: dict[str, Any] | None = None,
    retrieval_mode: str | None = None,
    context_packet: dict[str, Any] | None = None,
    generator: str = "template_stub",
) -> dict[str, Any]:
    if generator != "template_stub":
        raise ValueError(f"unsupported generator: {generator}")

    if context_packet is not None:
        if planner_prompt_payload is None:
            planner_prompt_payload = build_planner_prompt_payload(context_packet=context_packet)
        if evaluator_control_metadata is None:
            evaluator_control_metadata = build_evaluator_control_metadata(context_packet=context_packet)
    if planner_prompt_payload is None or evaluator_control_metadata is None:
        raise ValueError("planner_prompt_payload and evaluator_control_metadata are required")

    prompt_errs = validate_planner_prompt_payload(planner_prompt_payload)
    if prompt_errs:
        raise ValueError(f"invalid planner_prompt_payload: {prompt_errs}")

    mode = str(retrieval_mode or planner_prompt_payload.get("retrieval_mode") or "")
    packet = build_stub_answer_packet(
        planner_prompt_payload=planner_prompt_payload,
        evaluator_control_metadata=evaluator_control_metadata,
    )
    used_refs, unused_refs = _rendered_context_refs(planner_prompt_payload)
    source_gaps = list(planner_prompt_payload.get("source_derived_context_gaps") or [])
    gap_ids = [str(g.get("gap_id")) for g in source_gaps if isinstance(g, dict) and g.get("gap_id")]

    gap_note = (
        f" Source-derived gaps listed: {gap_ids}."
        if gap_ids
        else " No source-derived route gaps were listed in the prompt payload."
    )
    packet["answer_generation_status"] = "generated"
    packet["answer_text"] = (
        f"Generated with {generator} in {mode} mode. "
        f"Used rendered context refs: {used_refs if used_refs else 'none'}. "
        f"No facts are established beyond the rendered context.{gap_note}"
    )
    packet["structured_answer"] = {
        "summary": packet["answer_text"],
        "retrieved_facts_used": used_refs,
        "support_suggestions_used": [r for r in used_refs if r.startswith("support:")],
        "creative_extrapolations": [],
        "source_derived_context_gaps_used": gap_ids,
        "known_gaps": gap_ids,
        "manual_gm_decisions_needed": [],
        "notes": ["Answer generated from planner_prompt_payload only; evaluator labels were not injected."],
    }
    packet["used_context_refs"] = used_refs
    packet["unused_context_refs"] = unused_refs
    packet["source_derived_context_gaps_used"] = gap_ids
    packet["authority_notes"]["retrieved_prior_recap_facts"] = (
        ["rendered prior-campaign context available"] if used_refs else []
    )
    packet["authority_notes"]["support_derived_suggestions"] = (
        ["rendered support context available"] if any(r.startswith("support:") for r in used_refs) else []
    )
    packet["authority_notes"]["known_gaps"] = gap_ids

    _apply_must_not_include_safety(
        packet=packet,
        planner_prompt_payload=planner_prompt_payload,
        evaluator_control_metadata=evaluator_control_metadata,
    )
    packet["safety_checks"]["planner_prompt_payload_valid"] = True
    packet["safety_checks"]["no_control_metadata_in_prompt_payload"] = not find_forbidden_prompt_material(
        planner_prompt_payload
    )
    packet["safety_checks"]["eval_only_fields_absent"] = True
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
    for forbidden in (
        "authority_label",
        "oracle_risk",
        "expected_mode_behavior",
        "must_not_include_unless_sourced",
        "known_context_gaps",
        "expected_retrieval_context_eval_only",
        "expected_retrieval_modes",
        "retrieved_context",
    ):
        if forbidden in packet:
            errs.append(f"{forbidden} must be absent")
    meta = packet.get("evaluator_control_metadata") or {}
    answer_lower = str(packet.get("answer_text") or "").lower()
    for phrase in _CONTROL_LEAK_PHRASES:
        if phrase in answer_lower:
            errs.append(f"answer_text leaks control metadata phrase: {phrase}")
    if str(meta.get("oracle_risk") or "").lower() and str(meta.get("oracle_risk") or "").lower() in answer_lower:
        errs.append("answer_text leaks oracle_risk label")
    safety = packet.get("safety_checks") or {}
    if not safety.get("planner_prompt_payload_valid", False):
        errs.append("planner_prompt_payload_valid must be true")
    if not safety.get("no_control_metadata_in_prompt_payload", False):
        errs.append("no_control_metadata_in_prompt_payload must be true")
    if not safety.get("oracle_sensitive_terms_supported_or_absent", False):
        errs.append("unsupported forbidden terms present")
    return errs
