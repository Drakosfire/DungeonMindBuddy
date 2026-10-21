"""Bounded, independently attributed Rules execution records."""

from __future__ import annotations

from hashlib import sha256
import json
import unicodedata
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from .rules_authority_policy import rules_capability

from .rules_authority_types import (
    AnswerCompositionV1,
    ClosedRulesModel,
    Digest,
    Identity,
    MAX_LEDGER_BYTES,
    RulesScopeV1,
    RulesSupportRefV1,
    RulesSupportV1,
    canonical_bytes,
    canonical_sha256,
)


def normalized_question(text: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())


def query_identity(scope: RulesScopeV1, question: str) -> str:
    # Same exact immutable R1 query identity; authority also binds the frozen scope.
    return sha256(
        json.dumps(
            [scope.corpus_sha256, normalized_question(question), 4], ensure_ascii=False
        ).encode()
    ).hexdigest()


def ref_map(refs: tuple[RulesSupportRefV1, ...]) -> dict[UUID, str]:
    result = {ref.support_id: ref.support_sha256 for ref in refs}
    if len(result) != len(refs):
        raise ValueError("Repeated Rules support identity")
    return result


class RulesOutputRefV1(ClosedRulesModel):
    call_id: Identity
    packet_sha256: Digest


class RulesEventBaseV1(ClosedRulesModel):
    event_id: UUID
    sequence: Annotated[int, Field(ge=0, le=255)]
    execution_id: UUID


class RulesToolAuthorizedV1(RulesEventBaseV1):
    kind: Literal["tool_authorized"]
    call_id: Identity
    query_id: Digest
    normalized_question: Annotated[str, Field(min_length=1, max_length=14400)]
    packet_limit: Literal[4]

    @field_validator("packet_limit", mode="before")
    @classmethod
    def exact_limit(cls, value):
        if type(value) is not int:
            raise ValueError("Rules packet limit requires an exact integer")
        return value

    @model_validator(mode="after")
    def normalized(self):
        if self.normalized_question != normalized_question(self.normalized_question):
            raise ValueError("Rules query was not normalized")
        return self


def build_rules_operation_id(origin: UUID, request_id: str, operation_index: int, query_id: str) -> str:
    return "build-rules:" + canonical_sha256([str(origin), request_id, operation_index, query_id])


class RulesBuildToolAuthorizedV1(RulesToolAuthorizedV1):
    kind: Literal["build_tool_authorized"]
    origin_provider_attempt_id: UUID
    origin_request_envelope_sha256: Digest
    decision_request_id: Identity
    operation_index: Annotated[int, Field(ge=0, le=5)]

    @model_validator(mode="after")
    def exact_operation_identity(self):
        if self.call_id != build_rules_operation_id(self.origin_provider_attempt_id,
                self.decision_request_id, self.operation_index, self.query_id):
            raise ValueError("Build Rules operation differs from its authorized decision identity")
        return self


BuildRulesCarrierV1 = Literal["dmb_build_jev_driver_decision_v2", "dmb_build_jev_driver_continuation_v1",
    "dmb_build_jev_phase_controller_v1", "dmb_build_source_passage_writer_v1", "dmb_build_jev_writer_packet_v1"]


class RulesQueryObservedV1(RulesEventBaseV1):
    kind: Literal["query_observed"]
    call_id: Identity
    query_id: Digest
    packet_sha256: Digest
    presentation_utf8: Annotated[int, Field(ge=0, le=65536)]
    status: Literal["evidence", "no_evidence", "unavailable", "denied", "over_budget"]
    support_refs: Annotated[tuple[RulesSupportRefV1, ...], Field(max_length=4)]
    emitted_support_ids: Annotated[tuple[UUID, ...], Field(max_length=4)]

    @model_validator(mode="after")
    def exact_supports(self):
        refs = ref_map(self.support_refs)
        if (self.status == "evidence") != bool(refs):
            raise ValueError("Only an evidence result has support authority")
        if len(set(self.emitted_support_ids)) != len(
            self.emitted_support_ids
        ) or not set(self.emitted_support_ids) <= set(refs):
            raise ValueError("Emitted Rules text has no result identity")
        return self


