"""Closed Rules authority values. No corpus lookup, inference, or Graph authority."""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

Digest = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
Identity = Annotated[str, Field(min_length=1, max_length=128)]
Label = Annotated[str, Field(min_length=1, max_length=500)]
MAX_LEDGER_BYTES = 256 * 1024
MAX_BINDING_BYTES = 32 * 1024
MAX_SUPPORT_BYTES = 16 * 1024
MAX_PRESENTATION_BYTES = 64 * 1024


def canonical_bytes(value: BaseModel | object) -> bytes:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json", by_alias=True)
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")


def canonical_sha256(value: BaseModel | object) -> str:
    return sha256(canonical_bytes(value)).hexdigest()


class ClosedRulesModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True, revalidate_instances="always", validate_by_name=True)


class RulesBudgetV1(ClosedRulesModel):
    calls: Literal[6]
    distinct_questions: Literal[4]
    hits_per_query: Literal[4]
    supports: Literal[16]
    novel_excerpt_utf8: Literal[16384]
    presentation_utf8: Literal[65536]
    provider_requests: Literal[64]
    events: Literal[256]
    ledger_utf8: Literal[262144]

    @model_validator(mode="before")
    @classmethod
    def exact_integer_budget(cls, value):
        if isinstance(value, dict) and any(type(item) is not int for item in value.values()):
            raise ValueError("Rules budgets require exact integer constants")
        return value


RULES_BUDGET_V1 = RulesBudgetV1(calls=6, distinct_questions=4, hits_per_query=4, supports=16,
    novel_excerpt_utf8=16384, presentation_utf8=65536, provider_requests=64, events=256, ledger_utf8=262144)


class RulesScopeV1(ClosedRulesModel):
    schema_: Literal["dmb_rules_scope_v1"] = Field(alias="schema")
    execution_id: UUID
    world_id: Annotated[str, Field(min_length=1, max_length=256)]
    conversation_id: UUID
    turn_id: UUID
    product_attempt: Annotated[int, Field(ge=1)]
    ruleset_id: Annotated[str, Field(pattern=r"^[a-z0-9_]{1,80}$")]
    corpus_sha256: Digest
    authorization_id: UUID
    capability_policy_sha256: Digest
    budget: RulesBudgetV1


class RulesSupportV1(ClosedRulesModel):
    schema_: Literal["dmb_rules_support_v1"] = Field(alias="schema")
    support_id: UUID
    corpus_sha256: Digest
    ruleset_id: Annotated[str, Field(pattern=r"^[a-z0-9_]{1,80}$")]
    unit_id: Digest
    full_text_sha256: Digest
    excerpt_start: Annotated[int, Field(ge=0, le=8192)]
    excerpt_end: Annotated[int, Field(ge=1, le=8192)]
    excerpt_text: Annotated[str, Field(min_length=1, max_length=8192)]
    excerpt_sha256: Digest
    source_title: Label
    section: Label
    source_uri: Annotated[str, Field(pattern=r"^https://[^\s]+$", max_length=1000)]
    source_sha256: Digest
    page_fingerprint: Digest
    pdf_page_index: Annotated[int, Field(ge=0, le=100000)]
    printed_page: Annotated[int, Field(ge=1, le=100000)] | None

    @model_validator(mode="after")
    def exact_excerpt(self):
        if self.excerpt_end - self.excerpt_start != len(self.excerpt_text):
            raise ValueError("Rules excerpt codepoint range differs from its text")
        if sha256(self.excerpt_text.encode("utf-8")).hexdigest() != self.excerpt_sha256:
            raise ValueError("Rules excerpt hash differs from its text")
        if len(self.excerpt_text.encode("utf-8")) > MAX_SUPPORT_BYTES:
            raise ValueError("Rules excerpt exceeds its UTF8 budget")
        if len(canonical_bytes(self)) > MAX_BINDING_BYTES:
            raise ValueError("Rules support exceeds its serialized budget")
        return self


class RulesSupportRefV1(ClosedRulesModel):
    support_id: UUID
    support_sha256: Digest


class RulesClaimV1(ClosedRulesModel):
    kind: Literal["rules_claim"]
    claim_id: Identity
    text: Annotated[str, Field(min_length=1, max_length=4000)]
    support_refs: Annotated[tuple[RulesSupportRefV1, ...], Field(min_length=1, max_length=4)]

    @model_validator(mode="after")
    def unique_supports(self):
        if len({ref.support_id for ref in self.support_refs}) != len(self.support_refs):
            raise ValueError("Rules claim repeats an ambiguous support identity")
        return self


