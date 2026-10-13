"""Buddy observations bound to APP's current turn claim; never execution authority."""

from __future__ import annotations

from datetime import datetime, timezone
from time import monotonic
from typing import Any, Mapping
from uuid import uuid4

from pydantic import TypeAdapter

from application_state.agent_conversation.context_trace import (
    ContextTraceObservation, TraceSourcePassage,
)
from application_state.errors import ApplicationStateValidationError
from apps.live_control_server.services.agent_context_compaction_report import ContextCompactionReport

_OBSERVATION = TypeAdapter(ContextTraceObservation)
# Exact APP-owned rejection reasons. Identity, fencing, validation and transport
# errors are deliberately not eligible for receipt-only cap fallback.
_SOURCE_CAPTURE_LIMITS = {
    "trace exceeds the explicit 1 MiB per-attempt ceiling": "trace_size_limit",
    "captured source passages exceed the 8-read turn ceiling": "source_read_capture_limit",
    "captured source passages exceed the 96,000 character turn ceiling": "source_character_capture_limit",
}


class ContextTraceCollector:
    """Serialize trace operations with execution appends and lease renewal.

    The caller explicitly enables capture only on a schema-compatible runtime.
    Transport/fencing failures propagate: they cannot authorize tool inclusion.
    A known observation validation failure records incomplete capture instead.
    """

    def __init__(self, fence: Any) -> None:
        self.fence = fence
        self.started = monotonic()
        with fence.renewer._lock:
            turn = fence.renewer._turn
            self.trace = fence.service.start_context_trace(
                world_id=turn.world_id, conversation_id=turn.conversation_id,
                turn_id=turn.turn_id, expected_revision=turn.revision,
                attempt=turn.attempt, trace_id=uuid4(),
                started_at=datetime.now(timezone.utc),
            )

    @property
    def elapsed_ms(self) -> float:
        return (monotonic() - self.started) * 1000

    def _binding(self) -> dict[str, Any]:
        turn = self.fence.renewer._turn
        return dict(world_id=turn.world_id, conversation_id=turn.conversation_id,
                    turn_id=turn.turn_id, expected_revision=turn.revision,
                    attempt=turn.attempt, trace_id=self.trace.trace_id)

    def mark_incomplete(self, code: str) -> None:
        with self.fence.renewer._lock:
            self._mark_incomplete_locked(code)

    def _mark_incomplete_locked(self, code: str) -> None:
        self.trace = self.fence.service.mark_context_trace_incomplete(
            **self._binding(), failure_code=code,
        )

    def observe(self, fields: Mapping[str, Any]) -> None:
        with self.fence.renewer._lock:
            if self._capture_exhausted():
                return
            observation = _OBSERVATION.validate_python({
                **fields, "sequence": len(self.trace.observations),
                "elapsed_ms": self.elapsed_ms,
            })
            try:
                self.trace = self.fence.service.append_context_trace(
                    **self._binding(), observation=observation,
                )
            except ApplicationStateValidationError:
                self._mark_incomplete_locked("trace_observation_rejected")

    def refresh_after_source_capture(self) -> None:
        """Atomic source receipt writes assign observation sequences in APP."""
        with self.fence.renewer._lock:
            attempts = self.fence.service.list_context_trace_attempts(
                world_id=self.trace.world_id, turn_id=self.trace.turn_id,
            )
            matches = [item for item in attempts if item.trace_id == self.trace.trace_id]
            if len(matches) != 1:
                raise ApplicationStateValidationError("current trace capture is unavailable")
            self.trace = matches[0]

    def source_passages(self, event: Any, results: list[Mapping[str, Any]],
                        *, world_id: str, graph_revision: str) -> list[TraceSourcePassage]:
        """Construct exact snapshots for atomic receipt persistence, not append.

        Every successful receipt must match its returned bytes. Failed reads carry
        no snapshot. Sequence is provisional; APP assigns it while holding its row.
        """
        if len(event.receipts) != len(results):
            raise ValueError("source result count differs from validated receipts")
        passages = []
        for receipt, result in zip(event.receipts, results, strict=True):
            text = result.get("content")
            if receipt.returned_chars == 0:
                if text not in (None, ""):
                    raise ValueError("failed source receipt has returned prose")
                continue
            if self._capture_exhausted():
                raise ApplicationStateValidationError("source capture is incomplete")
            passages.append(TraceSourcePassage(
                sequence=0, elapsed_ms=self.elapsed_ms,
                source_read_event_id=event.event_id, read_call_id=event.read_call_id,
                world_id=world_id, graph_revision=graph_revision,
                source_read_id=receipt.source_read_id, anchor_id=receipt.anchor_id,
                evidence_ref_id=receipt.evidence_ref_id,
                source_artifact_id=receipt.source_artifact_id,
                source_revision_id=receipt.source_revision_id,
                line_start=receipt.line_start, line_end=receipt.line_end,
                outcome=receipt.outcome, returned_chars=receipt.returned_chars,
                content_sha256=receipt.content_sha256, text=text,
            ))
        return passages

    def provider_usage(self, calls: list[Mapping[str, Any]]) -> None:
        """Use already-canonical provider telemetry without estimating actuals."""
        for call in calls:
            provider = call.get("provider")
            model = call.get("response_model") or call.get("requested_model")
            if not isinstance(provider, str) or not isinstance(model, str) or not provider or not model:
                self.mark_incomplete("provider_identity_unavailable")
                return
            usage = call.get("usage")
            reported = isinstance(usage, Mapping) and usage.get("status") == "reported"

            def actual(name: str) -> int | None:
                value = usage.get(name) if reported else None
                return value if type(value) is int and value >= 0 else None

            self.observe({
                "kind": "provider_call", "provider": provider, "model": model,
                "outcome": "response_received" if call.get("status") == "ok" else "failed",
                "input_tokens": actual("input_tokens"),
                "output_tokens": actual("output_tokens"),
                "duration_ms": call.get("duration_ms"),
            })

    def persist_source_receipt(self, event: Any, results: list[Mapping[str, Any]],
                               *, world_id: str, graph_revision: str) -> tuple[Any, bool, bool]:
        """Return (updated turn, fresh receipt, captured bytes may be released).

        Only a known capture limit rolls back the atomic passage append and
        permits the SAME receipt to be persisted without passage bytes. The
        read itself is never repeated. Uncertain writes propagate unchanged.
        """
        if not self._capture_exhausted():
            passages = self.source_passages(event, results, world_id=world_id,
                                            graph_revision=graph_revision)
            try:
                updated, fresh = self.fence.append(
                    "record_validated_source_read", "receipt", event, source_passages=passages,
                )
            except ApplicationStateValidationError as exc:
                code = _SOURCE_CAPTURE_LIMITS.get(str(exc))
                if code is None:
                    raise
                self.mark_incomplete(code)
            else:
                self.refresh_after_source_capture()
                return updated, fresh, True
        updated, fresh = self.fence.append("record_validated_source_read", "receipt", event)
        return updated, fresh, False

    def _capture_exhausted(self) -> bool:
        # Missing historical provenance is an incomplete BEFORE view, not a
        # capacity failure or permission to withhold newly captured source reads.
        return (self.trace.capture_status == "incomplete"
                and self.trace.capture_failure_code != "historical_source_unavailable")

    def compaction(self, report: ContextCompactionReport, *, graph_world_id: str) -> None:
        turn = self.fence.turn
        before = [{"item_id": item.item_id, "state": "model_context", "role": item.role,
                   "text": item.text} for item in report.before_visible]
        matches: dict[str, list[dict[str, Any]]] = {item.item_id: [] for item in report.prior_sources}
        before_sequence = turn.sequence
        while matches and before_sequence > 1:
            turns = self.fence.service.list_turns(turn.world_id, turn.conversation_id,
                                                limit=100, before_sequence=before_sequence)
            if not turns:
                break
            for prior in turns:
                for trace in self.fence.service.list_context_trace_attempts(world_id=turn.world_id, turn_id=prior.turn_id):
                    for passage in trace.observations:
                        if not isinstance(passage, TraceSourcePassage):
                            continue
                        for candidate in report.prior_sources:
                            if (passage.anchor_id == candidate.anchor_id
                                    and passage.content_sha256 == candidate.content_sha256
                                    and passage.returned_chars == candidate.returned_chars
                                    and (candidate.evidence_ref_id is None or passage.evidence_ref_id == candidate.evidence_ref_id)
                                    and (candidate.source_artifact_id is None or passage.source_artifact_id == candidate.source_artifact_id)):
                                matches[candidate.item_id].append({
                                    "schema": "dmb_trace_historical_source_ref_v1", "world_id": trace.world_id,
                                    "conversation_id": trace.conversation_id, "turn_id": trace.turn_id,
                                    "attempt": trace.attempt, "trace_id": trace.trace_id,
                                    "source_read_event_id": passage.source_read_event_id,
                                    "source_read_id": passage.source_read_id,
                                    "content_sha256": candidate.content_sha256,
                                })
            before_sequence = min(item.sequence for item in turns)
        missing = False
        for candidate in report.prior_sources:
            references = matches[candidate.item_id]
            if len(references) != 1:
                missing = True
                continue
            before.append({"item_id": candidate.item_id, "state": "model_context", "role": "source",
                           "historical_source_reads": references})
        self.observe({"kind": "context_snapshot", "stage": "before", "materials": before})
        after = [{"item_id": item.item_id, "state": "model_context", "role": item.role,
                  "text": item.text} for item in report.after_visible]
        for kind in ("nodes", "sources"):
            for index, route in enumerate(report.routes.get(kind, [])):
                if route.get("world_id") not in {turn.world_id, graph_world_id}:
                    missing = True
                    continue
                handle = {key: value for key, value in route.items() if key not in {"label", "kind"}}
                # APP World identity is canonical; the observed revision/anchor
                # remain unchanged. These handles are not newly admitted reads.
                handle["world_id"] = turn.world_id
                handle["route_id"] = f"{kind}:{index}"
                after.append({"item_id": f"route:{kind}:{index}", "state": "retrieval_route",
                              "role": "source" if kind == "sources" else "fact", "route": handle})
        self.observe({"kind": "context_snapshot", "stage": "after", "materials": after})
        for decision in report.decisions:
            self.observe({"kind": "context_decision", "action": decision.action,
                          "item_ids": [decision.item_id], "reason_code": decision.reason_code,
                          "policy_version": report.policy_version})
        if missing:
            self.observe({"kind": "failure", "code": "historical_source_unavailable", "phase": "context_build"})
            self.mark_incomplete("historical_source_unavailable")
