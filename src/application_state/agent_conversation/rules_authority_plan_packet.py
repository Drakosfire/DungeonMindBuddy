"""Transient exact Rules exposure proof for a future tool-free Plan writer.

This does not authorize a lookup/provider, append a ledger event or accept an
answer. The owning locked Plan append must consume the returned witness and
independently bind its actual provider attempt/outcome before granting authority.
Current native function-call and Build carrier proofs remain separate.
"""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, TypeAdapter, model_validator

from .rules_authority_events import (
    RulesExecutionV1, RulesToolAuthorizedV1, RulesBuildToolAuthorizedV1,
    RulesQueryObservedV1, RulesOutputRefV1,
)
from .rules_authority_packet import RulesPacketV1, RulesBudgetDiagnosticV1, _unique_object, verify_output_proof
from .rules_authority_types import ClosedRulesModel, Digest, Label, RulesSupportRefV1, canonical_bytes

Packet = Annotated[RulesPacketV1 | RulesBudgetDiagnosticV1, Field(discriminator="schema_")]


class PlanRulesLookupV1(ClosedRulesModel):
    lookup: Annotated[int, Field(ge=0)]
    status: Literal["evidence", "no_evidence", "unavailable", "denied", "over_budget"]
    diagnostic: Literal["corpus_unavailable", "unsupported_ruleset", "rules_budget_exhausted"] | None


class PlanRulesEvidenceV1(ClosedRulesModel):
    support_id: UUID
    source_title: Label
    section: Label
    source_uri: str
    printed_page: int | None
    excerpt_text: str


class PlanRulesEvidenceFrameV1(ClosedRulesModel):
    schema_: Literal["dmb_plan_rules_evidence_v1"] = Field(alias="schema")
    ruleset: str
    lookups: tuple[PlanRulesLookupV1, ...]
    supports: tuple[PlanRulesEvidenceV1, ...]

    @model_validator(mode="after")
    def unique_entries(self):
        if len({item.lookup for item in self.lookups}) != len(self.lookups):
            raise ValueError("Plan Rules frame repeats a lookup")
        if len({item.support_id for item in self.supports}) != len(self.supports):
            raise ValueError("Plan Rules frame repeats a support")
        return self


class PlanRulesPacketExposureV1(ClosedRulesModel):
    """Metadata-only proof result, not an admitted event or citation receipt."""
    plan_context_receipt_sha256: Digest
    rules_execution_id: UUID
    request_envelope_sha256: Digest
    matched_outputs: tuple[RulesOutputRefV1, ...]
    support_refs: tuple[RulesSupportRefV1, ...]


def _observed(execution, call_id):
    auths = [e for e in execution.events if isinstance(e, RulesToolAuthorizedV1) and e.call_id == call_id]
    reads = [e for e in execution.events if isinstance(e, RulesQueryObservedV1) and e.call_id == call_id]
    if (len(auths) != 1 or len(reads) != 1 or isinstance(auths[0], RulesBuildToolAuthorizedV1)):
        raise ValueError("Plan packet has no unique non-Build authorized Rules read")
    return auths[0], reads[0]


def _sealed_packets(execution, call_ids):
    from .rules_authority_runtime import _replay
    packets = []
    for call_id in call_ids:
        auth, observed = _observed(execution, call_id)
        raw = _replay(execution, auth, observed).raw_output
        verify_output_proof(execution.scope, observed, execution.supports, raw)
        packets.append(TypeAdapter(Packet).validate_json(raw))
    return packets


def build_plan_rules_frame(execution: RulesExecutionV1, call_ids: tuple[str, ...]) -> PlanRulesEvidenceFrameV1:
    """Project sealed outputs in memory; keep authority bookkeeping outside model text."""
    observed_calls = [event.call_id for event in execution.events if isinstance(event, RulesQueryObservedV1)]
    lookups, supports = [], {}
    for packet in _sealed_packets(execution, call_ids):
        lookups.append(PlanRulesLookupV1(lookup=observed_calls.index(packet.call_id),
            status=packet.status if isinstance(packet, RulesPacketV1) else "over_budget",
            diagnostic=packet.diagnostic if isinstance(packet, RulesPacketV1) else packet.code))
        if isinstance(packet, RulesPacketV1):
            for capsule in packet.support_capsules:
                support = PlanRulesEvidenceV1(**{name: getattr(capsule, name)
                    for name in PlanRulesEvidenceV1.model_fields})
                if support.support_id in supports and supports[support.support_id] != support:
                    raise ValueError("Conflicting exposed Rules support")
                supports[support.support_id] = support
    return PlanRulesEvidenceFrameV1(schema="dmb_plan_rules_evidence_v1", ruleset=execution.scope.ruleset_id,
        lookups=tuple(lookups), supports=tuple(supports[key] for key in sorted(supports, key=str)))


def _frame_in_actual_request(body) -> PlanRulesEvidenceFrameV1:
    if (not isinstance(body, dict) or "messages" in body or not isinstance(body.get("input"), list)
            or body.get("tools", []) != [] or body.get("tool_choice") not in (None, "none")):
        raise ValueError("Plan Rules packet proof requires a tool-free Responses request")
    frames = []
    for item in body["input"]:
        # This new text-writer contract accepts messages only, not any of the
        # function/custom/MCP/computer/search tool transcript item families.
        if (not isinstance(item, dict) or set(item) - {"type", "role", "content"}
                or item.get("type") not in (None, "message")
                or item.get("role") not in {"system", "developer", "user", "assistant"}):
            raise ValueError("Plan packet writer accepts text messages, not tool transcripts")
        content = item.get("content")
        if isinstance(content, str):
            texts = [content]
        elif isinstance(content, list):
            if any(not isinstance(part, dict) or set(part) != {"type", "text"}
                   or part.get("type") != "input_text" or not isinstance(part.get("text"), str)
                   for part in content):
                raise ValueError("Plan packet writer accepts input_text content only")
            texts = [part["text"] for part in content]
        else:
            raise ValueError("Malformed Plan writer message content")
        if item["role"] != "user":
            continue
        for text in texts:
            try:
                candidate = json.loads(text, object_pairs_hook=_unique_object)
            except json.JSONDecodeError:
                continue
            if isinstance(candidate, dict) and candidate.get("schema") == "dmb_plan_rules_evidence_v1":
                frames.append(PlanRulesEvidenceFrameV1.model_validate_json(text))
    if len(frames) != 1:
        raise ValueError("Plan writer requires one exact Rules packet frame")
    return frames[0]


