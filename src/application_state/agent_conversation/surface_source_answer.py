"""Shared Plan/Play passage selections over exact producing input and receipts.

No corpus IO or graph admission. A passage claim attributes an authored excerpt;
only the native output owner may accept its actual final provider response.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from uuid import UUID

from . import types as t
from .rules_authority_types import canonical_bytes, canonical_sha256
from .source_writer_output import strict_json

ANSWER_SCHEMA = "dmb_surface_source_answer_v1"

SOURCE_ATTRIBUTION_INSTRUCTIONS = """Keep evidence claim prose about what the evidence says. The host supplies exact
source names and links in citations; do not add source-label headings, parenthetical
source labels, citation links or inferred session-number labels to claim prose. Plan text and dialogue
may mention other sessions; those numbers do not label separately supplied evidence.
Session notes and closing reflections are not an external recap. Describe them as
notes/reflections, preserving their uncertainty and planned versus played events.
review_revision is a review checkpoint selector, never a session number. Do not infer
a session number from a Plan title, nearby prose, dialogue or a revision selector.
External recap passages remain attributed through their owner-provided source names
in host citations. Never borrow another source's title or characterize notes as a recap.
When authored blocks are supplied for Plan/Play content, scene notes or closing
reflections, report those saved materials with authored_excerpt block selections.
The host supplies their literal text and their own attribution. Never paraphrase
session recollections or Plan/Play content as source_passage_claim or graph_claim,
or cite an adventure passage for a played outcome. A suggested next step belongs
in an explicitly hypothetical proposal, separate from the saved recollection.
Ground each factual clause in that claim's own admitted evidence.
Graph claims use their admitted Graph records; source_passage_claim uses its selected
passage_handles; native_source_claim uses its selected section_handles. These are
distinct evidence types, never interchangeable citation permissions.
A citation does not support facts borrowed from neighboring Plan blocks, dialogue,
other passages or your own reconstruction. Before writing a source_passage_claim,
check that its selected passages actually state every factual detail in its text.
A source saying someone asked for a description does not supply that description;
a plan to investigate does not establish what was discovered. Do not turn a request,
belief, possibility or intention into an observed account or completed outcome.
When only authored material supplies a detail, select its authored_excerpt instead
of attributing it to a corpus passage. Put cross-source creative synthesis in an
explicitly hypothetical proposal, while keeping each source claim locally supported.
"""

SOURCE_ANSWER_INSTRUCTIONS = """Only when at least one complete opened source passage has an actual opaque
passage_handle or passageHandle AND no complete Graph claim records are available,
you may answer from those actually opened source passages. This attributes authored source text; it does not
turn it into accepted World facts or played events. Use only complete, sufficient,
untruncated passages carrying passage_handle (or passageHandle in tool results).
Return {"schema":"dmb_surface_source_answer_v1","answer_context_status":"source_grounded or source_grounded_partial",
"answer_segments":[{"kind":"source_passage_claim","text":"source-attributed prose","passage_handles":["exact opaque handle"]}]}.
You may add connective segments for limitations or
proposal segments labeled invented_idea for suggestions. Do not mix graph_claim,
Plan/session/play-context claims or citation metadata into this source-only answer.
A source_grounded answer means these supplied passages support the requested details,
never that the corpus is complete. Use source_grounded_partial for missing details,
conflicts or retrieval gaps; say concretely what remains unknown. Use relevant opened
passages before more reads, and stop when they support the requested answer.
Every source_passage_claim requires at least one exact available handle in passage_handles;
never emit an empty handle list. Saved Plan prose and session notes/reflections are
not opened corpus passages. Without an eligible handle, use the owning Plan/Play
answer contract instead of this schema. Do not output passage handles anywhere
except passage_handles. Do not fabricate them.
"""


INSTRUCTIONS = SOURCE_ATTRIBUTION_INSTRUCTIONS + SOURCE_ANSWER_INSTRUCTIONS


def eligible(read):
    return (
        read.outcome == "enough"
        and read.evidence_sufficiency_status == "sufficient"
        and not read.truncated
        and bool(read.content_sha256)
        and bool(read.source_revision_id)
        and read.returned_chars > 0
    )


def passage_handle(read):
    fields = {
        key: getattr(read, key)
        for key in (
            "anchor_id",
            "evidence_ref_id",
            "source_artifact_id",
            "source_revision_id",
            "content_sha256",
            "line_start",
            "line_end",
            "returned_chars",
        )
    }
    return "p" + canonical_sha256(fields)


@dataclass(frozen=True)
class PassageSupport:
    handle: str
    event_id: UUID
    receipt: t.SourceReadAnchorReceiptV2
    source_name: str


def producing_passages(turn, authorization, request_json):
    """Reconstruct only whole source excerpts present in the exact final envelope."""
    if sha256(request_json.encode()).hexdigest() != authorization.envelope_sha256:
        raise ValueError("Source answer request differs from producing authorization")
    execution = turn.graph_context_execution
    included = set(t.included_passage_event_ids(authorization))
    reads = [
        (event.event_id, read)
        for event in execution.events
        if isinstance(event, t.SOURCE_PASSAGE_EVENTS)
        and event.event_id in included
        for read in event.receipts
        if eligible(read)
    ]
    body = strict_json(request_json)
    rows = []
    partial = False
    if isinstance(authorization, t.PlanJevWriterAuthorizedV1):
        from .plan_jev_graph_packet import frame_in_request

        frame = frame_in_request(request_json)
        if canonical_sha256(frame) != authorization.frame_sha256:
            raise ValueError("Surface source frame differs from admitted input")
        partial = bool(frame.get("retrieval_gaps"))
        for row in frame.get("opened_passages", []):
            rows.append(
                (
                    row.get("passage_handle"),
                    row.get("text"),
                    row.get("source_name"),
                    row.get("line_start"),
                    row.get("line_end"),
                    None,
                )
            )
    else:
        from .native_graph_input import _tool_outputs

        for name in ("read_graph_source", "expand_graph_retrieval"):
            for payload in _tool_outputs(body, tool_name=name):
                if not isinstance(payload, dict):
                    continue
                partial |= bool(payload.get("code")) or payload.get("outcome") in {
                    "partial",
                    "truncated",
                    "unavailable",
                    "denied",
                    "empty",
                }
                if payload.get("schema") == "dmb_graph_evidence_packet_v1":
                    candidates = payload.get("sources", [])
                    partial |= bool(
                        payload.get("coverage", {}).get("sourceReadStopCode")
                    )
                elif name == "read_graph_source":
                    candidates = payload.get("reads", [payload])
                else:
                    candidates = []
                for row in candidates:
                    if not isinstance(row, dict):
                        continue
                    rows.append(
                        (
                            row.get("passageHandle"),
                            row.get("content"),
                            row.get("sourceName"),
                            row.get("lineStart"),
                            row.get("lineEnd"),
                            row.get("anchorId"),
                        )
                    )
    support = set()
    for handle, text, name, start, end, anchor in rows:
        if handle is None:
            continue  # Historical input has no current source-answer capability.
        if (
            not isinstance(text, str)
            or not text
            or not isinstance(name, str)
            or not name.strip()
        ):
            # contentRef bundles do not donate bytes; an included literal donor must.
            continue
        matches = [
            (identity, read)
            for identity, read in reads
            if handle == passage_handle(read)
            and read.line_start == start
            and read.line_end == end
            and (anchor is None or read.anchor_id == anchor)
            and sha256(text.encode()).hexdigest() == read.content_sha256
            and len(text) == read.returned_chars
        ]
        if not matches:
            raise ValueError("Surface passage has no exact included successful read")
        for identity, read in matches:
            support.add((handle, identity, canonical_bytes(read), name))
    result = tuple(
        PassageSupport(
            handle, identity, t.SourceReadAnchorReceiptV2.model_validate_json(raw), name
        )
        for handle, identity, raw, name in sorted(
            support, key=lambda item: (item[0], str(item[1]), item[2], item[3])
        )
    )
    partial |= any(
        not eligible(read)
        for event in execution.events
        if isinstance(event, t.SOURCE_PASSAGE_EVENTS)
        and event.event_id in included
        for read in event.receipts
    )
    return result, partial


def normalize_surface_answer(candidate, turn, producer, support):
    receipt, execution = turn.graph_context_receipt, turn.graph_context_execution
    auth = next(
        event
        for event in execution.events
        if isinstance(event, t.ProviderAttemptAuthorizedEventV3)
        and event.provider_attempt_id == producer
    )
    if (
        support is None
        or support.provider_attempt_id != producer
        or support.envelope_sha256 != auth.envelope_sha256
        or support.context_receipt_sha256 != receipt.context_receipt_sha256
        or support.graph_revision != receipt.graph_authority.graph_revision
        or support.closures
        or auth.included_assertion_ids
        or auth.included_relationship_ids
    ):
        raise ValueError(
            "Source-only output requires its exact producing input without Graph claim authority"
        )
    if not isinstance(candidate, dict) or set(candidate) != {
        "schema",
        "answer_context_status",
        "answer_segments",
    }:
        raise ValueError("Unknown source-only answer fields")
    if candidate["schema"] != ANSWER_SCHEMA or not isinstance(
        candidate["answer_segments"], list
    ):
        raise ValueError("Invalid current source-only answer")
    if candidate["answer_context_status"] not in {
        "source_grounded",
        "source_grounded_partial",
    }:
        raise ValueError("Invalid source-only support status")
    available = {}
    for passage in getattr(support, "passages", ()):
        available.setdefault(passage.handle, []).append(passage)
    segments, citations = [], []
    for index, row in enumerate(candidate["answer_segments"]):
        if not isinstance(row, dict):
            raise ValueError("Invalid source segment")
        if row.get("kind") == "source_passage_claim":
            if set(row) != {"kind", "text", "passage_handles"}:
                raise ValueError("Source selection cannot assert citation metadata")
            handles = row["passage_handles"]
            if (
                not isinstance(handles, list)
                or not handles
                or any(not isinstance(h, str) for h in handles)
                or len(set(handles)) != len(handles)
                or any(h not in available for h in handles)
            ):
                raise ValueError("Unknown, repeated or unexposed source passage handle")
            segments.append({"kind": row["kind"], "text": row["text"]})
            for handle in handles:
                for passage in available[handle]:
                    citations.append(
                        t.SurfaceSourcePassageCitationV1(
                            segment_index=index,
                            text_sha256=sha256(row["text"].encode()).hexdigest(),
                            provider_attempt_id=producer,
                            envelope_sha256=auth.envelope_sha256,
                            read_event_id=passage.event_id,
                            receipt=passage.receipt,
                            source_name=passage.source_name,
                        )
                    )
        elif row.get("kind") in {"connective", "proposal"}:
            segments.append(row)
        else:
            raise ValueError(
                "Source-only answers cannot claim Graph or authored-context authority"
            )
    partial = getattr(support, "source_partial", False)
    if partial:
        segments.append(
            {
                "kind": "connective",
                "text": "Some retrieval was incomplete; these citations support only the passages shown.",
            }
        )
    completion = t.SurfaceSourceCompletionV1(
        surface_id=turn.provenance.surface_id,
        context_receipt_sha256=receipt.context_receipt_sha256,
        answer_context_status="source_grounded_partial"
        if partial
        else candidate["answer_context_status"],
        answer_segments=segments,
        source_citations=citations,
    )
    validate_surface_completion(completion, receipt, execution, producer, {})
    return (
        completion,
        {},
        "\n".join(segment.text for segment in completion.answer_segments),
    )


def validate_surface_completion(
    completion, receipt, execution, producer, graph_bindings
):
    """Durable source-only binding, also rerun on history/repository reconstruction."""
    plan = isinstance(receipt, t.PlanWorldGraphContextReceiptV1) and isinstance(
        execution, t.PlanWorldGraphExecutionV3
    )
    play = isinstance(receipt, t.PlayWorldGraphContextReceiptV1) and isinstance(
        execution, t.PlayWorldGraphExecutionV1
    )
    if (
        not (plan or play)
        or completion.surface_id != ("plan" if plan else "play")
        or graph_bindings
        or completion.context_receipt_sha256 != receipt.context_receipt_sha256
        or execution.context_receipt_sha256 != receipt.context_receipt_sha256
    ):
        raise ValueError(
            "Surface source completion differs from its owning receipt/execution"
        )
    t.validate_selected_source_binding(receipt, execution)
    authorizations = [
        e
        for e in execution.events
        if isinstance(e, t.ProviderAttemptAuthorizedEventV3)
        and e.provider_attempt_id == producer
    ]
    if len(authorizations) != 1:
        raise ValueError("Source completion has no unique producing authorization")
    auth = authorizations[0]
    if auth.included_assertion_ids or auth.included_relationship_ids:
        raise ValueError("Source-only completion cannot consume Graph claim authority")
    responses = [
        e
        for e in execution.events
        if isinstance(e, t.ProviderOutcomeEventV1)
        and e.provider_attempt_id == producer
        and e.outcome == "response_received"
    ]
    if len(responses) != 1 or any(
        not isinstance(e, t.CompletionBindingEventV1)
        for e in execution.events
        if e.sequence > responses[0].sequence
    ):
        raise ValueError(
            "Source completion requires its final acknowledged producer without later acquisition"
        )
    reads = {
        e.event_id: e
        for e in execution.events
        if isinstance(e, t.SOURCE_PASSAGE_EVENTS)
        and e.event_id in t.included_passage_event_ids(auth)
    }
    for citation in completion.source_citations:
        event = reads.get(citation.read_event_id)
        if (
            citation.provider_attempt_id != producer
            or citation.envelope_sha256 != auth.envelope_sha256
            or event is None
            or event.sequence >= auth.sequence
            or citation.receipt not in event.receipts
            or not eligible(citation.receipt)
        ):
            raise ValueError(
                "Source citation differs from its actual producing read inclusion"
            )
    bindings = [
        e for e in execution.events if isinstance(e, t.CompletionBindingEventV1)
    ]
    if bindings and (
        len(bindings) != 1
        or bindings[0].provider_attempt_id != producer
        or bindings[0].completion_sha256 != canonical_sha256(completion)
        or bindings[0].claim_graph_event_ids
    ):
        raise ValueError(
            "Stored source answer differs from its exact completion binding"
        )