class RulesProviderAuthorizedV1(RulesEventBaseV1):
    kind: Literal["provider_authorized"]
    provider_attempt_id: UUID
    request_envelope_sha256: Digest
    matched_outputs: Annotated[tuple[RulesOutputRefV1, ...], Field(max_length=6)]
    declared_support_refs: Annotated[
        tuple[RulesSupportRefV1, ...], Field(max_length=16)
    ]


class RulesProviderIncludedV1(RulesEventBaseV1):
    kind: Literal["provider_included"]
    provider_attempt_id: UUID
    request_envelope_sha256: Digest
    matched_outputs: Annotated[tuple[RulesOutputRefV1, ...], Field(max_length=6)]
    support_refs: Annotated[tuple[RulesSupportRefV1, ...], Field(max_length=16)]


class RulesBuildProviderAuthorizedV1(RulesProviderAuthorizedV1):
    kind: Literal["build_provider_authorized"]
    role: Literal["controller", "writer"]
    carrier_schema: BuildRulesCarrierV1
    request_id: Identity
    prior_provider_attempt_id: UUID | None


class RulesBuildProviderIncludedV1(RulesProviderIncludedV1):
    kind: Literal["build_provider_included"]
    role: Literal["controller", "writer"]
    carrier_schema: BuildRulesCarrierV1
    request_id: Identity
    prior_provider_attempt_id: UUID | None


class RulesProviderOutcomeV1(RulesEventBaseV1):
    kind: Literal["provider_outcome"]
    provider_attempt_id: UUID
    request_envelope_sha256: Digest
    status: Literal["tool_calls", "answered", "failed", "unknown"]


class RulesNativeProviderOutcomeV1(RulesProviderOutcomeV1):
    """Seal the exact uncapped native final reply without storing its body."""

    kind: Literal["native_provider_outcome"]
    provider: Annotated[str, Field(min_length=1, max_length=256)]
    model: Annotated[str, Field(min_length=1, max_length=256)]
    api_mode: Literal["chat_completions", "codex_responses"]
    authorization_id: Annotated[str, Field(min_length=1, max_length=256)]
    api_request_id: Annotated[str, Field(min_length=1, max_length=256)]
    output_sha256: Digest
    output_utf8_bytes: Annotated[int, Field(ge=1, le=262144)]
    finish_reason: Literal["stop"]
    tool_call_count: Literal[0]

    @classmethod
    def from_capture(
        cls,
        capture,
        *,
        event_id: UUID,
        sequence: int,
        execution_id: UUID,
        provider_attempt_id: UUID,
        request_envelope_sha256: str,
    ) -> "RulesNativeProviderOutcomeV1":
        text = getattr(capture, "text", None)
        if not isinstance(text, str):
            raise ValueError("Native Rules outcome requires complete captured text")
        encoded = text.encode("utf-8")
        output_sha256 = sha256(encoded).hexdigest()
        if (
            getattr(capture, "request_sha256", None)
            != request_envelope_sha256
            or getattr(capture, "text_sha256", None) != output_sha256
            or getattr(capture, "text_utf8_bytes", None) != len(encoded)
            or getattr(capture, "status", None) != "answered"
            or getattr(capture, "finish_reason", None) != "stop"
            or getattr(capture, "tool_calls", ())
            or not encoded
            or len(encoded) > 262144
        ):
            raise ValueError("Native Rules outcome requires a complete final reply")
        return cls(
            event_id=event_id,
            sequence=sequence,
            execution_id=execution_id,
            kind="native_provider_outcome",
            provider=capture.provider, model=capture.model, api_mode=capture.api_mode,
            provider_attempt_id=provider_attempt_id,
            request_envelope_sha256=request_envelope_sha256,
            status="answered",
            authorization_id=capture.authorization_id,
            api_request_id=capture.api_request_id,
            output_sha256=output_sha256,
            output_utf8_bytes=len(encoded),
            finish_reason="stop",
            tool_call_count=0,
        )


