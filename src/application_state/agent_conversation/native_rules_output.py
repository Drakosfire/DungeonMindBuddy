"""APP proof for the actual native Rules-producing provider response.

This owner deliberately stops before base Graph normalization or persistence.
It proves that the uncapped SDK capture is the final response for the exact
Graph and Rules authorizations, then parses the bounded mixed output. Callers
must still normalize the nested base through its owning Graph/Play validator
and commit both domains through ``complete_mixed_turn``.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Literal
from uuid import UUID

from pydantic import Field

from .rules_authority_events import (
    RulesBuildProviderAuthorizedV1,
    RulesBuildProviderIncludedV1,
    RulesProviderAuthorizedV1,
    RulesProviderIncludedV1,
    RulesProviderOutcomeV1,
    RulesExecutionV1,
)
from .rules_authority_output import (
    MAX_REQUEST_BYTES,
    POLICY,
    RulesWriterAnswerV1,
    parse_answer,
)
from .rules_authority_input import verify_prepared_input
from .rules_authority_types import AnswerCompositionV1, ClosedRulesModel
from .source_writer_output import strict_json
from .types import (
    PlanWorldGraphCompletionV2,
    PlanWorldGraphExecutionV3,
    PlayWorldGraphCompletionV1,
    PlayWorldGraphExecutionV1,
    ProviderAttemptAuthorizedEventV1,
    ProviderAttemptAuthorizedEventV2,
    ProviderAttemptAuthorizedEventV3,
    ProviderOutcomeEventV1,
    Turn,
)

MAX_NATIVE_OUTPUT_BYTES = 262144


class NativeRulesOutputProofV1(ClosedRulesModel):
    """Transient proof input. ``raw_output_json`` is never written to history."""

    schema_: Literal["dmb_native_rules_output_proof_v1"] = Field(alias="schema")
    policy: Literal["exact_producer_composition_v1"]
    rules_execution_id: UUID
    producing_provider_attempt_id: UUID
    request_envelope_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    authorization_id: str = Field(min_length=1, max_length=256)
    api_request_id: str = Field(min_length=1, max_length=256)
    prepared_request_json: str = Field(min_length=1, max_length=MAX_REQUEST_BYTES)
    raw_output_json: str = Field(min_length=1, max_length=MAX_NATIVE_OUTPUT_BYTES)
    raw_output_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    raw_output_utf8_bytes: int = Field(ge=1, le=MAX_NATIVE_OUTPUT_BYTES)

    @classmethod
    def from_capture(
        cls,
        capture,
        *,
        prepared_request_json: str,
        rules_execution_id: UUID,
        producing_provider_attempt_id: UUID,
    ):
        text = getattr(capture, "text", None)
        if not isinstance(text, str):
            raise ValueError("Native Rules capture has no complete text output")
        encoded = text.encode("utf-8")
        return cls(
            schema="dmb_native_rules_output_proof_v1",
            policy=POLICY,
            rules_execution_id=rules_execution_id,
            producing_provider_attempt_id=producing_provider_attempt_id,
            request_envelope_sha256=capture.request_sha256,
            authorization_id=capture.authorization_id,
            api_request_id=capture.api_request_id,
            prepared_request_json=prepared_request_json,
            raw_output_json=text,
            raw_output_sha256=sha256(encoded).hexdigest(),
            raw_output_utf8_bytes=len(encoded),
        )


def _one(items, message):
    if len(items) != 1:
        raise ValueError(message)
    return items[0]


def verify_native_output(
    graph_execution: PlanWorldGraphExecutionV3 | PlayWorldGraphExecutionV1,
    rules_execution: RulesExecutionV1,
    proof: NativeRulesOutputProofV1,
    capture,
) -> RulesWriterAnswerV1:
    """Revalidate exact final producer identity and strict captured mixed JSON."""
    if not isinstance(proof, NativeRulesOutputProofV1):
        raise ValueError("Native Rules output proof is not the current closed schema")
    if (
        rules_execution.state != "active"
        or proof.rules_execution_id != rules_execution.scope.execution_id
    ):
        raise ValueError("Native Rules output belongs to another active execution")
    if (
        proof.authorization_id != getattr(capture, "authorization_id", None)
        or proof.api_request_id != getattr(capture, "api_request_id", None)
        or proof.request_envelope_sha256 != getattr(capture, "request_sha256", None)
    ):
        raise ValueError("Native Rules proof differs from its SDK capture")
    if (
        getattr(capture, "status", None) != "answered"
        or getattr(capture, "finish_reason", None) != "stop"
        or getattr(capture, "tool_calls", ())
        or getattr(capture, "api_mode", None)
        not in {"chat_completions", "codex_responses"}
    ):
        raise ValueError(
            "Native Rules output is not a complete final assistant message"
        )
    raw = proof.raw_output_json
    try:
        request_bytes = proof.prepared_request_json.encode("utf-8")
    except UnicodeError as exc:
        raise ValueError("Native Rules request is not valid UTF8") from exc
    if (
        len(request_bytes) > MAX_REQUEST_BYTES
        or sha256(request_bytes).hexdigest() != proof.request_envelope_sha256
    ):
        raise ValueError("Native Rules proof differs from its exact prepared request")
    try:
        request = strict_json(proof.prepared_request_json)
    except (ValueError, TypeError, RecursionError) as exc:
        raise ValueError("Native Rules prepared request is not strict JSON") from exc
    if not isinstance(request, dict):
        raise ValueError("Native Rules prepared request is not an object")
    try:
        encoded = raw.encode("utf-8")
    except UnicodeError as exc:
        raise ValueError("Native Rules output is not valid UTF8") from exc
    if (
        len(encoded) != proof.raw_output_utf8_bytes
        or len(encoded) > MAX_NATIVE_OUTPUT_BYTES
        or sha256(encoded).hexdigest() != proof.raw_output_sha256
        or getattr(capture, "text_sha256", None) != proof.raw_output_sha256
        or getattr(capture, "text_utf8_bytes", None) != proof.raw_output_utf8_bytes
        or raw != getattr(capture, "text", None)
    ):
        raise ValueError("Native Rules output differs from the exact captured bytes")

    graph_auths = [
        event
        for event in graph_execution.events
        if isinstance(
            event,
            (
                ProviderAttemptAuthorizedEventV1,
                ProviderAttemptAuthorizedEventV2,
                ProviderAttemptAuthorizedEventV3,
            ),
        )
        and event.provider_attempt_id == proof.producing_provider_attempt_id
    ]
    graph_auth = _one(
        graph_auths, "Native Rules output has no unique Graph authorization"
    )
    graph_authorizations = [
        event
        for event in graph_execution.events
        if isinstance(
            event,
            (
                ProviderAttemptAuthorizedEventV1,
                ProviderAttemptAuthorizedEventV2,
                ProviderAttemptAuthorizedEventV3,
            ),
        )
    ]
    if (
        not graph_authorizations
        or graph_authorizations[-1].provider_attempt_id
        != proof.producing_provider_attempt_id
    ):
        raise ValueError(
            "Native Rules output is not the final Graph-authorized provider response"
        )
    if (
        graph_auth.envelope_sha256 != proof.request_envelope_sha256
        or graph_auth.provider != getattr(capture, "provider", None)
        or graph_auth.model != getattr(capture, "model", None)
        or graph_auth.api_mode != getattr(capture, "api_mode", None)
    ):
        raise ValueError(
            "Native Rules capture differs from its actual Graph provider authorization"
        )
    graph_outcomes = [
        event.outcome
        for event in graph_execution.events
        if isinstance(event, ProviderOutcomeEventV1)
        and event.provider_attempt_id == proof.producing_provider_attempt_id
    ]
    if not graph_outcomes or graph_outcomes[-1] != "response_received":
        raise ValueError(
            "Native Rules output lacks acknowledged Graph response lifecycle"
        )

    rules_auth = _one(
        [
            event
            for event in rules_execution.events
            if isinstance(event, RulesProviderAuthorizedV1)
            and not isinstance(event, RulesBuildProviderAuthorizedV1)
            and event.provider_attempt_id == proof.producing_provider_attempt_id
        ],
        "Native Rules output has no unique Rules authorization",
    )
    included = _one(
        [
            event
            for event in rules_execution.events
            if isinstance(event, RulesProviderIncludedV1)
            and not isinstance(event, RulesBuildProviderIncludedV1)
            and event.provider_attempt_id == proof.producing_provider_attempt_id
        ],
        "Native Rules output has no unique included input",
    )
    outcome = _one(
        [
            event
            for event in rules_execution.events
            if isinstance(event, RulesProviderOutcomeV1)
            and event.provider_attempt_id == proof.producing_provider_attempt_id
        ],
        "Native Rules output has no unique terminal outcome",
    )
    if (
        rules_auth.request_envelope_sha256 != proof.request_envelope_sha256
        or included.request_envelope_sha256 != proof.request_envelope_sha256
        or outcome.request_envelope_sha256 != proof.request_envelope_sha256
        or outcome.status != "answered"
        or rules_auth.declared_support_refs != included.support_refs
        or rules_auth.matched_outputs != included.matched_outputs
    ):
        raise ValueError(
            "Native Rules output differs from its exact included Rules evidence"
        )
    try:
        verify_prepared_input(rules_execution, rules_auth, proof.prepared_request_json)
        verify_prepared_input(rules_execution, included, proof.prepared_request_json)
    except (ValueError, TypeError, KeyError, RecursionError) as exc:
        raise ValueError("Native Rules prepared input differs from its recorded evidence") from exc
    latest = [
        event
        for event in rules_execution.events
        if isinstance(event, RulesProviderAuthorizedV1)
        and not isinstance(event, RulesBuildProviderAuthorizedV1)
    ]
    if (
        not latest
        or latest[-1].provider_attempt_id != proof.producing_provider_attempt_id
    ):
        raise ValueError(
            "Native Rules output is not the final authorized provider response"
        )
    answer = parse_answer(raw)
    admitted_supports = {str(item.support_id) for item in included.support_refs}
    if any(
        not set(segment.support_ids) <= admitted_supports
        for segment in answer.rules_segments
        if getattr(segment, "kind", None) == "rules_claim"
    ):
        raise ValueError(
            "Native Rules output cites support absent from its producing input"
        )
    return answer


@dataclass(frozen=True)
class NativeRulesNormalizedOutputV1:
    """Pure normalization result; it is not a durable acceptance receipt."""

    base_completion: PlanWorldGraphCompletionV2 | PlayWorldGraphCompletionV1 | None
    claim_graph_event_ids: dict[str, list[UUID]]
    composition: AnswerCompositionV1
    assistant_text: str
    graph_used: bool


def normalize_native_mixed_output(
    turn: Turn,
    graph_execution: PlanWorldGraphExecutionV3 | PlayWorldGraphExecutionV1,
    rules_execution: RulesExecutionV1,
    proof: NativeRulesOutputProofV1,
    capture,
    *,
    graph_support=None,
) -> NativeRulesNormalizedOutputV1:
    """Normalize the exact native outer answer through both domain owners.

    The caller still must persist the accepted Rules binding and completed Turn
    together under the live claim lock. This helper performs no database reads,
    commits, provider calls, or durable acceptance.
    """
    from .native_answer_output import normalize_native_answer

    scope = rules_execution.scope
    if (
        (scope.world_id, scope.conversation_id, scope.turn_id, scope.product_attempt)
        != (turn.world_id, turn.conversation_id, turn.turn_id, turn.attempt)
    ):
        raise ValueError("Native Rules execution differs from its Plan/Play turn")
    if turn.graph_context_execution != graph_execution:
        raise ValueError("Native Rules Graph execution differs from its owning turn")

    answer = verify_native_output(graph_execution, rules_execution, proof, capture)
    included = _one(
        [
            event
            for event in rules_execution.events
            if isinstance(event, RulesProviderIncludedV1)
            and not isinstance(event, RulesBuildProviderIncludedV1)
            and event.provider_attempt_id == proof.producing_provider_attempt_id
        ],
        "Native Rules output has no unique included input",
    )

    base_completion = None
    bindings: dict[str, list[UUID]] = {}
    base_segments: tuple[str, ...] = ()
    disposition = "unclaimed"
    graph_used = False
    if answer.base_output is not None:
        base_completion, bindings, base_text = normalize_native_answer(
            answer.base_output,
            turn,
            proof.producing_provider_attempt_id,
            support=graph_support,
        )
        base_segments = tuple(segment.text for segment in base_completion.answer_segments)
        if base_text != "\n".join(base_segments):
            raise ValueError("Native Graph base text differs from its normalized segments")
        disposition = "approved"
        graph_used = "world_graph" in base_completion.answer_basis
    elif turn.graph_context_receipt is None or turn.graph_context_execution is None:
        raise ValueError("Native Rules without a base partition requires frozen Graph scope")

    composition = answer.composition(
        supplied_refs=included.support_refs,
        base_segments=base_segments,
        base_disposition=disposition,
    )
    assistant_text = composition.render(base_segments)
    return NativeRulesNormalizedOutputV1(
        base_completion=base_completion,
        claim_graph_event_ids=bindings,
        composition=composition,
        assistant_text=assistant_text,
        graph_used=graph_used,
    )
