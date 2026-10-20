"""Explicit completed mixed-answer read model, separate from ordinary Turn.

Repository selects this model from the persisted marker before constructing a
Turn. The full mixed body never enters a base-domain answer validator.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, model_validator

from .rules_authority_types import (
    ClosedRulesModel,
    Digest,
    RulesAcceptedBindingV1,
    canonical_sha256,
)
from .types import (
    Turn,
    PlanAskHistoryAttributionV1,
    TurnProvenance,
    GraphContextReceipt,
    PlanWorldGraphExecution,
    PlayRunTurnContextReceiptV2,
    CompletionBindingEventV1,
    ProviderAttemptAuthorizedEventV1,
    ProviderOutcomeEventV1,
    BuildGraphContextReceiptV1,
    PlanWorldGraphContextReceiptV1,
    decode_plan_playable_target_reference,
    validate_turn_graph_fields,
    validate_turn_lifecycle_fields,
)


class CompletedTurnEnvelopeV1(ClosedRulesModel):
    turn_id: UUID
    conversation_id: UUID
    world_id: str
    idempotency_key: UUID
    sequence: Annotated[int, Field(ge=1)]
    revision: Annotated[int, Field(ge=1)]
    status: Literal["completed"]
    user_text: str
    failure_code: None
    provenance: TurnProvenance
    submitted_intent_fingerprint_v1: Digest | None
    submitted_intent_fingerprint_v2: Digest | None
    play_context_receipt: PlayRunTurnContextReceiptV2 | None
    attempt: Annotated[int, Field(ge=1)]
    claim_expires_at: None
    accepted_at: datetime
    completed_at: datetime
    updated_at: datetime

    @model_validator(mode="after")
    def lifecycle(self):
        validate_turn_lifecycle_fields(
            world_id=self.world_id,
            provenance=self.provenance,
            play_context_receipt=self.play_context_receipt,
            status=self.status,
            claim_expires_at=self.claim_expires_at,
            submitted_intent_fingerprint_v1=self.submitted_intent_fingerprint_v1,
            submitted_intent_fingerprint_v2=self.submitted_intent_fingerprint_v2,
        )
        if self.provenance.world_id != self.world_id:
            raise ValueError("Mixed answer provenance belongs to another World")
        return self


class RulesApprovedBaseV1(ClosedRulesModel):
    kind: Literal["approved"]
    turn: Turn


class RulesAbsentBaseV1(ClosedRulesModel):
    kind: Literal["absent"]


class RulesUnclaimedBaseV1(ClosedRulesModel):
    kind: Literal["unclaimed"]
    graph_context_receipt: GraphContextReceipt
    graph_context_execution: PlanWorldGraphExecution


RulesBaseProjectionV1 = Annotated[
    RulesApprovedBaseV1 | RulesAbsentBaseV1 | RulesUnclaimedBaseV1,
    Field(discriminator="kind"),
]


def validate_unclaimed_receipt_owner(
    envelope: CompletedTurnEnvelopeV1 | Turn, receipt: GraphContextReceipt
) -> None:
    if isinstance(receipt, BuildGraphContextReceiptV1):
        # The shared Graph validator checks Build source/provenance exactly.
        if (
            receipt.source_basis.world_id != envelope.world_id
            or receipt.graph_authority.managed_world_id != envelope.world_id
        ):
            raise ValueError("Unclaimed Build receipt belongs to another World")
        return
    if not isinstance(receipt, PlanWorldGraphContextReceiptV1):
        raise ValueError("Unknown unclaimed Graph receipt")
    primary = envelope.provenance.primary_work
    basis = receipt.plan_basis
    if (
        envelope.provenance.surface_resolution != "resolved"
        or envelope.provenance.surface_id != "plan"
        or primary.resolution != "resolved"
        or primary.kind != "plan"
        or basis.world_id != envelope.world_id
        or receipt.graph_authority.managed_world_id != envelope.world_id
        or (
            primary.object_id,
            primary.object_revision,
            primary.work_revision_id,
            primary.revision_n,
            primary.content_sha256,
        )
        != (
            basis.document_id,
            basis.object_revision,
            basis.work_revision_id,
            basis.revision_n,
            basis.content_sha256,
        )
    ):
        raise ValueError("Unclaimed Plan receipt differs from frozen provenance")
    targets = [
        ref
        for ref in envelope.provenance.supporting_work
        if ref.kind == "dmb_plan_playable_target_v1"
    ]
    if (
        len(targets) > 1
        or (decode_plan_playable_target_reference(targets[0]) if targets else None)
        != receipt.playable_target
    ):
        raise ValueError("Unclaimed Plan target differs from frozen provenance")


def validate_graph_producer_join(
    execution: PlanWorldGraphExecution, binding: RulesAcceptedBindingV1
) -> None:
    authorizations = [
        item
        for item in execution.events
        if isinstance(item, ProviderAttemptAuthorizedEventV1)
        and item.provider_attempt_id == binding.producing_provider_attempt_id
    ]
    outcomes = [
        item
        for item in execution.events
        if isinstance(item, ProviderOutcomeEventV1)
        and item.provider_attempt_id == binding.producing_provider_attempt_id
    ]
    if (
        len(authorizations) != 1
        or authorizations[0].envelope_sha256 != binding.request_envelope_sha256
        or not outcomes
        or outcomes[-1].outcome != "response_received"
    ):
        raise ValueError(
            "Mixed Rules/Graph answer lacks the same acknowledged producing request"
        )


class MixedCompletedTurnV1(ClosedRulesModel):
    schema_: Literal["dmb_mixed_completed_turn_v1"] = Field(alias="schema")
    envelope: CompletedTurnEnvelopeV1
    assistant_text: Annotated[str, Field(min_length=1, max_length=32000)]
    accepted_binding: RulesAcceptedBindingV1
    accepted_binding_sha256: Digest
    base_projection: RulesBaseProjectionV1

    @model_validator(mode="after")
    def exact_completed_record(self):
        envelope = self.envelope
        binding = self.accepted_binding
        base = self.base_projection
        if (
            binding.world_id,
            binding.conversation_id,
            binding.turn_id,
            binding.product_attempt,
            binding.accepted_turn_revision,
        ) != (
            envelope.world_id,
            envelope.conversation_id,
            envelope.turn_id,
            envelope.attempt,
            envelope.revision,
        ):
            raise ValueError(
                "Mixed answer differs from accepted owner, attempt or revision"
            )
        if self.accepted_binding_sha256 != canonical_sha256(binding):
            raise ValueError("Mixed accepted summary differs from its durable seal")
        if base.kind != binding.base_disposition:
            raise ValueError("Mixed base projection differs from accepted disposition")
        segments = ()
        if isinstance(base, RulesApprovedBaseV1):
            turn = base.turn
            if turn.completion is None:
                raise ValueError("Approved base requires its existing typed completion")
            for key in type(envelope).model_fields:
                if getattr(turn, key) != getattr(envelope, key):
                    raise ValueError(
                        "Approved base owner/lifecycle differs from mixed envelope"
                    )
            if binding.graph_used != ("world_graph" in turn.completion.answer_basis):
                raise ValueError("Mixed summary cannot relabel base Graph grounding")
            segments = tuple(item.text for item in turn.completion.answer_segments)
            if turn.assistant_text != "\n".join(segments):
                raise ValueError(
                    "Approved base text differs from its completion subsequence"
                )
            if turn.graph_context_execution is not None:
                graph_bindings = [
                    item
                    for item in turn.graph_context_execution.events
                    if isinstance(item, CompletionBindingEventV1)
                ]
                if (
                    len(graph_bindings) != 1
                    or graph_bindings[0].provider_attempt_id
                    != binding.producing_provider_attempt_id
                ):
                    raise ValueError(
                        "Approved Graph completion has a different Rules producer"
                    )
                validate_graph_producer_join(turn.graph_context_execution, binding)
        elif isinstance(base, RulesUnclaimedBaseV1):
            validate_turn_graph_fields(
                provenance=envelope.provenance,
                submitted_intent_fingerprint_v2=envelope.submitted_intent_fingerprint_v2,
                graph_context_receipt=base.graph_context_receipt,
                graph_context_execution=base.graph_context_execution,
                completion=None,
                assistant_text=None,
            )
            validate_unclaimed_receipt_owner(envelope, base.graph_context_receipt)
            if any(
                isinstance(item, CompletionBindingEventV1)
                for item in base.graph_context_execution.events
            ):
                raise ValueError(
                    "Unclaimed Graph execution cannot carry an answer binding"
                )
            validate_graph_producer_join(base.graph_context_execution, binding)
        binding.validate_text(self.assistant_text, segments)
        return self


TurnReadModel = Turn | MixedCompletedTurnV1


class MixedHistoryAttributionV1(ClosedRulesModel):
    schema_: Literal["dmb_mixed_history_attribution_v1"] = Field(alias="schema")
    source_sequence: Annotated[int, Field(ge=1)]
    accepted_binding: RulesAcceptedBindingV1
    base_attribution: "PlanAskHistoryAttributionV1 | None"

    @model_validator(mode="after")
    def exact_base_attribution(self):
        base = self.base_attribution
        binding = self.accepted_binding
        if (binding.base_disposition == "approved") != (base is not None):
            raise ValueError(
                "Mixed Plan history base attribution differs from its disposition"
            )
        if base is not None and (
            base.source_turn_id != binding.turn_id
            or base.source_conversation_id != binding.conversation_id
            or base.source_sequence != self.source_sequence
        ):
            raise ValueError(
                "Mixed Plan history base attribution differs from its owner"
            )
        if base is not None and binding.graph_used != (
            "world_graph" in base.answer_basis
        ):
            raise ValueError("Mixed Plan history cannot relabel Graph grounding")
        return self

    def validate_visible_pair(
        self, *, record_id: UUID, sequence: int, answer: str
    ) -> None:
        if (
            self.accepted_binding.turn_id != record_id
            or self.source_sequence != sequence
        ):
            raise ValueError("Mixed history attribution differs from its visible pair")
        segments = (
            tuple(segment.text for segment in self.base_attribution.answer_segments)
            if self.base_attribution is not None
            else ()
        )
        self.accepted_binding.validate_text(answer, segments)