class RulesCompletionBoundV1(RulesEventBaseV1):
    kind: Literal["completion_bound"]
    producing_provider_attempt_id: UUID
    composition_sha256: Digest
    assistant_text_sha256: Digest
    accepted_binding_sha256: Digest
    claim_support_refs: Annotated[
        dict[Identity, tuple[RulesSupportRefV1, ...]], Field(max_length=16)
    ]
    accepted_turn_revision: Annotated[int, Field(ge=1)]


RulesEventV1 = Annotated[
    RulesToolAuthorizedV1
    | RulesBuildToolAuthorizedV1
    | RulesQueryObservedV1
    | RulesProviderAuthorizedV1
    | RulesProviderIncludedV1
    | RulesBuildProviderAuthorizedV1
    | RulesBuildProviderIncludedV1
    | RulesProviderOutcomeV1
    | RulesNativeProviderOutcomeV1
    | RulesCompletionBoundV1,
    Field(discriminator="kind"),
]


class RulesStoredSupportV1(ClosedRulesModel):
    support: RulesSupportV1
    support_sha256: Digest

    @model_validator(mode="after")
    def digest_matches(self):
        if self.support_sha256 != canonical_sha256(self.support):
            raise ValueError("Stored Rules capsule differs from its digest")
        return self


class RulesBudgetUseV1(ClosedRulesModel):
    calls: Annotated[int, Field(ge=0, le=6)]
    distinct_questions: Annotated[int, Field(ge=0, le=4)]
    novel_excerpt_utf8: Annotated[int, Field(ge=0, le=16384)]
    presentation_utf8: Annotated[int, Field(ge=0, le=65536)]
    provider_requests: Annotated[int, Field(ge=0, le=64)]


class RulesCompletionV1(ClosedRulesModel):
    schema_: Literal["dmb_rules_completion_v1"] = Field(alias="schema")
    execution_id: UUID
    producing_provider_attempt_id: UUID
    request_envelope_sha256: Digest
    composition_sha256: Digest
    claim_support_refs: Annotated[
        dict[Identity, tuple[RulesSupportRefV1, ...]], Field(max_length=16)
    ]
    approved_support_refs: Annotated[
        tuple[RulesSupportRefV1, ...], Field(max_length=16)
    ]


