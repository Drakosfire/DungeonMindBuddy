"""Draft-aware output: authored discussion references never become source citations."""
from __future__ import annotations

from pydantic import Field, TypeAdapter, model_validator
from typing import Literal

from .build_draft_context import (
    _Frozen, DraftReferenceClaimV1, context_record, validate_writer_reference, resolve_body_aliases,
)
from .source_writer_output import (
    PassageFact, SavedFact, Suggestion, RequestedDetailGap, strict_json, gap_messages,
)

FORMAT = "build_working_draft_answer_v1"
STATUSES = ("authored_grounded", "authored_grounded_partial", "source_grounded",
    "source_grounded_partial", "creative_proposal", "insufficient_evidence")


class DraftDiscussionV1(_Frozen):
    kind: Literal["discussion"]
    text: str = Field(min_length=1)


class DraftWriterAnswerV1(_Frozen):
    answer_context_status: Literal["authored_grounded", "authored_grounded_partial", "source_grounded",
        "source_grounded_partial", "creative_proposal", "insufficient_evidence"]
    answer_segments: list[DraftReferenceClaimV1 | PassageFact | SavedFact | Suggestion | DraftDiscussionV1] = Field(min_length=1)
    limitations: list[Literal["missing_requested_details", "partial_retrieval", "unresolved_conflict"]]
    requested_detail_gaps: list[RequestedDetailGap]

    @model_validator(mode="after")
    def exact_status(self):
        if len(set(self.limitations)) != len(self.limitations):
            raise ValueError("Duplicate draft-answer limitation")
        if any(not segment.text.strip() for segment in self.answer_segments):
            raise ValueError("Blank draft-answer segment")
        has_draft = any(isinstance(s, DraftReferenceClaimV1) for s in self.answer_segments)
        has_source = any(isinstance(s, (PassageFact, SavedFact)) for s in self.answer_segments)
        has_suggestion = any(isinstance(s, Suggestion) for s in self.answer_segments)
        base = "authored_grounded" if has_draft else "source_grounded" if has_source else "creative_proposal" if has_suggestion else "insufficient_evidence"
        if base == "insufficient_evidence" and not self.limitations:
            raise ValueError("An evidence gap requires its explicit qualification")
        expected = base + "_partial" if self.limitations and base in {"authored_grounded","source_grounded"} else base
        if self.answer_context_status != expected:
            raise ValueError("Draft answer status must follow its authored/source segments and limitations")
        if self.requested_detail_gaps and "missing_requested_details" not in self.limitations:
            raise ValueError("Draft answer gaps require missing-details qualification")
        return self


def output_schema(packet):
    from .source_writer_output import finite_output_schema
    from uuid import UUID
    lane = packet.get("working_draft_context")
    if not isinstance(lane, dict):
        raise ValueError("Draft output requires its captured working context")
    record_id = str(UUID(lane["record_id"]))
    source_packet = {key: value for key, value in resolve_body_aliases(packet).items() if key != "working_draft_context"}
    source_schema = finite_output_schema(source_packet, requested_detail_gaps=True)
    schema = DraftWriterAnswerV1.model_json_schema()
    # The draft wrapper adds authored statuses, but cannot broaden the source
    # status domain already derived from the exact retrieval disposition.
    source_statuses = source_schema["properties"]["answer_context_status"]["enum"]
    if "source_grounded" not in source_statuses:
        schema["properties"]["answer_context_status"]["enum"].remove("source_grounded")
    schema["$defs"]["DraftReferenceClaimV1"]["properties"]["draft_record_id"] = {
        "type": "string", "enum": [record_id]}
    for name, field in (("PassageFact", "passage_handles"), ("SavedFact", "section_read_ids")):
        if name in source_schema["$defs"]:
            schema["$defs"][name]["properties"][field] = source_schema["$defs"][name]["properties"][field]
        else:
            del schema["$defs"][name]
    schema["properties"]["answer_segments"]["items"]["anyOf"] = [
        item for item in schema["properties"]["answer_segments"]["items"]["anyOf"]
        if item["$ref"].split("/")[-1] in schema["$defs"]]
    return schema


