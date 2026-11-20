"""Evaluation-only stop at the real admitted Plan writer-input boundary.

No replacement input producer or response is supplied. The ordinary SDK prepares
its request and APP/Rules authorize it. The default stops before dispatch.
The opt-in mode instead terminates in a local sink below the dispatch gate.
"""
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from time import monotonic_ns
from unittest.mock import patch

import httpx

from .artifacts import immutable_save


class ContextReadyStop(BaseException):
    """Do not translate an intentional pre-IO stop into a retryable SDK error."""


class WriterIODenied(BaseException):
    """The intended boundary was missed; context capture must fail closed."""


def validate_context_packet(ready, request, terminal):
    """Join exact prepared bytes to the final, normally interrupted APP turn."""
    from application_state.agent_conversation import types as t
    from application_state.agent_conversation.native_execution import NativeWriterAuthorizedV1

    sink = terminal.get("transport_sink")
    expected_hits = 1 if sink is not None else 0
    if (ready.get("schema") != "dmb_benchmark_context_ready_v1"
            or terminal.get("status") != "captured"
            or type(terminal.get("authorization_calls")) is not int
            or type(terminal.get("writer_io_guard_hits")) is not int
            or terminal.get("authorization_calls") != 1
            or terminal.get("writer_io_guard_hits") != expected_hits
            or terminal.get("stop_issued") is not True):
        raise ValueError("Context stop or zero-writer-IO proof is incomplete")
    body = bytes.fromhex(request["body_hex"])
    if len(body) != request["body_size"] or sha256(body).hexdigest() != request["body_sha256"]:
        raise ValueError("Prepared context bytes changed")
    turn = t.Turn.model_validate_json(json.dumps(terminal["turn"]))
    execution = turn.graph_context_execution
    if (turn.status != "interrupted" or turn.claim_expires_at is not None
            or turn.completion is not None or turn.assistant_text is not None
            or (str(turn.turn_id), str(turn.conversation_id), turn.world_id, turn.attempt)
            != (ready["turn_id"], ready["conversation_id"], ready["world_id"], ready["attempt"])):
        raise ValueError("Context capture did not retain its interrupted, response-free turn")
    events = [event for event in execution.events
              if isinstance(event, NativeWriterAuthorizedV1)]
    if len(events) != 1:
        raise ValueError("Context capture requires one durable native writer authorization")
    authorization = events[0]
    if (str(authorization.event_id) != ready["authorization_event_id"]
            or str(authorization.provider_attempt_id) != ready["provider_attempt_id"]
            or authorization.envelope_sha256 != request["body_sha256"]
            or authorization.frame_sha256 != ready["frame_sha256"]
            or execution.context_receipt_sha256 != ready["context_receipt_sha256"]):
        raise ValueError("Prepared context differs from its durable authorization")
    outcomes = [event.outcome for event in execution.events
                if isinstance(event, t.ProviderOutcomeEventV1)
                and event.provider_attempt_id == authorization.provider_attempt_id]
    expected_outcomes = ["sdk_entered", "outcome_unknown"] if sink is not None else ["known_not_sent"]
    if outcomes != expected_outcomes:
        raise ValueError("Writer lifecycle differs from the captured boundary")
    accepted = turn.accepted_at
    observed_accepted = datetime.fromisoformat(ready["accepted_at"])
    observed_ready = datetime.fromisoformat(ready["ready_at"])
    elapsed_ms = (observed_ready - accepted).total_seconds() * 1000
    if accepted != observed_accepted or elapsed_ms < 0 or type(ready["ready_monotonic_ns"]) is not int:
        raise ValueError("Context-ready clock correlation differs")
    payload = json.loads(body)
    request_started = ready.get("request_started_monotonic_ns")
    request_to_ready_ms = None
    if request_started is not None:
        if type(request_started) is not int or not 0 < request_started <= ready["ready_monotonic_ns"]:
            raise ValueError("Context request-start clock correlation differs")
        request_to_ready_ms = (ready["ready_monotonic_ns"] - request_started) / 1_000_000
    if (request["provider"], request["model"], request["api_mode"], request["method"], request["url"]) != (
            "openai", authorization.model, "responses", "POST", "https://api.openai.com/v1/responses"):
        raise ValueError("Context request provider identity differs")
    request_to_transport_ms = None
    if sink is not None:
        if not isinstance(sink, dict):
            raise ValueError("Writer transport receipt must be an object")
        sink_tick = sink.get("monotonic_ns")
        if (type(sink_tick) is not int or sink_tick < ready["ready_monotonic_ns"]
                or (sink.get("method"), sink.get("url"), sink.get("body_hex"))
                != (request["method"], request["url"], request["body_hex"])):
            raise ValueError("Writer transport bytes or clock differs from authorization")
        if request_started is not None:
            request_to_transport_ms = (sink_tick - request_started) / 1_000_000
    return {"turn": turn, "authorization": authorization, "payload": payload,
            "elapsed_ms": elapsed_ms, "request_to_ready_ms": request_to_ready_ms,
            "request_to_transport_ms": request_to_transport_ms, "prepared_bytes": len(body)}


