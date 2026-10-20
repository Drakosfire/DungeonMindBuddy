"""Exact mixed writer output; this never grants Graph or saved-source authority.

The outer raw response stays the comparison evidence. The base owner must still
validate the returned base_output against its own receipt and producing request.
No extracted base object is represented as another provider response.
"""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from .rules_authority_types import (
    AnswerCompositionV1, ClosedRulesModel, OrderedAnswerRefV1,
    RulesClaimV1, RulesContextV1, RulesSupportRefV1, canonical_bytes,
)
from .rules_authority_events import (
    RulesBuildProviderAuthorizedV1, RulesProviderAuthorizedV1,
    RulesProviderIncludedV1, RulesProviderOutcomeV1, ref_map,
)
from .rules_authority_input import verify_prepared_input
from . import source_writer_output as base_writer

POLICY = "exact_producer_composition_v1"
SCHEMA = "dmb_rules_mixed_answer_v1"
MAX_OUTPUT_BYTES = 262144
MAX_REQUEST_BYTES = 1050000
Text = Annotated[str, Field(min_length=1, max_length=4000)]


class WriterRulesClaimV1(ClosedRulesModel):
    kind: Literal["rules_claim"]
    text: Text
    support_ids: Annotated[tuple[str, ...], Field(min_length=1, max_length=4)]

    @field_validator("support_ids")
    @classmethod
    def exact_ids(cls, values):
        if len(set(values)) != len(values) or any(str(UUID(v)) != v for v in values):
            raise ValueError("Rules output requires distinct canonical support IDs")
        return values


class WriterRulesContextV1(ClosedRulesModel):
    kind: Literal["rules_context"]
    text: Text
    category: Literal["interpretation", "gap", "connective"]


class WriterOrderRefV1(ClosedRulesModel):
    domain: Literal["base", "rules"]
    segment_index: Annotated[int, Field(ge=0, le=31)] | None

    @model_validator(mode="after")
    def domain_index(self):
        if (self.domain == "base") != (self.segment_index is None):
            raise ValueError("Base output is an atomic block; Rules needs an index")
        return self


class RulesWriterAnswerV1(ClosedRulesModel):
    schema_: Literal["dmb_rules_mixed_answer_v1"] = Field(alias="schema")
    base_output: dict | None
    rules_segments: Annotated[tuple[Annotated[
        WriterRulesClaimV1 | WriterRulesContextV1, Field(discriminator="kind")
    ], ...], Field(max_length=32)]
    ordered_refs: Annotated[tuple[WriterOrderRefV1, ...], Field(min_length=1, max_length=33)]

    @model_validator(mode="after")
    def partitions(self):
        base = sum(ref.domain == "base" for ref in self.ordered_refs)
        if base != int(self.base_output is not None):
            raise ValueError("Mixed output needs exactly one marker for its base object")
        indices = [ref.segment_index for ref in self.ordered_refs if ref.domain == "rules"]
        if sorted(indices) != list(range(len(self.rules_segments))):
            raise ValueError("Mixed output must use each Rules segment exactly once")
        if sum(isinstance(seg, WriterRulesClaimV1) for seg in self.rules_segments) > 16:
            raise ValueError("Mixed output exceeds its Rules claim limit")
        if any(not seg.text.strip() for seg in self.rules_segments):
            raise ValueError("Blank Rules writer text")
        return self

    def composition(self, *, supplied_refs: tuple[RulesSupportRefV1, ...],
                    base_segments: tuple[str, ...], base_disposition: str) -> AnswerCompositionV1:
        """Use only independently normalized base text and actual included Rules refs."""
        if (self.base_output is not None) != bool(base_segments):
            raise ValueError("Base normalization differs from the raw base partition")
        if (base_disposition == "approved") != bool(base_segments):
            raise ValueError("Base disposition differs from independently approved text")
        if len(supplied_refs) > 16:
            raise ValueError("Too many producing Rules supports")
        supports = ref_map(supplied_refs)
        segments = []
        for index, segment in enumerate(self.rules_segments):
            identity = f"rules:{index}"
            if isinstance(segment, WriterRulesClaimV1):
                selected = tuple(UUID(value) for value in segment.support_ids)
                if any(key not in supports for key in selected):
                    raise ValueError("Rules output cites a support absent from its producing input")
                segments.append(RulesClaimV1(kind="rules_claim", claim_id=identity,
                    text=segment.text, support_refs=tuple(RulesSupportRefV1(
                        support_id=key, support_sha256=supports[key]) for key in selected)))
            else:
                segments.append(RulesContextV1(kind="rules_context", segment_id=identity,
                    text=segment.text, category=segment.category))
        order = []
        texts = []
        for ref in self.ordered_refs:
            if ref.domain == "base":
                order.extend(OrderedAnswerRefV1(domain="base", segment_index=i)
                             for i in range(len(base_segments)))
                texts.extend(base_segments)
            else:
                order.append(OrderedAnswerRefV1(domain="rules", segment_index=ref.segment_index))
                texts.append(segments[ref.segment_index].text)
        body = "\n".join(texts)
        result = AnswerCompositionV1(schema="dmb_answer_composition_v1",
            base_disposition=base_disposition, ordered_refs=tuple(order),
            rules_segments=tuple(segments), assistant_text_sha256=sha256(body.encode()).hexdigest())
        result.render(base_segments)  # Enforce full visible text/codepoint/partition bounds.
        return result


def parse_answer(raw: str) -> RulesWriterAnswerV1:
    if not isinstance(raw, str) or len(raw.encode("utf-8")) > MAX_OUTPUT_BYTES:
        raise ValueError("Mixed writer output exceeds its UTF8 byte limit")
    parsed = base_writer.strict_json(raw)  # Duplicate keys and nonfinite numbers reject.
    return RulesWriterAnswerV1.model_validate_json(json.dumps(parsed, ensure_ascii=False, allow_nan=False))