def normalize(raw, packet):
    body = strict_json(raw)
    # Status is a host-derived description, not a second model judgment. Keep
    # typed segments/limitations and all later provenance checks authoritative.
    if isinstance(body, dict) and body.get("answer_context_status") in STATUSES and isinstance(body.get("answer_segments"), list) and isinstance(body.get("limitations"), list):
        segment_type = DraftReferenceClaimV1 | PassageFact | SavedFact | Suggestion | DraftDiscussionV1
        segments = TypeAdapter(list[segment_type]).validate_python(body["answer_segments"])
        base = ("authored_grounded" if any(isinstance(s, DraftReferenceClaimV1) for s in segments)
            else "source_grounded" if any(isinstance(s, (PassageFact, SavedFact)) for s in segments)
            else "creative_proposal" if any(isinstance(s, Suggestion) for s in segments)
            else "insufficient_evidence")
        body = {**body, "answer_context_status": base + "_partial" if body["limitations"] and base in {"authored_grounded", "source_grounded"} else base}
    answer = DraftWriterAnswerV1.model_validate(body)
    lane = packet["working_draft_context"]
    sources = [s for s in answer.answer_segments if isinstance(s, (PassageFact, SavedFact))]
    for segment in answer.answer_segments:
        if isinstance(segment, DraftReferenceClaimV1) and str(segment.draft_record_id) != lane["record_id"]:
            raise ValueError("Draft answer selected an unincluded working copy")
    disposition = packet.get("retrieval_disposition", {})
    if sources:
        required = set()
        if disposition.get("coverage_status") != "catalog_exhausted" or disposition.get("status") == "insufficient_evidence":
            required.add("partial_retrieval")
        if disposition.get("status") == "unresolved_conflict":
            required.add("unresolved_conflict")
        if not required.issubset(answer.limitations):
            raise ValueError("Draft answer omitted the related-source retrieval qualification")
    segments = [({"kind": "connective", "text": "Suggestion: " + s.text}
        if isinstance(s, Suggestion) else {"kind":"connective","text":s.text}
        if isinstance(s,DraftDiscussionV1) else s.model_dump(mode="json", by_alias=True)) for s in answer.answer_segments]
    # Missing World details qualify only those exact requested phrases, not the available draft.
    segments.extend(gap_messages(answer, packet))
    if "unresolved_conflict" in answer.limitations:
        segments.append({"kind": "connective", "text": "The related sources leave a conflict unresolved."})
    return {"answer_context_status": answer.answer_context_status, "answer_segments": segments}


def validate_completion(completion, receipt, execution, attempt_id):
    from . import types as t
    captured = context_record(execution)
    included = [e for e in execution.events if isinstance(e, t.BuildDraftProviderInclusionV1)
        and e.provider_attempt_id == attempt_id and e.draft_event_id == captured.event_id]
    attempts = [e for e in execution.events if isinstance(e,t.ProviderAttemptAuthorizedEventV1)
        and e.provider_attempt_id == attempt_id]
    if (len(included) != 1 or len(attempts) != 1 or included[0].envelope_sha256 != attempts[0].envelope_sha256
        or captured.record.snapshot.saved_basis() != receipt.source_basis.model_dump(mode="json", by_alias=True)):
        raise ValueError("Draft completion lacks its exact producing input")
    for segment in completion.answer_segments:
        if isinstance(segment, DraftReferenceClaimV1) and segment.draft_record_id != captured.record.record_id:
            raise ValueError("Draft completion refers to another captured working copy")


def validate_packet(packet, turn, auth):
    captured = context_record(turn.graph_context_execution)
    validate_writer_reference(packet.get("working_draft_context"), captured.record, turn)
    included = [e for e in turn.graph_context_execution.events
        if getattr(e,"kind",None) == "build_draft_provider_inclusion_v1"
        and e.provider_attempt_id == auth.provider_attempt_id]
    if len(included) != 1 or included[0].envelope_sha256 != auth.envelope_sha256:
        raise ValueError("Writer working draft was not included in its producing envelope")