class RulesExecutionV1(ClosedRulesModel):
    schema_: Literal["dmb_rules_execution_v1"] = Field(alias="schema")
    scope: RulesScopeV1
    state: Literal["active", "unused", "accepted", "failed"]
    supports: Annotated[dict[UUID, RulesStoredSupportV1], Field(max_length=16)]
    events: Annotated[tuple[RulesEventV1, ...], Field(max_length=256)]
    budget_use: RulesBudgetUseV1
    composition: AnswerCompositionV1 | None
    rules_completion: RulesCompletionV1 | None

    @model_validator(mode="after")
    def causal_execution(self):
        if len(canonical_bytes(self)) > MAX_LEDGER_BYTES:
            raise ValueError("Rules ledger exceeds its serialized budget")
        known_supports = {}
        span_identities = set()
        novel_bytes = 0
        for key, stored in self.supports.items():
            unit = stored.support
            if (
                key != unit.support_id
                or unit.corpus_sha256 != self.scope.corpus_sha256
                or unit.ruleset_id != self.scope.ruleset_id
            ):
                raise ValueError("Rules support belongs to another scope")
            span = (
                unit.unit_id,
                unit.full_text_sha256,
                unit.excerpt_start,
                unit.excerpt_end,
                unit.excerpt_sha256,
            )
            if span in span_identities:
                raise ValueError(
                    "Duplicate source span must reuse its Rules support ID"
                )
            span_identities.add(span)
            known_supports[key] = stored.support_sha256
            novel_bytes += len(unit.excerpt_text.encode("utf-8"))
        event_ids = set()
        calls = {}
        observations = {}
        providers = {}
        inclusions = {}
        outcomes = {}
        successful_queries = {}
        questions = set()
        seen_supports = set()
        bound = None
        presentation = 0
        retired = False
        for index, event in enumerate(self.events):
            if (
                event.sequence != index
                or event.event_id in event_ids
                or event.execution_id != self.scope.execution_id
            ):
                raise ValueError("Rules event sequence, identity or scope is invalid")
            if bound is not None:
                raise ValueError("Accepted Rules execution is immutable")
            event_ids.add(event.event_id)
            if isinstance(event, RulesToolAuthorizedV1):
                # Reaching a hard threshold retires further tool admissions; the
                # current admitted output and final provider response may settle.
                if retired or len(calls) >= 6 or len(questions) >= 4:
                    raise ValueError(
                        "Rules tool capability exhausted its admission budget"
                    )
                if isinstance(event, RulesBuildToolAuthorizedV1):
                    origin = providers.get(event.origin_provider_attempt_id)
                    outcome = outcomes.get(event.origin_provider_attempt_id)
                    if (not isinstance(origin, RulesBuildProviderAuthorizedV1) or origin.role != "controller"
                            or origin.request_envelope_sha256 != event.origin_request_envelope_sha256
                            or origin.request_id != event.decision_request_id
                            or outcome is None or outcome.status not in {"answered", "tool_calls"}):
                        raise ValueError("Build Rules lookup lacks its acknowledged originating controller")
                if event.call_id in calls or event.query_id != query_identity(
                    self.scope, event.normalized_question
                ):
                    raise ValueError(
                        "Rules call identity was reused or query identity differs"
                    )
                calls[event.call_id] = event
                questions.add(event.normalized_question)
            elif isinstance(event, RulesQueryObservedV1):
                auth = calls.get(event.call_id)
                if (
                    auth is None
                    or auth.query_id != event.query_id
                    or event.call_id in observations
                ):
                    raise ValueError("Rules result has no unique prior authorization")
                refs = ref_map(event.support_refs)
                previous_success = successful_queries.get(event.query_id)
                if (
                    previous_success is not None
                    and event.status != "over_budget"
                    and previous_success
                    != (
                        event.status,
                        refs,
                    )
                ):
                    raise ValueError(
                        "Successful Rules query must reuse its frozen result"
                    )
                if event.status in {"evidence", "no_evidence"}:
                    successful_queries[event.query_id] = (event.status, refs)
                if any(
                    known_supports.get(key) != digest for key, digest in refs.items()
                ):
                    raise ValueError("Rules result has an unadmitted capsule")
                if not (set(refs) - seen_supports) <= set(event.emitted_support_ids):
                    raise ValueError(
                        "A new support must be emitted before it can be reused"
                    )
                seen_supports.update(refs)
                presentation += event.presentation_utf8
                if event.status == "over_budget":
                    if event.presentation_utf8 > 1024 or presentation > 65536:
                        raise ValueError(
                            "Rules retirement diagnostic exceeds its reserved budget"
                        )
                    retired = True
                elif presentation > 64512 or retired:
                    raise ValueError(
                        "Rules output consumed the reserved diagnostic budget"
                    )
                observations[event.call_id] = event
            elif isinstance(event, RulesProviderAuthorizedV1):
                if isinstance(event, RulesBuildProviderAuthorizedV1):
                    cap = rules_capability(graph=True)
                    if (self.scope.capability_policy_sha256 != cap.policy_sha256
                            or self.scope.corpus_sha256 != cap.corpus_sha256 or self.scope.ruleset_id != cap.ruleset_id):
                        raise ValueError("Build Rules provider lacks its frozen typed policy")
                    previous = list(providers.values())[-1] if providers else None
                    if previous is None and (event.sequence != 0 or event.role != "controller"
                            or event.carrier_schema != "dmb_build_jev_driver_decision_v2"
                            or event.matched_outputs or event.declared_support_refs):
                        raise ValueError("First Build Rules request must be a source-free initial controller")
                    if event.prior_provider_attempt_id != (previous.provider_attempt_id if previous else None):
                        raise ValueError("Build Rules provider has a stale prior attempt")
                    if previous is not None and (not isinstance(previous, RulesBuildProviderAuthorizedV1)
                            or outcomes.get(previous.provider_attempt_id) is None
                            or outcomes[previous.provider_attempt_id].status not in {"answered", "tool_calls"}):
                        raise ValueError("Build Rules provider lacks an acknowledged prior attempt")
                    if any(isinstance(item, RulesBuildProviderAuthorizedV1) and item.request_id == event.request_id for item in providers.values()):
                        raise ValueError("Build Rules decision request identity was reused")
                    controller = event.carrier_schema in {"dmb_build_jev_driver_decision_v2", "dmb_build_jev_driver_continuation_v1", "dmb_build_jev_phase_controller_v1"}
                    if controller != (event.role == "controller"):
                        raise ValueError("Build Rules role differs from its carrier")
                if event.provider_attempt_id in providers:
                    raise ValueError("Rules provider authorization identity was reused")
                self._check_output_refs(event.matched_outputs, observations)
                refs = ref_map(event.declared_support_refs)
                if any(
                    known_supports.get(key) != digest for key, digest in refs.items()
                ):
                    raise ValueError("Rules provider declared an unadmitted support")
                providers[event.provider_attempt_id] = event
            elif isinstance(event, RulesProviderIncludedV1):
                auth = providers.get(event.provider_attempt_id)
                if (
                    auth is None
                    or auth.request_envelope_sha256 != event.request_envelope_sha256
                    or event.provider_attempt_id in inclusions
                    or event.provider_attempt_id in outcomes
                ):
                    raise ValueError(
                        "Rules inclusion has no matching current provider authorization"
                    )
                if isinstance(auth, RulesBuildProviderAuthorizedV1) != isinstance(event, RulesBuildProviderIncludedV1):
                    raise ValueError("Rules provider inclusion changed its input carrier")
                if isinstance(auth, RulesBuildProviderAuthorizedV1) and any(
                        getattr(event, key) != getattr(auth, key) for key in (
                            "role", "carrier_schema", "request_id", "prior_provider_attempt_id")):
                    raise ValueError("Build Rules inclusion differs from its authorized role/request")
                self._check_output_refs(event.matched_outputs, observations)
                if event.matched_outputs != auth.matched_outputs or ref_map(
                    event.support_refs
                ) != ref_map(auth.declared_support_refs):
                    raise ValueError(
                        "Rules actual inclusion differs from its authorized input"
                    )
                emitted = set()
                for output in event.matched_outputs:
                    emitted.update(observations[output.call_id].emitted_support_ids)
                if not set(ref_map(event.support_refs)) <= emitted:
                    raise ValueError(
                        "Rules handles or cached results alone do not expose source text"
                    )
                inclusions[event.provider_attempt_id] = event
            elif isinstance(event, RulesProviderOutcomeV1):
                auth = providers.get(event.provider_attempt_id)
                if (
                    auth is None
                    or auth.request_envelope_sha256 != event.request_envelope_sha256
                    or event.provider_attempt_id in outcomes
                ):
                    raise ValueError(
                        "Rules provider outcome has no unique authorization"
                    )
                if isinstance(event, RulesNativeProviderOutcomeV1) and (
                    isinstance(auth, RulesBuildProviderAuthorizedV1)
                    or event.status != "answered"
                    or event.provider_attempt_id not in inclusions
                ):
                    raise ValueError(
                        "Native Rules outcome lacks its final included non-Build input"
                    )
                outcomes[event.provider_attempt_id] = event
            else:
                bound = event
        if seen_supports != set(known_supports):
            raise ValueError("Orphan Rules source bodies are not retained")
        derived = RulesBudgetUseV1(
            calls=len(calls),
            distinct_questions=len(questions),
            novel_excerpt_utf8=novel_bytes,
            presentation_utf8=presentation,
            provider_requests=len(providers),
        )
        if self.budget_use != derived:
            raise ValueError("Rules budget counters differ from sealed observations")
        if self.state == "unused" and (calls or self.supports):
            raise ValueError("A used Rules capability cannot be closed as unused")
        if self.state != "accepted":
            if (
                bound is not None
                or self.composition is not None
                or self.rules_completion is not None
            ):
                raise ValueError(
                    "Unaccepted Rules execution cannot carry an approved answer"
                )
        else:
            self._validate_completion(bound, providers, inclusions, outcomes)
        return self

    @staticmethod
    def _check_output_refs(refs, observations):
        if len({item.call_id for item in refs}) != len(refs):
            raise ValueError("Rules provider output identities are ambiguous")
        for item in refs:
            observed = observations.get(item.call_id)
            if observed is None or observed.packet_sha256 != item.packet_sha256:
                raise ValueError(
                    "Rules provider output differs from its parent observation"
                )

    def _validate_completion(self, bound, providers, inclusions, outcomes):
        from .rules_authority_types import RulesClaimV1

        completion = self.rules_completion
        composition = self.composition
        if bound is None or completion is None or composition is None:
            raise ValueError(
                "Accepted Rules execution needs an atomic bound composition"
            )
        producer = completion.producing_provider_attempt_id
        auth = providers.get(producer)
        included = inclusions.get(producer)
        outcome = outcomes.get(producer)
        if (
            auth is None
            or included is None
            or outcome is None
            or outcome.status != "answered"
        ):
            raise ValueError("Rules answer lacks an acknowledged producing input")
        if isinstance(auth, RulesBuildProviderAuthorizedV1) and auth.role != "writer":
            raise ValueError("A Build controller cannot produce an accepted Rules answer")
        if (
            completion.execution_id != self.scope.execution_id
            or completion.request_envelope_sha256 != auth.request_envelope_sha256
        ):
            raise ValueError("Rules answer belongs to another producing request")
        claims = {
            seg.claim_id: seg.support_refs
            for seg in composition.rules_segments
            if isinstance(seg, RulesClaimV1)
        }
        expected = {}
        for refs in claims.values():
            expected.update(ref_map(refs))
        if claims != completion.claim_support_refs or expected != ref_map(
            completion.approved_support_refs
        ):
            raise ValueError("Rules answer claims differ from approved source bindings")
        available = ref_map(included.support_refs)
        if any(available.get(key) != digest for key, digest in expected.items()):
            raise ValueError(
                "Rules answer cites source text absent from its producing input"
            )
        digest = canonical_sha256(composition)
        if (
            completion.composition_sha256 != digest
            or bound.composition_sha256 != digest
            or bound.assistant_text_sha256 != composition.assistant_text_sha256
            or bound.producing_provider_attempt_id != producer
            or bound.claim_support_refs != claims
        ):
            raise ValueError("Rules completion seal differs from its approved answer")


def empty_execution(scope: RulesScopeV1) -> RulesExecutionV1:
    return RulesExecutionV1(
        schema="dmb_rules_execution_v1",
        scope=scope,
        state="active",
        supports={},
        events=(),
        budget_use=RulesBudgetUseV1(
            calls=0,
            distinct_questions=0,
            novel_excerpt_utf8=0,
            presentation_utf8=0,
            provider_requests=0,
        ),
        composition=None,
        rules_completion=None,
    )