def _namespace_base_schema(schema: dict) -> tuple[dict, dict]:
    """Keep nested base schema references local without definition collisions."""
    definitions = schema.get("$defs", {})
    def rewrite(value):
        if isinstance(value, list):
            return [rewrite(item) for item in value]
        if not isinstance(value, dict):
            return value
        return {key: ("#/$defs/Base_" + item[len("#/$defs/"):]
                if key == "$ref" and isinstance(item, str) and item.startswith("#/$defs/")
                else rewrite(item)) for key, item in value.items() if key != "$defs"}
    return rewrite(schema), {"Base_" + key: rewrite(value) for key, value in definitions.items()}


def build_output_format(packet: dict, supplied_refs: tuple[RulesSupportRefV1, ...]) -> dict:
    """Freeze finite selectors for the actual Build source writer input only."""
    if packet.get("rules_mixed_output_policy") != POLICY:
        raise ValueError("Build writer did not select the mixed output policy")
    if len(supplied_refs) > 16:
        raise ValueError("Too many producing Rules supports")
    supports = ref_map(supplied_refs)
    schema = RulesWriterAnswerV1.model_json_schema(by_alias=True)
    base_schema, defs = _namespace_base_schema(base_writer.finite_output_schema(
        packet, requested_detail_gaps=True))
    schema["properties"]["base_output"] = {"anyOf": [base_schema, {"type": "null"}]}
    schema["$defs"].update(defs)
    # Avoid discriminator/OpenAPI mappings in a strict JSON-schema request.
    variants = [{"$ref": "#/$defs/WriterRulesContextV1"}]
    if supports:
        schema["$defs"]["WriterRulesClaimV1"]["properties"]["support_ids"]["items"] = {
            "type": "string", "enum": sorted(str(key) for key in supports)}
        variants.insert(0, {"$ref": "#/$defs/WriterRulesClaimV1"})
    else:
        del schema["$defs"]["WriterRulesClaimV1"]
    schema["properties"]["rules_segments"]["items"] = {"anyOf": variants}
    return {"type": "json_schema", "name": SCHEMA, "strict": True, "schema": schema}


def verify_build_output(execution, *, producing_provider_attempt_id: UUID,
                        prepared_request_json: str, raw_output_json: str, trace: dict
                        ) -> RulesWriterAnswerV1:
    """Prove exact raw outer output, never approve its base source completion.

    The atomic completion caller must additionally reconstruct/validate base_output
    through the existing Graph/source owner using this same actual request.
    """
    if execution.state != "active":
        raise ValueError("Mixed writer requires an active Rules execution")
    if not isinstance(prepared_request_json, str) or len(prepared_request_json.encode()) > MAX_REQUEST_BYTES:
        raise ValueError("Mixed writer request exceeds its byte limit")
    auths = [e for e in execution.events if isinstance(e, RulesProviderAuthorizedV1)]
    auth = auths[-1] if auths else None
    if (not isinstance(auth, RulesBuildProviderAuthorizedV1)
            or auth.provider_attempt_id != producing_provider_attempt_id or auth.role != "writer"
            or auth.carrier_schema != "dmb_build_source_passage_writer_v1"):
        raise ValueError("Mixed output lacks its actual final Build source writer")
    included = [e for e in execution.events if isinstance(e, RulesProviderIncludedV1)
                and e.provider_attempt_id == producing_provider_attempt_id]
    outcomes = [e for e in execution.events if isinstance(e, RulesProviderOutcomeV1)
                and e.provider_attempt_id == producing_provider_attempt_id]
    if len(included) != 1 or len(outcomes) != 1 or outcomes[0].status != "answered":
        raise ValueError("Mixed producing writer has no unique acknowledged input/answer")
    verify_prepared_input(execution, auth, prepared_request_json)
    verify_prepared_input(execution, included[0], prepared_request_json)
    request = base_writer.strict_json(prepared_request_json)
    packet = base_writer.strict_json(request["input"])
    text = request.get("text")
    fmt = text.get("format") if isinstance(text, dict) else None
    if canonical_bytes(fmt) != canonical_bytes(build_output_format(packet, included[0].support_refs)):
        raise ValueError("Mixed writer format differs from exact producing selectors")
    scope = execution.scope
    if (trace.get("world_id"), trace.get("conversation_id"), trace.get("turn_id"), trace.get("attempt")) != (
            scope.world_id, str(scope.conversation_id), str(scope.turn_id), scope.product_attempt
    ) or type(trace.get("attempt")) is not int or trace.get("capture_status") not in {"recording", "complete"}:
        raise ValueError("Mixed output capture belongs to another attempt or is incomplete")
    item_id = f"unvalidated-rules-answer:{producing_provider_attempt_id}:{scope.execution_id}"
    drafts = [m for o in trace.get("observations", [])
              if o.get("kind") == "context_snapshot" and o.get("stage") == "after"
              for m in o.get("materials", []) if m.get("item_id") == item_id]
    if (len(drafts) != 1 or drafts[0].get("text") != raw_output_json
            or drafts[0].get("state") != "model_context" or drafts[0].get("role") != "assistant"):
        raise ValueError("Mixed output differs from its exact captured producer bytes")
    answer = parse_answer(raw_output_json)
    supplied = ref_map(included[0].support_refs)
    for segment in answer.rules_segments:
        if isinstance(segment, WriterRulesClaimV1) and any(
                UUID(key) not in supplied for key in segment.support_ids):
            raise ValueError("Rules output cites a support absent from its producing input")
    return answer
