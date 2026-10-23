"""Typed source-writer output and deterministic host presentation.

This does not judge entailment. Handles remain subject to APP's durable receipt
checks; raw model output is comparison evidence, never knowledge authority.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Literal

from pydantic import Field, model_validator

from .types import StrictModel

POLICY = "cited_facts_host_limitations_v1"
SCHEMA_NAME = "build_cited_source_answer"
FINITE_SCHEMA_NAME = "build_cited_source_answer_v2"
GAP_SCHEMA_NAME = "build_cited_source_answer_v4"
GAP_POLICY = "exact_question_phrase_selected_excerpts_v1"
LIMITATIONS = {
    "missing_requested_details": "The retrieved evidence does not establish all the requested details.",
    "partial_retrieval": "This answer uses partial retrieval and does not establish corpus completeness.",
    "unresolved_conflict": "The retrieved evidence leaves a conflict unresolved.",
}


class PassageFact(StrictModel):
    kind: Literal["source_passage_claim"]
    text: str = Field(min_length=1, max_length=4000)
    passage_handles: list[str] = Field(min_length=1, max_length=128)


class SavedFact(StrictModel):
    kind: Literal["saved_source_claim"]
    text: str = Field(min_length=1, max_length=4000)
    section_read_ids: list[str] = Field(min_length=1, max_length=128)


class Suggestion(StrictModel):
    kind: Literal["suggestion"]
    text: str = Field(min_length=1, max_length=3988)


class CitedSourceAnswer(StrictModel):
    answer_context_status: Literal[
        "source_grounded", "source_grounded_partial", "source_insufficient_evidence"
    ]
    answer_segments: list[PassageFact | SavedFact | Suggestion] = Field(max_length=125)
    limitations: list[
        Literal["missing_requested_details", "partial_retrieval", "unresolved_conflict"]
    ] = Field(max_length=3)

    @model_validator(mode="after")
    def validate_content(self):
        if len(self.limitations) != len(set(self.limitations)):
            raise ValueError("Duplicate limitation code")
        facts = []
        for segment in self.answer_segments:
            if not segment.text.strip():
                raise ValueError("Blank writer segment")
            if isinstance(segment, (PassageFact, SavedFact)):
                facts.append(segment)
                ids = (
                    segment.passage_handles
                    if isinstance(segment, PassageFact)
                    else segment.section_read_ids
                )
                if any(not value.strip() for value in ids) or len(ids) != len(set(ids)):
                    raise ValueError("Fact selectors must be nonblank and distinct")
        if self.answer_context_status == "source_insufficient_evidence":
            if facts or not self.limitations:
                raise ValueError(
                    "Abstention requires host limitations without factual claims"
                )
        elif not facts:
            raise ValueError("Source-grounded output requires cited source facts")
        if self.answer_context_status == "source_grounded" and self.limitations:
            raise ValueError("Full support cannot carry limitations")
        if (
            self.answer_context_status == "source_grounded_partial"
            and not self.limitations
        ):
            raise ValueError("Partial support requires a limitation")
        return self


class RequestedDetailGap(StrictModel):
    question_phrase: str = Field(strict=True, min_length=1, max_length=256)


class CitedSourceAnswerWithGaps(CitedSourceAnswer):
    # Existing completion permits 128 segments: reserve 16 gaps and 3 limitations.
    answer_segments: list[PassageFact | SavedFact | Suggestion] = Field(max_length=109)
    requested_detail_gaps: list[RequestedDetailGap] = Field(max_length=16)

    @model_validator(mode="after")
    def validate_gaps(self):
        if self.requested_detail_gaps and (
            self.answer_context_status == "source_grounded"
            or "missing_requested_details" not in self.limitations
        ):
            raise ValueError("Requested-detail gaps require a missing-details limitation and partial/insufficient status")
        return self


def gap_messages(answer, packet):
    question = packet.get("user_question")
    if not isinstance(question, str) or not question.strip():
        raise ValueError("Requested-detail gaps require the exact user question")
    located = []
    for gap in answer.requested_detail_gaps:
        phrase = gap.question_phrase
        if (phrase != phrase.strip() or not all(char.isprintable() for char in phrase)
            or not any(char.isalnum() for char in phrase)):
            raise ValueError("Requested-detail gap is not a bounded displayable detail")
        start = question.find(phrase)
        if start < 0 or question.find(phrase, start + 1) >= 0:
            raise ValueError("Requested-detail phrase must occur exactly once in the original question")
        located.append((start, start + len(phrase), phrase))
    located.sort()
    if any(left[1] > right[0] for left, right in zip(located, located[1:])):
        raise ValueError("Requested-detail phrases must be distinct and nonoverlapping")
    messages = []
    for _, _, phrase in located:
        # User text stays literal in the Markdown conversation: no links, media,
        # HTML or formatting can be introduced through a question slice.
        literal = re.sub(r"([\\`*_{}\[\]()<>#+.!|~&\-])", r"\\\1", phrase)
        messages.append({"kind": "connective", "text":
            f"The selected source excerpts do not establish: “{literal}”."})
    return messages


def strict_json(raw: str):
    def unique(pairs):
        obj = {}
        for key, value in pairs:
            if key in obj:
                raise ValueError("Duplicate source writer JSON key")
            obj[key] = value
        return obj

    return json.loads(
        raw,
        object_pairs_hook=unique,
        parse_constant=lambda _: (_ for _ in ()).throw(
            ValueError("Nonfinite source writer JSON")
        ),
    )


def normalize(raw: str, packet: dict) -> dict:
    gap_policy = packet.get("requested_detail_gap_policy")
    if "requested_detail_gap_policy" in packet and gap_policy != GAP_POLICY:
        raise ValueError("Unknown requested-detail gap policy")
    answer_type = CitedSourceAnswerWithGaps if gap_policy == GAP_POLICY else CitedSourceAnswer
    answer = answer_type.model_validate(strict_json(raw))
    gaps = gap_messages(answer, packet) if gap_policy == GAP_POLICY else []
    disposition = packet.get("retrieval_disposition")
    if not isinstance(disposition, dict):
        raise ValueError("Cited source writer requires the host retrieval disposition")
    status = disposition.get("status")
    coverage = disposition.get("coverage_status")
    if status not in {
        "provisionally_supported",
        "insufficient_evidence",
        "unresolved_conflict",
    }:
        raise ValueError("Unknown host retrieval disposition")
    if coverage not in {
        "catalog_exhausted",
        "heuristic_exclusions",
        "heuristic_partial",
    }:
        raise ValueError("Unknown host retrieval coverage")
    required = set()
    if coverage != "catalog_exhausted":
        required.add("partial_retrieval")
    if status == "insufficient_evidence":
        if answer.answer_context_status == "source_insufficient_evidence":
            required.add("missing_requested_details")
        elif not {"missing_requested_details", "partial_retrieval"}.intersection(
            answer.limitations
        ):
            raise ValueError("Writer omitted the host retrieval limitation")
        # Acquisition uncertainty is not proof that a requested detail is absent
        # from the selected passages. Keep the answer partial either way.
        if answer.answer_context_status == "source_grounded":
            raise ValueError("Writer strengthened partial host retrieval")
    if status == "unresolved_conflict":
        required.add("unresolved_conflict")
    if not required.issubset(answer.limitations):
        raise ValueError("Writer omitted the host retrieval limitation")
    if required and answer.answer_context_status == "source_grounded":
        raise ValueError("Writer strengthened partial host retrieval")
    segments = []
    for segment in answer.answer_segments:
        if isinstance(segment, Suggestion):
            segments.append(
                {"kind": "connective", "text": "Suggestion: " + segment.text}
            )
        else:
            segments.append(segment.model_dump(mode="json"))
    # Append host-authored gaps after facts; existing citation indexes stay fixed.
    segments.extend(gaps)
    # Canonical ordering; fact indexes stay unchanged for saved/source bindings.
    segments.extend(
        {"kind": "connective", "text": text}
        for code, text in LIMITATIONS.items()
        if code in answer.limitations
    )
    return {
        "answer_context_status": answer.answer_context_status,
        "answer_segments": segments,
    }


def output_schema() -> dict:
    return CitedSourceAnswer.model_json_schema()


def finite_output_schema(packet: dict, *, requested_detail_gaps: bool = False) -> dict:
    """Narrow selectors to this exact packet; do not infer knowledge authority."""
    from .types import ValidatedBuildSectionReadV1

    if (
        not isinstance(packet, dict)
        or packet.get("source_writer_output_policy") != POLICY
    ):
        raise ValueError("Finite writer schema requires its source policy")
    passages, exposure = packet.get("opened_passages", []), packet.get("exposure", {})
    if (
        not isinstance(passages, list)
        or len(passages) > 16384
        or not isinstance(exposure, dict)
    ):
        raise ValueError("Malformed writer selector packet")
    sections = exposure.get("saved_sections", [])
    if not isinstance(sections, list) or len(sections) > 128:
        raise ValueError("Malformed saved-section selector packet")
    handles = set()
    for passage in passages:
        fields = (
            "text",
            "source_class",
            "source_artifact_id",
            "source_revision_id",
            "line_start",
            "line_end",
        )
        if not isinstance(passage, dict) or set(passage) != {*fields, "handle"}:
            raise ValueError("Malformed passage selector identity")
        text = passage["text"]
        if (
            not isinstance(text, str)
            or not text.strip()
            or len(text) > 12000
            or passage["source_class"] != "opened_source_passage_not_graph_truth"
            or any(
                not isinstance(passage[k], str) or not passage[k].strip()
                for k in ("source_artifact_id", "source_revision_id")
            )
        ):
            raise ValueError("Malformed passage selector identity")
        start, end = passage["line_start"], passage["line_end"]
        if not (start is None and end is None) and not (
            type(start) is int and type(end) is int and 0 < start <= end
        ):
            raise ValueError("Malformed passage selector range")
        handle = (
            "p"
            + hashlib.sha256(
                json.dumps(
                    {k: passage[k] for k in fields},
                    sort_keys=True,
                    ensure_ascii=False,
                    separators=(",", ":"),
                    allow_nan=False,
                ).encode()
            ).hexdigest()[:24]
        )
        if passage["handle"] != handle or handle in handles:
            raise ValueError("Invalid or duplicate passage selector")
        handles.add(handle)
    read_ids, event_ids = set(), set()
    for section in sections:
        read = ValidatedBuildSectionReadV1.model_validate(section)
        if (
            section.get("read_id") != str(read.read_id)
            or str(read.read_id) in read_ids
            or read.event_id in event_ids
        ):
            raise ValueError("Invalid or duplicate saved-section selector")
        read_ids.add(str(read.read_id))
        event_ids.add(read.event_id)
    from .build_primary_context import packet_rows
    for row in packet_rows(packet):
        if row["read_id"] in read_ids:
            raise ValueError("Primary section duplicated into selected evidence")
        read_ids.add(row["read_id"])
    if requested_detail_gaps and packet.get("requested_detail_gap_policy") != GAP_POLICY:
        raise ValueError("Gap output schema requires its exact packet capability")
    schema = CitedSourceAnswerWithGaps.model_json_schema() if requested_detail_gaps else output_schema()
    available = {
        "PassageFact": ("passage_handles", handles),
        "SavedFact": ("section_read_ids", read_ids),
    }
    for name, (field, values) in available.items():
        if values:
            schema["$defs"][name]["properties"][field]["items"] = {
                "type": "string",
                "enum": sorted(values),
            }
        else:
            del schema["$defs"][name]
    choices = schema["properties"]["answer_segments"]["items"]["anyOf"]
    schema["properties"]["answer_segments"]["items"]["anyOf"] = [
        choice for choice in choices if choice["$ref"].split("/")[-1] in schema["$defs"]
    ]
    if "writer_status_policy" in packet:
        from .build_primary_context import STATUS_POLICY, SCHEMA
        if packet["writer_status_policy"] != STATUS_POLICY or packet.get("schema") != SCHEMA:
            raise ValueError("Unknown writer status capability")
        disposition = packet.get("retrieval_disposition")
        if (not isinstance(disposition, dict)
                or disposition.get("status") not in {"provisionally_supported", "insufficient_evidence", "unresolved_conflict"}
                or disposition.get("coverage_status") not in {"catalog_exhausted", "heuristic_exclusions", "heuristic_partial"}):
            raise ValueError("Writer status schema requires exact host retrieval disposition")
        if (disposition.get("status") in {"insufficient_evidence", "unresolved_conflict"}
                or disposition.get("coverage_status") != "catalog_exhausted"):
            schema["properties"]["answer_context_status"]["enum"] = [
                "source_grounded_partial", "source_insufficient_evidence"]
    return schema


def validate_writer_format(fmt: dict, packet: dict) -> None:
    """Old captures keep their exact schema; V2 is exact packet-derived only."""
    if not isinstance(fmt, dict):
        raise ValueError("Source writer request lacks its frozen output schema")
    name = fmt.get("name")
    if name in {SCHEMA_NAME, FINITE_SCHEMA_NAME} and "requested_detail_gap_policy" in packet:
        raise ValueError("Historical writer format cannot claim the new gap capability")
    if name == SCHEMA_NAME:
        schema = output_schema()
    elif name == FINITE_SCHEMA_NAME:
        schema = finite_output_schema(packet)
    elif name == GAP_SCHEMA_NAME:
        schema = finite_output_schema(packet, requested_detail_gaps=True)
    else:
        raise ValueError("Source writer request has an unknown output schema")
    if (
        fmt != {"type": "json_schema", "name": name, "schema": schema, "strict": True}
        or fmt.get("strict") is not True
    ):
        raise ValueError("Source writer request lacks its frozen output schema")


def validate_completion_proof(result, turn, trace: dict) -> None:
    """Reconstruct the entire V2 completion from the actual captured producer.

    Request/output proof is transient: existing completion/execution persistence
    remains unchanged and old turns never acquire a new proof requirement.
    """
    from . import types as t

    if not isinstance(result, t.CitedSourceTurnResult):
        raise ValueError("Cited source completion requires producer output proof")
    execution = turn.graph_context_execution
    authorizations = [
        e
        for e in execution.events
        if isinstance(e, t.ProviderAttemptAuthorizedEventV1)
        and e.provider_attempt_id == result.producing_provider_attempt_id
    ]
    if len(authorizations) != 1:
        raise ValueError("Ambiguous producing source writer authorization")
    auth = authorizations[0]
    if (
        auth.provider,
        auth.model,
        auth.api_mode,
    ) != execution.policy.provider_roles.writer.identity() or hashlib.sha256(
        result.writer_request_json.encode()
    ).hexdigest() != auth.envelope_sha256:
        raise ValueError("Source writer request differs from producing authorization")
    receipt_sha = turn.graph_context_receipt.context_receipt_sha256
    draft_id = f"unvalidated-provider-answer:{auth.provider_attempt_id}:{receipt_sha}"
    if (
        trace.get("world_id") != turn.world_id
        or trace.get("turn_id") != str(turn.turn_id)
        or trace.get("conversation_id") != str(turn.conversation_id)
        or trace.get("attempt") != turn.attempt
        or trace.get("capture_status") not in {"recording", "complete"}
    ):
        raise ValueError(
            "Source writer capture is missing, incomplete or belongs to another attempt"
        )
    drafts = [
        m
        for o in trace.get("observations", [])
        if o.get("kind") == "context_snapshot" and o.get("stage") == "after"
        for m in o.get("materials", [])
        if m.get("item_id") == draft_id
    ]
    if (
        len(drafts) != 1
        or drafts[0].get("text") != result.raw_provider_output_json
        or drafts[0].get("state") != "model_context"
        or drafts[0].get("role") != "assistant"
    ):
        raise ValueError(
            "Source writer output differs from exact captured producer bytes"
        )
    request = strict_json(result.writer_request_json)
    fmt = request.get("text", {}).get("format", {})
    if request.get("model") != auth.model or request.get("tools") != []:
        raise ValueError("Source writer request lacks its frozen output schema")
    packet = strict_json(request["input"])
    if packet.get("source_writer_output_policy") != POLICY:
        raise ValueError("Source writer request lacks its frozen output policy")
    validate_writer_format(fmt, packet)
    expected, bindings = reconstruct(
        result.raw_provider_output_json, packet, turn, auth
    )

    # Citation order is not authority; membership, multiplicity and every field are.
    def citation_keys(completion):
        return sorted(
            json.dumps(c.model_dump(mode="json"), sort_keys=True)
            for c in getattr(completion, "source_citations", ())
        )

    actual = result.completion
    if (
        type(actual) is not type(expected)
        or actual.model_dump(exclude={"source_citations"})
        != expected.model_dump(exclude={"source_citations"})
        or citation_keys(actual) != citation_keys(expected)
        or result.build_section_bindings != bindings
    ):
        raise ValueError(
            "Source completion differs from captured typed writer normalization"
        )


def reconstruct(raw_output: str, packet: dict, turn, auth):
    """Select the persisted shape from actual input, never caller preference."""
    from . import types as t

    execution = turn.graph_context_execution
    receipt_sha = turn.graph_context_receipt.context_receipt_sha256
    if "requested_detail_gap_policy" in packet and packet.get("user_question") != turn.user_text:
        raise ValueError("Writer gap question differs from its exact original turn")
    candidate = normalize(raw_output, packet)
    included_ids = set(getattr(auth, "included_source_read_event_ids", ()))
    reads = [
        e
        for e in execution.events
        if isinstance(e, t.ValidatedSourceReadEventV2) and e.event_id in included_ids
    ]
    passages = packet.get("opened_passages", [])
    by_handle = {}
    for p in passages:
        fields = {
            key: p[key]
            for key in (
                "text",
                "source_class",
                "source_artifact_id",
                "source_revision_id",
                "line_start",
                "line_end",
            )
        }
        handle = (
            "p"
            + hashlib.sha256(
                json.dumps(
                    fields, sort_keys=True, ensure_ascii=False, separators=(",", ":")
                ).encode()
            ).hexdigest()[:24]
        )
        if (
            p["handle"] != handle
            or handle in by_handle
            or fields["source_class"] != "opened_source_passage_not_graph_truth"
        ):
            raise ValueError("Invalid frozen passage handle")
        matches = [
            (e.event_id, r)
            for e in reads
            for r in e.receipts
            if r.source_artifact_id == p["source_artifact_id"]
            and r.source_revision_id == p["source_revision_id"]
            and r.line_start == p["line_start"]
            and r.line_end == p["line_end"]
            and r.content_sha256 == hashlib.sha256(p["text"].encode()).hexdigest()
            and r.returned_chars == len(p["text"])
            and r.outcome == "enough"
            and not r.truncated
            and r.evidence_sufficiency_status == "sufficient"
        ]
        if not matches:
            raise ValueError("Frozen passage lacks producing included receipts")
        by_handle[handle] = matches
    section_inclusions = [
        e
        for e in execution.events
        if isinstance(e, t.BuildSectionProviderInclusionV1)
        and e.provider_attempt_id == auth.provider_attempt_id
    ]
    section_ids = (
        set(section_inclusions[0].section_event_ids)
        if len(section_inclusions) == 1
        else set()
    )
    sections = {
        str(e.read_id): e
        for e in execution.events
        if isinstance(e, t.ValidatedBuildSectionReadV1) and e.event_id in section_ids
    }
    from .build_primary_context import validate_packet
    supplied_sections = validate_packet(packet, execution, turn.graph_context_receipt.source_basis)
    expected_sections = sorted(sections.values(), key=lambda e: str(e.event_id))
    if supplied_sections != expected_sections:
        raise ValueError("Writer saved sections differ from producing included reads")
    if packet.get("source_basis") != turn.graph_context_receipt.source_basis.model_dump(
        mode="json", by_alias=True
    ):
        raise ValueError("Writer source basis differs from its frozen receipt")
    segments, citations, bindings = [], [], []
    for index, segment in enumerate(candidate["answer_segments"]):
        segment = dict(segment)
        if segment["kind"] == "source_passage_claim":
            chosen = segment.pop("passage_handles")
            if any(h not in by_handle for h in chosen):
                raise ValueError("Source fact selects an unknown passage handle")
            seen = set()
            for h in chosen:
                for event_id, receipt in by_handle[h]:
                    key = (event_id, receipt.source_read_id)
                    if key in seen:
                        continue
                    seen.add(key)
                    citations.append(
                        t.BuildSourcePassageCitationV1(
                            segment_index=index,
                            text_sha256=hashlib.sha256(
                                segment["text"].encode()
                            ).hexdigest(),
                            provider_attempt_id=auth.provider_attempt_id,
                            envelope_sha256=auth.envelope_sha256,
                            read_event_id=event_id,
                            receipt=receipt,
                        )
                    )
        elif segment["kind"] == "saved_source_claim":
            chosen = segment.pop("section_read_ids")
            if any(rid not in sections for rid in chosen):
                raise ValueError("Saved fact selects an unincluded section")
            bindings.append(
                t.BuildSectionSegmentBindingV1(
                    segment_index=index,
                    text_sha256=hashlib.sha256(segment["text"].encode()).hexdigest(),
                    section_event_ids=sorted(
                        [sections[rid].event_id for rid in chosen], key=str
                    ),
                )
            )
            segment["content_sha256"] = (
                turn.graph_context_receipt.source_basis.content_sha256
            )
        segments.append(segment)
    if not passages or (bindings and not citations):
        status = t.derive_execution_answer_context_status(
            context_receipt_sha256=receipt_sha,
            answer_segments=[
                t.SavedSourceClaimV1.model_validate(s)
                if s["kind"] == "saved_source_claim"
                else t.PlanWorldGraphConnectiveSegmentV1.model_validate(s)
                for s in segments
            ],
            citation_map=None,
            receipt=turn.graph_context_receipt,
            execution=execution,
            producing_provider_attempt_id=auth.provider_attempt_id,
            claim_graph_event_ids={},
        )
        expected = t.BuildGraphCompletionV1(
            context_receipt_sha256=receipt_sha,
            answer_basis="saved_source",
            answer_context_status={
                "plan_only_insufficient_evidence": "source_only_insufficient_evidence",
                "plan_only_graph_unused": "source_only_graph_unused",
            }.get(status, status),
            answer_segments=segments,
            citation_map=None,
        )
        return expected, bindings
    expected = t.BuildGraphCompletionV2(
        context_receipt_sha256=receipt_sha,
        answer_basis="saved_source_and_opened_passages"
        if bindings
        else "opened_source_passages",
        answer_context_status=candidate["answer_context_status"],
        answer_segments=segments,
        source_citations=citations,
    )

    return expected, bindings