class ContextCapture:
    def __init__(self, directory, *, writer_transport=False):
        self.directory = Path(directory)
        self.writer_transport = writer_transport
        self.transport_sink = None
        self.ready = self.request = None
        self.authorization_calls = self.guard_hits = 0
        self.stop_issued = False
        self.request_started_monotonic_ns = None

    @contextmanager
    def install(self):
        from apps.live_control_server.services.plan_jev_writer import PlanJevWriter

        owner = self
        original_authorize, original_run = PlanJevWriter.authorize, PlanJevWriter.run

        class DenyWriterIO(httpx.AsyncBaseTransport):
            async def handle_async_request(self, request):
                owner.guard_hits += 1
                if owner.writer_transport and owner.guard_hits == 1 and owner.request is not None:
                    tick = monotonic_ns()
                    owner.transport_sink = {"monotonic_ns": tick, "method": request.method,
                                            "url": str(request.url), "body_hex": request.content.hex()}
                    owner.stop_issued = True
                    raise ContextReadyStop("Writer captured at the local transport sink")
                raise WriterIODenied("Writing-provider IO is disabled in context capture")

        guard = DenyWriterIO()

        def authorize(writer, prepared):
            owner.authorization_calls += 1
            if owner.authorization_calls != 1 or not writer.shared:
                raise ContextReadyStop("Context capture requires one shared native Plan writer")
            if original_authorize(writer, prepared) is not True:
                return False
            # Original authorization has populated writer.record's lifecycle
            # state and completed APP, Rules and exact prompt-witness admission.
            now, tick = datetime.now(timezone.utc), monotonic_ns()
            turn, event = writer.adapter.turn, writer.authorization
            if writer.prepared is not prepared:
                raise ContextReadyStop("Writer lifecycle has not retained its prepared context")
            if turn.graph_context_receipt.work_context.surface_id != "plan":
                raise ContextReadyStop("Context capture requires the ordinary Plan owner")
            trace = getattr(writer.adapter, "trace", None)
            owner.ready = {
                "schema": "dmb_benchmark_context_ready_v1", "world_id": turn.world_id,
                "conversation_id": str(turn.conversation_id), "turn_id": str(turn.turn_id),
                "attempt": turn.attempt, "authorization_event_id": str(event.event_id),
                "provider_attempt_id": str(event.provider_attempt_id),
                "context_receipt_sha256": turn.graph_context_receipt.context_receipt_sha256,
                "frame_sha256": event.frame_sha256, "accepted_at": turn.accepted_at.isoformat(),
                "ready_at": now.isoformat(), "ready_monotonic_ns": tick,
                "request_started_monotonic_ns": owner.request_started_monotonic_ns,
                "host_spans": deepcopy(trace.spans) if trace is not None else None,
            }
            owner.request = {
                "provider": prepared.provider, "model": prepared.model, "api_mode": prepared.api_mode,
                "method": prepared.method, "url": prepared.url, "body_hex": prepared.body.hex(),
                "body_size": prepared.body_size, "body_sha256": prepared.body_sha256,
            }
            if owner.writer_transport:
                return True
            owner.stop_issued = True
            raise ContextReadyStop("Admitted context captured; no response requested")

        async def run(writer, *, transport=None, api_key=None):
            # Below GE's real prepared-request gate, not responses.create: the
            # actual SDK bytes and ordinary authorization must still be built.
            return await original_run(writer, transport=guard, api_key=api_key)

        with patch.object(PlanJevWriter, "authorize", authorize), patch.object(PlanJevWriter, "run", run):
            yield self

    def finalize(self, turn):
        terminal = {"status": "captured", "authorization_calls": self.authorization_calls,
                    "writer_io_guard_hits": self.guard_hits, "stop_issued": self.stop_issued,
                    "turn": turn.model_dump(mode="json", by_alias=True)}
        try:
            if self.writer_transport:
                if self.transport_sink is None:
                    raise ValueError("Writer transport sink was not reached")
                terminal["transport_sink"] = self.transport_sink
            for name, value in (("context-ready", self.ready), ("context-request", self.request)):
                if value is not None:
                    immutable_save(self.directory, name, value)
            ready = json.loads((self.directory / "context-ready.json").read_text())
            request = json.loads((self.directory / "context-request.json").read_text())
            validate_context_packet(ready, request, terminal)
        except Exception as exc:
            terminal.update(status="incomplete", error_type=type(exc).__name__)
            immutable_save(self.directory, "context-stop", terminal)
            raise
        immutable_save(self.directory, "context-stop", terminal)

