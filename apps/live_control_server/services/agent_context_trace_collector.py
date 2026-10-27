"""Buddy observations bound to APP's current turn claim; never execution authority."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from time import monotonic
from typing import Any, Mapping
from uuid import uuid4

from pydantic import TypeAdapter, ValidationError

from application_state.agent_conversation.context_trace import (
    ContextTraceObservation, TraceSourcePassage, MAX_CONTEXT_TRACE_BYTES,
    CONTEXT_TRACE_TERMINAL_RESERVE_BYTES,
)
from application_state.errors import ApplicationStateValidationError
from apps.live_control_server.services.agent_context_compaction_report import ContextCompactionReport
from apps.live_control_server.services.agent_conversation_context import ROUTE_MARKER

_OBSERVATION = TypeAdapter(ContextTraceObservation)
# Exact APP-owned rejection reasons. Identity, fencing, validation and transport
# errors are deliberately not eligible for receipt-only cap fallback.
_SOURCE_CAPTURE_LIMITS = {
    "trace exceeds the explicit 1 MiB per-attempt ceiling": "trace_size_limit",
    "captured source passages exceed the 96,000 character turn ceiling": "source_character_capture_limit",
}


def _source_capture_limit(exc: ApplicationStateValidationError) -> str | None:
    direct = _SOURCE_CAPTURE_LIMITS.get(str(exc))
    if direct is not None:
        return direct
    cause = exc.__cause__
    if isinstance(cause, ValidationError) and cause.title == "TurnContextTraceV1":
        errors = cause.errors(include_input=False, include_url=False)
        if len(errors) == 1 and errors[0].get("loc") == () and errors[0].get("type") == "value_error":
            owned = errors[0].get("ctx", {}).get("error")
            if isinstance(owned, ValueError):
                return _SOURCE_CAPTURE_LIMITS.get(str(owned))
    return None


class ContextTraceCollector:
    """Serialize trace operations with execution appends and lease renewal.

    The caller explicitly enables capture only on a schema-compatible runtime.
    Transport/fencing failures propagate: they cannot authorize tool inclusion.
    A known observation validation failure records incomplete capture instead.
    """

    def __init__(self, fence: Any) -> None:
        self.fence = fence
        self.current_provider_materials: list[dict[str, Any]] = []
        self.started = monotonic()
        self.provider_attempts_by_request: dict[str, Any] = {}
        self.ambiguous_provider_requests: set[str] = set()
        with fence.renewer._lock:
            turn = fence.renewer._turn
            self.bound_context_receipt_sha256 = getattr(getattr(turn, "graph_context_receipt", None),
                                                       "context_receipt_sha256", None)
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
        # APP preserves the first durable marker. Later gaps must not ask it
        # to replace that marker, and capacity exhaustion is independent of it.
        if code not in {"historical_source_unavailable", "recap_context_capture_unavailable"}:
            self.capture_capacity_exhausted = True
        if self.trace.capture_status != "incomplete":
            self.trace = self.fence.service.mark_context_trace_incomplete(
                **self._binding(), failure_code=code,
            )
        elif self.trace.capture_failure_code != code:
            observation = _OBSERVATION.validate_python({
                "kind": "failure", "phase": "trace_capture", "code": code,
                "sequence": len(self.trace.observations), "elapsed_ms": self.elapsed_ms,
            })
            try:
                self.trace = self.fence.service.append_context_trace(
                    **self._binding(), observation=observation,
                )
            except ApplicationStateValidationError:
                # The first durable gap survives even when no more trace fits.
                self.capture_capacity_exhausted = True

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

    def authored_reference(self, event: Any) -> None:
        """Observe only after its APP append; never create read/provider authority."""
        self.observe({'kind': 'authored_graph_reference_v1',
                      'execution_event': event.model_dump(mode='json', by_alias=True)})

    def capture_prompt(self, view: Mapping[str, Any], authorization: Any) -> None:
        """Commit an exact request reference or refuse dispatch; never best effort."""
        from .agent_prompt_evidence import store_prompt
        with self.fence.renewer._lock:
            evidence_id = store_prompt(view["payloadJson"], digest=view["payloadSha256"], size=view["payloadUtf8Bytes"])
            observation = _OBSERVATION.validate_python({
                "kind": "prompt_reference", "sequence": len(self.trace.observations),
                "elapsed_ms": self.elapsed_ms, "evidence_id": evidence_id,
                "provider_attempt_id": authorization.provider_attempt_id,
                "provider": authorization.provider, "model": authorization.model,
                "api_mode": authorization.api_mode, "serializer_version": authorization.serializer_version,
                "payload_sha256": view["payloadSha256"], "payload_utf8_bytes": view["payloadUtf8Bytes"],
            })
            self.trace = self.fence.service.append_context_trace(**self._binding(), observation=observation)
            if observation not in self.trace.observations:
                raise ApplicationStateValidationError("prompt reference was not durably captured")

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
                source_name=result.get("sourceName") if isinstance(result.get("sourceName"), str) and result["sourceName"].strip() else None,
                source_revision_id=receipt.source_revision_id,
                line_start=receipt.line_start, line_end=receipt.line_end,
                outcome=receipt.outcome, returned_chars=receipt.returned_chars,
                content_sha256=receipt.content_sha256, text=text,
            ))
        return passages

    def bind_provider_request(self, request_id: Any, provider_attempt_id: Any) -> None:
        """Correlate acknowledged SDK entry, never infer a join from call order."""
        if not isinstance(request_id, str) or not request_id.strip():
            return
        with self.fence.renewer._lock:
            if request_id in self.ambiguous_provider_requests:
                return
            previous = self.provider_attempts_by_request.get(request_id)
            if previous is not None and previous != provider_attempt_id:
                self.provider_attempts_by_request.pop(request_id)
                self.ambiguous_provider_requests.add(request_id)
                return
            self.provider_attempts_by_request[request_id] = provider_attempt_id

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

            request_id = call.get("runtime_api_request_id")
            attempt_id = self.provider_attempts_by_request.get(request_id) if isinstance(request_id, str) else None
            self.observe({
                "kind": "provider_call", "provider": provider, "model": model,
                "provider_attempt_id": attempt_id,
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
                code = _source_capture_limit(exc)
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
        return (getattr(self, "capture_capacity_exhausted", False) or
                self.trace.capture_status == "incomplete"
                and self.trace.capture_failure_code not in {
                    "historical_source_unavailable", "recap_context_capture_unavailable",
                })

    def provider_context(self, question: str, source_events: list[Any], *, body: Mapping[str, Any] | None = None, historical_sources=()) -> None:
        """Observe source material proven included by the parent envelope gate.

        Routes and old answers do not establish passage presence. Only the
        included validated reads refer to exact current or protected earlier captures.
        The complete provider prompt/Plan body is deliberately not recorded.
        """
        materials = [{"item_id": "current-question", "state": "model_context",
                      "role": "user", "text": question}]
        visible: list[tuple[str, str]] = []
        for item in (body or {}).get("input", []):
            if not isinstance(item, Mapping) or item.get("role") not in {"user", "assistant"}:
                continue
            content = item.get("content")
            if isinstance(content, str):
                visible.append((item["role"], content))
            elif isinstance(content, list):
                visible.extend((item["role"], part["text"]) for part in content
                               if isinstance(part, Mapping) and part.get("type") in {"input_text", "output_text"}
                               and isinstance(part.get("text"), str))
        for material in getattr(self, "compacted_materials", []):
            identity = (material["role"], material.get("text"))
            if material["state"] == "model_context" and identity in visible:
                visible.remove(identity)
                materials.append({**material, "item_id": f"retained:{material['item_id']}"})
        report = getattr(self, "compacted_report", None)
        if report is not None:
            import json
            routes_text = ROUTE_MARKER + json.dumps(report.routes, ensure_ascii=False, separators=(",", ":"))
            if ("user", routes_text) in visible:
                materials.extend(item for item in self.compacted_materials if item["state"] == "retrieval_route")
        for event in source_events:
            refs, prior_refs = [], []
            for receipt in event.receipts:
                if receipt.returned_chars == 0:
                    continue
                matches = [passage for passage in self.trace.observations
                           if isinstance(passage, TraceSourcePassage)
                           and passage.source_read_event_id == event.event_id
                           and passage.source_read_id == receipt.source_read_id
                           and passage.content_sha256 == receipt.content_sha256]
                if not matches:
                    from application_state.agent_conversation.context_trace import TraceHistoricalSourceReferenceV1
                    prior = [TraceHistoricalSourceReferenceV1.model_validate(ref) for ref in historical_sources
                        if str(ref.get('source_read_event_id')) == str(event.event_id)
                        and ref.get('source_read_id') == receipt.source_read_id
                        and ref.get('content_sha256') == receipt.content_sha256]
                    if (len(prior)!=1 or prior[0].world_id != self.trace.world_id
                        or prior[0].conversation_id != self.trace.conversation_id or prior[0].turn_id != self.trace.turn_id
                        or prior[0].attempt >= self.trace.attempt):
                        raise ApplicationStateValidationError("included source has no exact captured passage")
                    prior_refs.append(prior[0].model_dump(mode='json',by_alias=True))
                elif len(matches)==1:
                    refs.append({"source_read_id": receipt.source_read_id,
                                 "content_sha256": receipt.content_sha256})
                else:
                    raise ApplicationStateValidationError("included source has ambiguous captured passages")
            if refs and prior_refs:
                raise ApplicationStateValidationError("one source event cannot mix physical capture owners")
            if prior_refs:
                materials.append({"item_id":f"source:{event.event_id}","state":"model_context",
                    "role":"source","historical_source_reads":prior_refs})
            if refs:
                materials.append({"item_id": f"source:{event.event_id}", "state": "model_context",
                                  "role": "source", "source_read_event_id": event.event_id,
                                  "source_reads": refs})
        self.observe({"kind": "context_snapshot", "stage": "before", "snapshot_kind": "provider_input", "materials": materials})
        self.current_provider_materials = materials

    def answer_draft(self, answer: str, *, producing_provider_attempt_id: Any) -> None:
        """Retain exact unvalidated writer output, preserving historical item identity."""
        self._provider_output(answer, producing_provider_attempt_id=producing_provider_attempt_id)

    def controller_decision_response(self, response_json: str, *, producing_provider_attempt_id: Any) -> None:
        """Retain exact normalized SDK response for APP's selection proof check."""
        self._provider_output(response_json, producing_provider_attempt_id=producing_provider_attempt_id,
                              controller_response=True)

    def _provider_output(self, answer: str, *, producing_provider_attempt_id: Any, controller_response: bool = False) -> None:
        """Retain exact unvalidated output; it never supplies answer authority."""
        with self.fence.renewer._lock:
            turn = self.fence.renewer._turn
            execution = turn.graph_context_execution
            authorizations = [event for event in execution.events if event.kind in {
                "provider_attempt_authorized", "provider_attempt_authorized_v2",
                "provider_attempt_authorized_v3", "provider_attempt_authorized_v4", "plan_jev_provider_authorized_v1", "plan_requested_work_authorized_v1", "plan_requested_work_authorized_v2", "plan_jev_writer_authorized_v1", "plan_jev_writer_authorized_v2"}]
            if (not authorizations or authorizations[-1].provider_attempt_id != producing_provider_attempt_id
                or not any(event.kind == "provider_outcome" and event.provider_attempt_id == producing_provider_attempt_id
                    and event.outcome == "response_received" for event in execution.events)):
                raise ApplicationStateValidationError("answer draft lacks its producing provider response")
            if controller_response:
                from application_state.agent_conversation.types import BuildSelectedSourceActionControllerWriterPolicyV1
                if (not isinstance(execution.policy, BuildSelectedSourceActionControllerWriterPolicyV1)
                    or (authorizations[-1].provider, authorizations[-1].model, authorizations[-1].api_mode)
                    != execution.policy.provider_roles.controller.identity()):
                    raise ApplicationStateValidationError("controller capture lacks its frozen selection role")
            receipt_sha = turn.graph_context_receipt.context_receipt_sha256
            if (receipt_sha != self.bound_context_receipt_sha256 or self.trace.world_id != turn.world_id
                or self.trace.turn_id != turn.turn_id or self.trace.conversation_id != turn.conversation_id):
                raise ApplicationStateValidationError("answer draft differs from its frozen trace context")
            prefix = "unvalidated-controller-decision" if controller_response else "unvalidated-provider-answer"
            item_id = f"{prefix}:{producing_provider_attempt_id}:{receipt_sha}"
            prior = [material for observation in self.trace.observations
                if observation.kind == "context_snapshot" for material in observation.materials
                if material.item_id == item_id]
            if prior:
                if len(prior) != 1 or prior[0].text != answer:
                    raise ApplicationStateValidationError("answer draft identity already has different bytes")
                return
            if self._capture_exhausted():
                return
            try:
                answer.encode("utf-8")
            except UnicodeEncodeError:
                self._mark_incomplete_locked("answer_draft_encoding_unavailable")
                return
            if len(self.trace.observations) >= 2048:
                self._mark_incomplete_locked("answer_draft_event_limit")
                return
            observation = _OBSERVATION.validate_python({
                "kind": "context_snapshot", "stage": "after", "snapshot_kind": "provider_response",
                "sequence": len(self.trace.observations), "elapsed_ms": self.elapsed_ms,
                "materials": [{"item_id": item_id, "state": "model_context",
                    "role": "assistant", "text": answer}],
            })
            candidate = self.trace.model_copy(update={"observations": [*self.trace.observations, observation]})
            encoded = json.dumps(candidate.model_dump(mode="json", by_alias=True),
                                 ensure_ascii=True, sort_keys=True, allow_nan=False).encode("utf-8")
            reserve = (CONTEXT_TRACE_TERMINAL_RESERVE_BYTES if self.trace.capture_status == "recording"
                       else CONTEXT_TRACE_TERMINAL_RESERVE_BYTES // 2)
            if len(encoded) > MAX_CONTEXT_TRACE_BYTES - reserve:
                self._mark_incomplete_locked("answer_draft_size_limit")
                return
            # Identity/fencing/transport failures propagate; unlike a known
            # observation cap they must never be mistaken for successful capture.
            self.trace = self.fence.service.append_context_trace(**self._binding(), observation=observation)

    def answer_context(self, answer: str) -> None:
        """Record the validated visible answer and producing request's material."""
        materials = [*getattr(self, "current_provider_materials", []),
                     {"item_id": "validated-answer", "state": "model_context",
                      "role": "assistant", "text": answer}]
        self.observe({"kind": "context_snapshot", "stage": "after", "snapshot_kind": "validated_answer", "materials": materials})

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
                            if candidate.retrieval_session_id is not None:
                                events = getattr(getattr(prior, "graph_context_execution", None), "events", [])
                                if not any(getattr(event, "kind", None) == "source_read_authorized_v2"
                                           and event.read_call_id == passage.read_call_id
                                           and event.retrieval_session_id == candidate.retrieval_session_id for event in events):
                                    continue
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
        comparison_id = uuid4()
        self.observe({"kind": "context_snapshot", "stage": "before", "snapshot_kind": "compaction_input",
                      "comparison_id": comparison_id, "materials": before})
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
        self.observe({"kind": "context_snapshot", "stage": "after", "snapshot_kind": "compaction_output",
                      "comparison_id": comparison_id, "materials": after})
        self.compacted_report = report
        self.compacted_materials = after
        for decision in report.decisions:
            self.observe({"kind": "context_decision", "action": decision.action,
                          "item_ids": [decision.item_id], "reason_code": decision.reason_code,
                          "policy_version": report.policy_version})
        if missing:
            self.observe({"kind": "failure", "code": "historical_source_unavailable", "phase": "context_build"})
            self.mark_incomplete("historical_source_unavailable")
