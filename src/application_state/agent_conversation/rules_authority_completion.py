"""Deterministic Rules acceptance values; the caller owns the atomic SQL commit."""

from __future__ import annotations

from uuid import UUID
from typing import Annotated, Literal
from pydantic import Field, model_validator
from .types import TurnResult, CitedSourceTurnResult

from .rules_authority_events import (
    RulesCompletionBoundV1,
    RulesCompletionV1,
    RulesExecutionV1,
    RulesProviderAuthorizedV1,
)
from .rules_authority_types import (
    AnswerCompositionV1,
    ClosedRulesModel,
    RulesScopeV1,
    RulesAcceptedBindingV1,
    RulesClaimV1,
    RulesSupportRefV1,
    SegmentMapItemV1,
    SourceAffordanceV1,
    canonical_sha256,
)


def prepare_rules_acceptance(
    execution: RulesExecutionV1,
    composition: AnswerCompositionV1,
    *,
    producing_provider_attempt_id: UUID,
    accepted_turn_revision: int,
    event_id: UUID,
    base_segments: tuple[str, ...] = (),
    graph_used: bool = False,
) -> tuple[RulesExecutionV1, RulesAcceptedBindingV1]:
    """Build a sealed map without source/answer copies in the history summary."""
    if execution.state != "active":
        raise ValueError("Only an active Rules attempt can prepare acceptance")
    body = composition.render(base_segments)
    authorizations = [
        item
        for item in execution.events
        if isinstance(item, RulesProviderAuthorizedV1)
        and item.provider_attempt_id == producing_provider_attempt_id
    ]
    if len(authorizations) != 1:
        raise ValueError("Rules acceptance has no unique producing request")
    source_refs = {}
    claim_refs = {}
    items = []
    offset = 0
    for ordinal, ref in enumerate(composition.ordered_refs):
        fields = dict(
            base_segment_index=None,
            rules_claim_id=None,
            rules_context_id=None,
            category=None,
            support_refs=(),
        )
        if ref.domain == "base":
            text = base_segments[ref.segment_index]
            domain = "base"
            fields["base_segment_index"] = ref.segment_index
        else:
            segment = composition.rules_segments[ref.segment_index]
            text = segment.text
            domain = segment.kind
            if isinstance(segment, RulesClaimV1):
                fields.update(
                    rules_claim_id=segment.claim_id, support_refs=segment.support_refs
                )
                claim_refs[segment.claim_id] = segment.support_refs
                for support_ref in segment.support_refs:
                    stored = execution.supports.get(support_ref.support_id)
                    if (
                        stored is None
                        or stored.support_sha256 != support_ref.support_sha256
                    ):
                        raise ValueError("Rules acceptance cites an unadmitted source")
                    source_refs[support_ref.support_id] = support_ref.support_sha256
            else:
                fields.update(
                    rules_context_id=segment.segment_id, category=segment.category
                )
        items.append(
            SegmentMapItemV1(
                ordinal=ordinal,
                domain=domain,
                text_start=offset,
                text_end=offset + len(text),
                **fields,
            )
        )
        offset += len(text) + 1
    table = []
    for key, digest in source_refs.items():
        source = execution.supports[key].support
        label = f"{source.source_title} · {source.section}"
        if source.printed_page is not None:
            label += f" · p. {source.printed_page}"
        table.append(
            SourceAffordanceV1(
                support_id=key, support_sha256=digest, source_label=label[:160]
            )
        )
    scope = execution.scope
    from hashlib import sha256

    binding = RulesAcceptedBindingV1(
        schema="dmb_rules_accepted_binding_v1",
        world_id=scope.world_id,
        conversation_id=scope.conversation_id,
        turn_id=scope.turn_id,
        corpus_sha256=scope.corpus_sha256,
        ruleset_id=scope.ruleset_id,
        accepted_turn_revision=accepted_turn_revision,
        product_attempt=scope.product_attempt,
        execution_id=scope.execution_id,
        producing_provider_attempt_id=producing_provider_attempt_id,
        request_envelope_sha256=authorizations[0].request_envelope_sha256,
        composition_sha256=canonical_sha256(composition),
        assistant_text_sha256=composition.assistant_text_sha256,
        base_text_sha256=sha256("\n".join(base_segments).encode()).hexdigest()
        if base_segments
        else None,
        base_disposition=composition.base_disposition,
        segment_map=tuple(items),
        support_table=tuple(table),
        graph_used=graph_used,
    )
    binding.validate_text(body, base_segments)
    completion = RulesCompletionV1(
        schema="dmb_rules_completion_v1",
        execution_id=scope.execution_id,
        producing_provider_attempt_id=producing_provider_attempt_id,
        request_envelope_sha256=binding.request_envelope_sha256,
        composition_sha256=binding.composition_sha256,
        claim_support_refs=claim_refs,
        approved_support_refs=tuple(
            RulesSupportRefV1(support_id=key, support_sha256=digest)
            for key, digest in source_refs.items()
        ),
    )
    bound = RulesCompletionBoundV1(
        event_id=event_id,
        sequence=len(execution.events),
        execution_id=scope.execution_id,
        kind="completion_bound",
        producing_provider_attempt_id=producing_provider_attempt_id,
        composition_sha256=binding.composition_sha256,
        assistant_text_sha256=binding.assistant_text_sha256,
        accepted_binding_sha256=canonical_sha256(binding),
        claim_support_refs=claim_refs,
        accepted_turn_revision=accepted_turn_revision,
    )
    data = execution.model_dump(mode="json", by_alias=True)
    data.update(
        state="accepted",
        composition=composition.model_dump(mode="json", by_alias=True),
        rules_completion=completion.model_dump(mode="json", by_alias=True),
    )
    data["events"].append(bound.model_dump(mode="json", by_alias=True))
    import json

    return RulesExecutionV1.model_validate_json(
        json.dumps(data, ensure_ascii=False)
    ), binding


class MixedTurnResultV1(ClosedRulesModel):
    """Internal mixed result; base proof remains its existing typed result."""

    schema_: Literal["dmb_mixed_turn_result_v1"] = Field(alias="schema")
    scope: RulesScopeV1
    expected_turn_revision: Annotated[int, Field(ge=1)]
    expected_rules_revision: Annotated[int, Field(ge=1)]
    assistant_text: Annotated[str, Field(min_length=1, max_length=32000)]
    composition: AnswerCompositionV1
    producing_provider_attempt_id: UUID
    base_result: CitedSourceTurnResult | TurnResult | None

    @model_validator(mode="after")
    def exact_partitions(self):
        base = self.base_result
        scope = self.scope
        if (self.composition.base_disposition == "approved") != (base is not None):
            raise ValueError(
                "Mixed base result differs from its composition disposition"
            )
        segments = ()
        if base is not None:
            if (
                base.world_id,
                base.conversation_id,
                base.turn_id,
                base.expected_revision,
            ) != (
                scope.world_id,
                scope.conversation_id,
                scope.turn_id,
                self.expected_turn_revision,
            ):
                raise ValueError("Mixed base result differs from its owner or revision")
            if (
                base.completion is None
                or base.producing_provider_attempt_id
                != self.producing_provider_attempt_id
            ):
                raise ValueError(
                    "Mixed approved base needs its same producing completion"
                )
            segments = tuple(item.text for item in base.completion.answer_segments)
            if base.assistant_text != "\n".join(segments):
                raise ValueError(
                    "Mixed base text differs from exact base completion segments"
                )
        if self.composition.render(segments) != self.assistant_text:
            raise ValueError("Mixed text differs from its ordered composition")
        return self
