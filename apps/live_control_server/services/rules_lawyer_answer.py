"""Evidence-bounded structured synthesis through GenerationEngine."""

from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Protocol

from generationengine import GenerationClient, TextRequest

from apps.live_control_server.models.rules_lawyer_answer import RulesAnswer, RulesAnswerResponse
from apps.live_control_server.models.rules_query import RulesQueryPacket
from src.model_policy import load_buddy_model_policy


ANSWER_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["answer", "citation_evidence_ref_ids", "support_status", "needs_more_evidence", "reason"],
    "properties": {
        "answer": {"type": "string"},
        "citation_evidence_ref_ids": {"type": "array", "items": {"type": "string"}},
        "support_status": {"type": "string", "enum": ["supported", "insufficient_evidence"]},
        "needs_more_evidence": {"type": "boolean"},
        "reason": {"type": "string"},
    },
}


class StructuredGenerator(Protocol):
    async def generate_structured(self, request: TextRequest) -> Any: ...


def answer_model() -> str:
    policy = load_buddy_model_policy(strict=True)
    role = policy.get("actions", {}).get("ruleslawyer_response_synthesis")
    model = policy.get("models", {}).get(role)
    if not isinstance(model, str) or not model.strip():
        raise ValueError("Rules Lawyer synthesis model is not configured")
    return model


def unavailable(packet: RulesQueryPacket, reason: str) -> RulesAnswerResponse:
    return RulesAnswerResponse(packet=packet, answer=RulesAnswer(
        status="unavailable" if packet.status in {"rules_space_unavailable", "downstream_failure"} else "insufficient_evidence",
        needs_more_evidence=True, reason=reason,
    ))


async def synthesize_rules_answer(
    *, question: str, packet: RulesQueryPacket, generator: StructuredGenerator | None = None,
) -> RulesAnswerResponse:
    if packet.status != "success" or not packet.evidence:
        return unavailable(packet, f"retrieval_{packet.status}")

    evidence = [
        {"evidence_ref_id": item.evidence_ref_id, "excerpt": item.excerpt,
         "source_locator": item.source_locator, "locator": item.locator}
        for item in packet.evidence
    ]
    trace = "rules-answer:" + sha256(json.dumps(
        [packet.query_id, packet.trace.search_result_digest, evidence],
        sort_keys=True, ensure_ascii=False,
    ).encode()).hexdigest()[:32]
    request = TextRequest(
        provider="openai", model=answer_model(), temperature=None,
        system_prompt=(
            "Answer the user's rules question using only the supplied evidence excerpts. "
            "Never use remembered rulebook knowledge. Cite evidence_ref_id values exactly. "
            "If the excerpts cannot support the answer, say so and set support_status to "
            "insufficient_evidence. Do not make unsupported claims."
        ),
        user_prompt=json.dumps({"question": question, "evidence": evidence}, ensure_ascii=False),
        json_schema=ANSWER_SCHEMA, schema_name="rules_lawyer_cited_answer_v1",
    )
    try:
        client = generator if generator is not None else GenerationClient.from_env()
        result = await client.generate_structured(request)
        parsed = getattr(result, "parsed", None)
        if not isinstance(parsed, dict):
            return unavailable(packet, "generation_unparsed")
        cited = parsed.get("citation_evidence_ref_ids")
        allowed = {item.evidence_ref_id for item in packet.evidence}
        if not isinstance(cited, list) or any(not isinstance(id_, str) or id_ not in allowed for id_ in cited):
            return unavailable(packet, "unknown_citation")
        status = parsed.get("support_status")
        answer = str(parsed.get("answer") or "").strip()
        if status == "supported" and (not answer or not cited):
            return unavailable(packet, "answer_lacks_support")
        if status not in {"supported", "insufficient_evidence"}:
            return unavailable(packet, "invalid_support_status")
        if status == "insufficient_evidence":
            return RulesAnswerResponse(packet=packet, answer=RulesAnswer(
                status=status, answer=answer or None, citation_evidence_ref_ids=cited,
                needs_more_evidence=True, reason=str(parsed.get("reason") or "insufficient_evidence"),
                generation_trace_id=trace,
            ))
        return RulesAnswerResponse(packet=packet, answer=RulesAnswer(
            status="supported", answer=answer, citation_evidence_ref_ids=cited,
            needs_more_evidence=False, generation_trace_id=trace,
        ))
    except Exception:
        return unavailable(packet, "generation_failure")
