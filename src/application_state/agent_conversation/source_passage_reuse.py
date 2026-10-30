"""Retained source eligibility; history observations never create read authority."""
from dataclasses import dataclass
from uuid import UUID, uuid4

from . import types as t
from .context_trace import TraceSourcePassage, TraceSourceReuse, TurnContextTraceV1
from .rules_authority_reads import MixedCompletedTurnV1
from .surface_source_answer import eligible


@dataclass(frozen=True)
class RetainedPassage:
    origin: t.Turn
    producer: t.ProviderAttemptAuthorizedEventV3
    read: t.ValidatedSourceReadEventV2
    receipt: t.SourceReadAnchorReceiptV2
    passage: TraceSourcePassage

    def admission(self, sequence: int, elapsed_ms: float, request_id: UUID, request_sha: str, request_revision: int):
        event = t.SourcePassageReuseEventV1(
            kind="source_passage_reused_v1", event_id=uuid4(), sequence=sequence,
            reuse_request_id=request_id, request_sha256=request_sha, request_turn_revision=request_revision,
            origin_turn_id=self.origin.turn_id, origin_attempt=self.origin.attempt,
            origin_read_event_id=self.read.event_id,
            origin_provider_attempt_id=self.producer.provider_attempt_id,
            read_call_id=self.read.read_call_id, receipts=[self.receipt])
        passage = TraceSourceReuse.model_validate({**self.passage.model_dump(mode="python"),
            "kind": "source_passage_reuse", "source_read_event_id": event.event_id, "elapsed_ms": elapsed_ms,
            "origin_turn_id": self.origin.turn_id, "origin_attempt": self.origin.attempt,
            "origin_read_event_id": self.read.event_id,
            "origin_provider_attempt_id": self.producer.provider_attempt_id})
        return event, passage


def eligible_passages(current, previous, payload, requested, max_chars):
    """Yield only original reads included by a completed acknowledged producer.

    Models are reconstructed at the repository boundary. Missing historical trace
    bytes are a miss, never a fabricated read. Current APP mutation fencing is the
    caller's transaction responsibility.
    """
    if isinstance(previous, MixedCompletedTurnV1):
        if previous.base_projection.kind != "approved":
            return ()
        previous = previous.base_projection.turn
    from .plan_source_context import capability_bases
    def graph_basis(turn):
        receipt = turn.graph_context_receipt
        return capability_bases(receipt).graph if isinstance(receipt, (t.PlanSourceContextReceiptV1, t.PlanWorldGraphContextReceiptV1)) else None
    current_graph, previous_graph = graph_basis(current), graph_basis(previous)
    if (previous.status != "completed" or previous.completed_at is None
            or previous.world_id != current.world_id or previous.conversation_id != current.conversation_id
            or previous.sequence >= current.sequence or previous.completion is None
            or previous.graph_context_execution is None or previous.graph_context_receipt is None
            or current.graph_context_receipt is None
            or current_graph is None or previous_graph is None
            or previous_graph.graph_authority != current_graph.graph_authority):
        return ()
    try:
        trace = TurnContextTraceV1.model_validate(payload)
    except (ValueError, TypeError):
        return ()
    if (trace.world_id != current.world_id or trace.conversation_id != current.conversation_id
            or trace.turn_id != previous.turn_id or trace.attempt != previous.attempt
            or trace.capture_status != "complete" or trace.terminal_status != "completed"
            or trace.closed_at is None):
        return ()
    events = previous.graph_context_execution.events
    bindings = [e for e in events if isinstance(e, t.CompletionBindingEventV1)]
    if len(bindings) != 1:
        return ()
    producer = next((e for e in events if isinstance(e, t.ProviderAttemptAuthorizedEventV3)
        and e.provider_attempt_id == bindings[0].provider_attempt_id), None)
    if producer is None or not any(isinstance(e, t.ProviderOutcomeEventV1)
            and e.provider_attempt_id == producer.provider_attempt_id and e.outcome == "response_received"
            and producer.sequence < e.sequence < bindings[0].sequence for e in events):
        return ()
    # A current source completion is sealed to exact producer inclusion by APP.
    # Do not recursively reuse a reuse event or infer support from assistant text.
    reads = [e for e in reversed(events) if isinstance(e, t.ValidatedSourceReadEventV2)
        and e.event_id in producer.included_source_read_event_ids and e.sequence < producer.sequence]
    pins = current.graph_context_execution.effective_source_pins()
    passages = {(p.source_read_event_id, p.source_read_id): p for p in trace.observations
        if type(p) is TraceSourcePassage}
    found = []
    for read in reads:
        for receipt in read.receipts:
            pin = pins.get(receipt.anchor_id)
            passage = passages.get((read.event_id, receipt.source_read_id))
            if (receipt.anchor_id not in requested or pin is None or not eligible(receipt)
                    or receipt.returned_chars > max_chars or passage is None
                    or not isinstance(passage.source_name, str) or not passage.source_name.strip()):
                continue
            if any(getattr(pin, key) != getattr(receipt, key) for key in
                    ("anchor_id", "evidence_ref_id", "source_artifact_id", "source_revision_id")):
                continue
            fields = ("anchor_id", "evidence_ref_id", "source_artifact_id", "source_revision_id",
                      "content_sha256", "line_start", "line_end", "returned_chars", "outcome")
            if (passage.read_call_id != read.read_call_id or passage.world_id != current.world_id
                    or passage.graph_revision != current_graph.graph_authority.graph_revision
                    or any(getattr(passage, key) != getattr(receipt, key) for key in fields)):
                continue
            found.append(RetainedPassage(previous, producer, read, receipt, passage))
    return tuple(found)


def retained_candidates(conn, current, requested, max_chars):
    """One existing-size history page and one batched trace lookup, never N+1."""
    from . import repository as repo
    previous = repo.list_retained_source_turns(conn, current, requested)
    ids = [(p.envelope if isinstance(p, MixedCompletedTurnV1) else p).turn_id for p in previous]
    if not ids:
        return ()
    traces = {(row[0], row[1]): row[2] for row in conn.execute(
        "SELECT turn_id,attempt,payload FROM agent.turn_context_trace WHERE turn_id=ANY(%s)", (ids,)).fetchall()}
    selected = {}
    for prior in reversed(previous):
        envelope = prior.envelope if isinstance(prior, MixedCompletedTurnV1) else prior
        for candidate in eligible_passages(current, prior, traces.get((envelope.turn_id, envelope.attempt)),
                                           requested, max_chars):
            selected.setdefault(candidate.receipt.anchor_id, candidate)
    return tuple(selected[key] for key in sorted(selected))