def verify_plan_rules_packet_input(execution: RulesExecutionV1, turn, prepared_request_json: str, *,
                                   expected_envelope_sha256: str) -> PlanRulesPacketExposureV1:
    """Join actual input bytes to sealed Rules sources and the current Plan owner.

    Caller supplies its locked, owner-loaded Turn, not a model/HTTP substitute.
    Nothing returned by this pure verifier is itself permission to dispatch/cite.
    """
    from .types import Turn, PlanWorldGraphContextReceiptV1, PlanSourceContextReceiptV1
    if not isinstance(turn, Turn) or not isinstance(turn.graph_context_receipt,
            (PlanWorldGraphContextReceiptV1, PlanSourceContextReceiptV1)):
        raise ValueError("Rules packet requires an actual Plan receipt")
    receipt = type(turn.graph_context_receipt).model_validate_json(turn.graph_context_receipt.model_dump_json(by_alias=True))
    if isinstance(receipt, PlanSourceContextReceiptV1):
        from .plan_source_context import validate_source_execution_binding
        validate_source_execution_binding(receipt, turn.graph_context_execution)
    execution = RulesExecutionV1.model_validate_json(execution.model_dump_json(by_alias=True))
    scope = execution.scope
    if (turn.status != "running" or turn.provenance.surface_id != "plan" or execution.state != "active"
            or (scope.world_id, scope.conversation_id, scope.turn_id, scope.product_attempt)
            != (turn.world_id, turn.conversation_id, turn.turn_id, turn.attempt)
            or receipt.plan_basis.world_id != scope.world_id):
        raise ValueError("Rules packet differs from the current Plan turn scope")
    from .rules_authority_policy import (
        capability_for_policy_sha256, rules_capability, rules_submission_authorization_id,
    )
    capability = capability_for_policy_sha256(scope.capability_policy_sha256)
    fingerprints = [value for value in (turn.submitted_intent_fingerprint_v1,
                    turn.submitted_intent_fingerprint_v2) if value is not None]
    if (capability is None or capability != rules_capability(graph=True)
            or scope.corpus_sha256 != capability.corpus_sha256 or scope.ruleset_id != capability.ruleset_id
            or len(fingerprints) != 1 or turn.provenance.surface_resolution != "resolved"
            or scope.authorization_id != rules_submission_authorization_id(
                world_id=turn.world_id, conversation_id=turn.conversation_id,
                idempotency_key=turn.idempotency_key, submitted_intent_sha256=fingerprints[0],
                capability=capability)):
        raise ValueError("Rules packet lacks the current Plan submission capability/authorization")
    if sha256(prepared_request_json.encode()).hexdigest() != expected_envelope_sha256:
        raise ValueError("Plan Rules envelope differs from the actual request")
    body = json.loads(prepared_request_json, object_pairs_hook=_unique_object,
        parse_constant=lambda _value: (_ for _ in ()).throw(ValueError("Nonfinite Plan request")))
    frame = _frame_in_actual_request(body)
    observed_calls = [event.call_id for event in execution.events if isinstance(event, RulesQueryObservedV1)]
    if any(item.lookup >= len(observed_calls) for item in frame.lookups):
        raise ValueError("Plan Rules frame names an unread lookup")
    call_ids = tuple(observed_calls[item.lookup] for item in frame.lookups)
    expected = build_plan_rules_frame(execution, call_ids)
    if canonical_bytes(frame) != canonical_bytes(expected):
        raise ValueError("Plan Rules evidence differs from sealed outputs")
    from .plan_jev_graph_packet import frame_in_request
    from .plan_writer_output_schema import verify_format
    verify_format(body, frame_in_request(prepared_request_json), expected)
    outputs, supports = [], {}
    for packet in _sealed_packets(execution, call_ids):
        _auth, observed = _observed(execution, packet.call_id)
        verify_output_proof(scope, observed, execution.supports, canonical_bytes(packet).decode())
        outputs.append(RulesOutputRefV1(call_id=packet.call_id, packet_sha256=observed.packet_sha256))
        if isinstance(packet, RulesPacketV1):
            # A cached support handle without its capsule in this actual input
            # grants no exposure; only the physically supplied excerpts count.
            refs = {ref.support_id: ref for ref in packet.support_refs}
            for capsule in packet.support_capsules:
                ref = refs[capsule.support_id]
                if capsule.support_id in supports and supports[capsule.support_id] != ref:
                    raise ValueError("Conflicting exposed Rules support")
                supports[capsule.support_id] = ref
    return PlanRulesPacketExposureV1(
        plan_context_receipt_sha256=receipt.context_receipt_sha256,
        rules_execution_id=scope.execution_id, request_envelope_sha256=expected_envelope_sha256,
        matched_outputs=tuple(outputs), support_refs=tuple(supports[key] for key in sorted(supports, key=str)),
    )