class RulesContextV1(ClosedRulesModel):
    kind: Literal["rules_context"]
    segment_id: Identity
    text: Annotated[str, Field(min_length=1, max_length=4000)]
    category: Literal["interpretation", "gap", "connective"]


RulesSegmentV1 = Annotated[RulesClaimV1 | RulesContextV1, Field(discriminator="kind")]


class OrderedAnswerRefV1(ClosedRulesModel):
    domain: Literal["base", "rules"]
    segment_index: Annotated[int, Field(ge=0, le=127)]


class AnswerCompositionV1(ClosedRulesModel):
    schema_: Literal["dmb_answer_composition_v1"] = Field(alias="schema")
    base_disposition: Literal["absent", "approved", "unclaimed"]
    ordered_refs: Annotated[tuple[OrderedAnswerRefV1, ...], Field(min_length=1, max_length=128)]
    rules_segments: Annotated[tuple[RulesSegmentV1, ...], Field(max_length=32)]
    assistant_text_sha256: Digest

    @model_validator(mode="after")
    def exact_partition(self):
        base_indices = [ref.segment_index for ref in self.ordered_refs if ref.domain == "base"]
        if base_indices != list(range(len(base_indices))):
            raise ValueError("Base answer subsequence must preserve exact segment order")
        if (self.base_disposition == "approved") != bool(base_indices):
            raise ValueError("Only an approved base domain may have base segments")
        rules_indices = [ref.segment_index for ref in self.ordered_refs if ref.domain == "rules"]
        if sorted(rules_indices) != list(range(len(self.rules_segments))):
            raise ValueError("Rules composition must use every segment exactly once")
        identities = [seg.claim_id if isinstance(seg, RulesClaimV1) else seg.segment_id for seg in self.rules_segments]
        if len(identities) != len(set(identities)):
            raise ValueError("Rules segment identities must be unambiguous")
        if sum(isinstance(seg, RulesClaimV1) for seg in self.rules_segments) > 16:
            raise ValueError("Too many Rules claims")
        if len(canonical_bytes(self)) > MAX_LEDGER_BYTES:
            raise ValueError("Answer composition exceeds its serialized budget")
        return self

    def render(self, base_segments: tuple[str, ...] = ()) -> str:
        expected = sum(ref.domain == "base" for ref in self.ordered_refs)
        if len(base_segments) != expected:
            raise ValueError("Base completion does not match composition partition")
        texts = [base_segments[ref.segment_index] if ref.domain == "base" else self.rules_segments[ref.segment_index].text for ref in self.ordered_refs]
        if any(not text for text in texts):
            raise ValueError("Answer segments must be nonempty")
        answer = "\n".join(texts)
        if len(answer) > 32000 or sha256(answer.encode("utf-8")).hexdigest() != self.assistant_text_sha256:
            raise ValueError("Full answer differs from its approved composition")
        return answer


class SegmentMapItemV1(ClosedRulesModel):
    ordinal: Annotated[int, Field(ge=0, le=127)]
    domain: Literal["base", "rules_claim", "rules_context"]
    text_start: Annotated[int, Field(ge=0, le=32000)]
    text_end: Annotated[int, Field(ge=1, le=32000)]
    base_segment_index: Annotated[int, Field(ge=0, le=127)] | None
    rules_claim_id: Identity | None
    rules_context_id: Identity | None
    category: Literal["interpretation", "gap", "connective"] | None
    support_refs: Annotated[tuple[RulesSupportRefV1, ...], Field(max_length=4)]

    @model_validator(mode="after")
    def domain_fields(self):
        if self.text_end <= self.text_start:
            raise ValueError("Empty or reversed answer segment range")
        if self.domain == "base":
            valid = self.base_segment_index is not None and self.rules_claim_id is None and self.rules_context_id is None and self.category is None and not self.support_refs
        elif self.domain == "rules_claim":
            valid = self.base_segment_index is None and self.rules_claim_id is not None and self.rules_context_id is None and self.category is None and bool(self.support_refs)
        else:
            valid = self.base_segment_index is None and self.rules_claim_id is None and self.rules_context_id is not None and self.category is not None and not self.support_refs
        if not valid:
            raise ValueError("Answer range carries authority from another segment domain")
        if len({ref.support_id for ref in self.support_refs}) != len(self.support_refs):
            raise ValueError("Answer range repeats a Rules support")
        return self


