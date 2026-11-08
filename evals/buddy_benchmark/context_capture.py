"""Evaluation-only stop at the real admitted Plan writer-input boundary.

No replacement input producer or response is supplied. The ordinary SDK prepares
its request, APP/Rules authorize it, and GE records known_not_sent on our stop.
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

    if (ready.get("schema") != "dmb_benchmark_context_ready_v1"
            or terminal.get("status") != "captured"
            or type(terminal.get("authorization_calls")) is not int
            or type(terminal.get("writer_io_guard_hits")) is not int
            or terminal.get("authorization_calls") != 1
            or terminal.get("writer_io_guard_hits") != 0
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
    if outcomes != ["known_not_sent"]:
        raise ValueError("Writer lifecycle does not prove known_not_sent")
    accepted = turn.accepted_at
    observed_accepted = datetime.fromisoformat(ready["accepted_at"])
    observed_ready = datetime.fromisoformat(ready["ready_at"])
    elapsed_ms = (observed_ready - accepted).total_seconds() * 1000
    if accepted != observed_accepted or elapsed_ms < 0 or type(ready["ready_monotonic_ns"]) is not int:
        raise ValueError("Context-ready clock correlation differs")
    payload = json.loads(body)
    if (request["provider"], request["model"], request["api_mode"], request["method"], request["url"]) != (
            "openai", authorization.model, "responses", "POST", "https://api.openai.com/v1/responses"):
        raise ValueError("Context request provider identity differs")
    return {"turn": turn, "authorization": authorization, "payload": payload,
            "elapsed_ms": elapsed_ms, "prepared_bytes": len(body)}


class ContextCapture:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.authorization_calls = self.guard_hits = 0
        self.stop_issued = False

    @contextmanager
    def install(self):
        from apps.live_control_server.services.plan_jev_writer import PlanJevWriter

        owner = self
        original_authorize, original_run = PlanJevWriter.authorize, PlanJevWriter.run

        class DenyWriterIO(httpx.AsyncBaseTransport):
            async def handle_async_request(self, request):
                owner.guard_hits += 1
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
            immutable_save(owner.directory, "context-ready", {
                "schema": "dmb_benchmark_context_ready_v1", "world_id": turn.world_id,
                "conversation_id": str(turn.conversation_id), "turn_id": str(turn.turn_id),
                "attempt": turn.attempt, "authorization_event_id": str(event.event_id),
                "provider_attempt_id": str(event.provider_attempt_id),
                "context_receipt_sha256": turn.graph_context_receipt.context_receipt_sha256,
                "frame_sha256": event.frame_sha256, "accepted_at": turn.accepted_at.isoformat(),
                "ready_at": now.isoformat(), "ready_monotonic_ns": tick,
                "host_spans": deepcopy(trace.spans) if trace is not None else None,
            })
            immutable_save(owner.directory, "context-request", {
                "provider": prepared.provider, "model": prepared.model, "api_mode": prepared.api_mode,
                "method": prepared.method, "url": prepared.url, "body_hex": prepared.body.hex(),
                "body_size": prepared.body_size, "body_sha256": prepared.body_sha256,
            })
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
            ready = json.loads((self.directory / "context-ready.json").read_text())
            request = json.loads((self.directory / "context-request.json").read_text())
            validate_context_packet(ready, request, terminal)
        except Exception as exc:
            terminal.update(status="incomplete", error_type=type(exc).__name__)
            immutable_save(self.directory, "context-stop", terminal)
            raise
        immutable_save(self.directory, "context-stop", terminal)

