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

_OBSERVATION = TypeAdapter(ContextTraceObservation)


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
            if self.trace.capture_status == "incomplete":
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
            if self.trace.capture_status == "incomplete":
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