class SourceAffordanceV1(ClosedRulesModel):
    support_id: UUID
    support_sha256: Digest
    source_label: Annotated[str, Field(min_length=1, max_length=160)]


class RulesAcceptedBindingV1(ClosedRulesModel):
    schema_: Literal["dmb_rules_accepted_binding_v1"] = Field(alias="schema")
    world_id: Annotated[str, Field(min_length=1, max_length=256)]
    conversation_id: UUID
    turn_id: UUID
    corpus_sha256: Digest
    ruleset_id: Annotated[str, Field(pattern=r"^[a-z0-9_]{1,80}$")]
    accepted_turn_revision: Annotated[int, Field(ge=1)]
    product_attempt: Annotated[int, Field(ge=1)]
    execution_id: UUID
    producing_provider_attempt_id: UUID
    request_envelope_sha256: Digest
    composition_sha256: Digest
    assistant_text_sha256: Digest
    base_text_sha256: Digest | None
    base_disposition: Literal["absent", "approved", "unclaimed"]
    segment_map: Annotated[tuple[SegmentMapItemV1, ...], Field(min_length=1, max_length=128)]
    support_table: Annotated[tuple[SourceAffordanceV1, ...], Field(max_length=16)]
    graph_used: bool

    @model_validator(mode="after")
    def exact_map(self):
        if len(canonical_bytes(self)) > MAX_BINDING_BYTES:
            raise ValueError("Accepted Rules summary exceeds its serialized budget")
        if [item.ordinal for item in self.segment_map] != list(range(len(self.segment_map))):
            raise ValueError("Answer map ordinals must be complete and ordered")
        if self.segment_map[0].text_start != 0 or any(b.text_start != a.text_end + 1 for a, b in zip(self.segment_map, self.segment_map[1:])):
            raise ValueError("Answer map has gaps or overlapping segments")
        if sum(item.domain != "base" for item in self.segment_map) > 32 or sum(item.domain == "rules_claim" for item in self.segment_map) > 16:
            raise ValueError("Accepted summary exceeds its Rules segment budget")
        base = [item.base_segment_index for item in self.segment_map if item.domain == "base"]
        if base != list(range(len(base))) or ((self.base_disposition == "approved") != bool(base)):
            raise ValueError("Answer map base partition does not match its disposition")
        if (self.base_text_sha256 is not None) != bool(base):
            raise ValueError("Only an approved base answer has a base text hash")
        if self.base_disposition != "approved" and self.graph_used:
            raise ValueError("Unused Graph context cannot become grounding")
        table = {item.support_id: item.support_sha256 for item in self.support_table}
        if len(table) != len(self.support_table):
            raise ValueError("Duplicate source affordance")
        used = {}
        ids = []
        for item in self.segment_map:
            if item.domain != "base":
                ids.append(item.rules_claim_id or item.rules_context_id)
            for ref in item.support_refs:
                if table.get(ref.support_id) != ref.support_sha256:
                    raise ValueError("Rules claim has no exact approved source affordance")
                used[ref.support_id] = ref.support_sha256
        if len(ids) != len(set(ids)) or set(used) != set(table):
            raise ValueError("Ambiguous Rules claims or unused source affordances")
        return self

    def validate_text(self, assistant_text: str, base_segments: tuple[str, ...] = ()) -> str:
        if len(assistant_text) > 32000 or sha256(assistant_text.encode("utf-8")).hexdigest() != self.assistant_text_sha256:
            raise ValueError("Stored mixed answer differs from its accepted hash")
        if self.segment_map[-1].text_end != len(assistant_text):
            raise ValueError("Stored mixed answer map does not cover the full text")
        base_texts = []
        for item in self.segment_map:
            if item.ordinal and assistant_text[item.text_start - 1:item.text_start] != "\n":
                raise ValueError("Stored mixed answer has another delimiter")
            text = assistant_text[item.text_start:item.text_end]
            if not text:
                raise ValueError("Stored mixed answer contains an empty segment")
            if item.domain == "base":
                base_texts.append(text)
        if tuple(base_texts) != base_segments:
            raise ValueError("Stored mixed answer differs from the validated base subsequence")
        base_text = "\n".join(base_texts)
        if base_texts and sha256(base_text.encode("utf-8")).hexdigest() != self.base_text_sha256:
            raise ValueError("Stored base answer hash does not match its subsequence")
        return base_text
