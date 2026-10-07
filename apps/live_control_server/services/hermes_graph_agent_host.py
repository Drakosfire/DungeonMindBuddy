"""Process-isolated host for Rung 3 Hermes graph-agent turns (PR010B Rung 4 / PR353).

FastAPI must not call :func:`run_hermes_graph_agent_turn` in-process. This host
owns a reusable ``spawn`` worker that imports and executes Rung 3 only inside
the child process, communicating through bounded JSON wire bytes.
"""

from __future__ import annotations

import multiprocessing as mp
import hashlib
import os
import re
import shutil
import sys
import tempfile
import threading
import time
import uuid
from datetime import UTC, datetime
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from multiprocessing.context import BaseContext
from multiprocessing.process import BaseProcess
from multiprocessing.queues import Queue
from pathlib import Path
from typing import Any, Literal

from apps.live_control_server.services.hermes_graph_agent_contract import (
    MAX_MODEL_CALLS,
    PROCESS_ISOLATION_MODE,
    HermesGraphAgentTurnRequest,
    HermesGraphAgentTurnResult,
    decode_json_wire,
    deserialize_hermes_graph_agent_turn_request,
    deserialize_hermes_graph_agent_turn_result,
    encode_json_wire,
    serialize_hermes_graph_agent_turn_request,
    serialize_hermes_graph_agent_turn_result,
    serialize_model_call,
)
from apps.live_control_server.config import session_dir
from apps.live_control_server.services.hermes_session_store import (
    STRUCTURED_PROFILE_ROOT_NAME,
)

HostErrorCode = Literal[
    "hermes_worker_lost",
    "hermes_worker_timeout",
    "hermes_worker_start_failed",
    "hermes_worker_protocol_error",
]

DEFAULT_TURN_TIMEOUT_S = 120.0
DEFAULT_ACCEPT_TIMEOUT_S = 15.0
DEFAULT_READY_TIMEOUT_S = 30.0
DEFAULT_SHUTDOWN_TIMEOUT_S = 5.0
_WORKER_HOME_ENV = "DMB_HERMES_GRAPH_AGENT_WORKER_HOME"
_SESSION_PROFILES_ENV = "DMB_HERMES_GRAPH_AGENT_SESSION_PROFILES_ROOT"
_WORKER_HOME_PREFIX = "dmb-hermes-graph-worker-home-"
_LOGGING_DRAINED_MARKER = ".dmb-hermes-logging-drained"
_MAX_WORKER_PHASES = 8
_WORKER_PHASE_NAMES = frozenset(
    {
        "rung3_bootstrap_logger_home_setup",
        "rung3_cached_agent_factory_lookup",
        "rung3_plugin_discovery",
        "rung3_agent_construction",
        "rung3_provider_conversation",
        "rung3_response_normalization_projection",
    }
)
_WORKER_PHASE_ID_RE = re.compile(r"(?P<group>[0-9a-f]{32}):(?P<sequence>[1-9][0-9]?)\Z")
_WORKER_PHASE_GROUP_RE = re.compile(r"[0-9a-f]{32}\Z")


def _sanitize_worker_phase(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, Mapping):
        return None
    span_id = value.get("span_id")
    name = value.get("name")
    status = value.get("status")
    duration_ms = value.get("duration_ms")
    started_at = value.get("started_at")
    completed_at = value.get("completed_at")
    attributes = value.get("attributes")
    if (
        not isinstance(span_id, str)
        or len(span_id) > 35
        or not isinstance(name, str)
        or name not in _WORKER_PHASE_NAMES
        or not isinstance(status, str)
        or status not in {"ok", "error"}
        or isinstance(duration_ms, bool)
        or not isinstance(duration_ms, int)
        or not 0 <= duration_ms <= 120_000
        or not isinstance(started_at, str)
        or not isinstance(completed_at, str)
        or len(started_at) > 40
        or len(completed_at) > 40
        or not isinstance(attributes, Mapping)
    ):
        return None
    group_id = attributes.get("host_phase_group_id")
    id_match = _WORKER_PHASE_ID_RE.fullmatch(span_id)
    if (
        not isinstance(group_id, str)
        or _WORKER_PHASE_GROUP_RE.fullmatch(group_id) is None
        or id_match is None
        or id_match.group("group") != group_id
        or int(id_match.group("sequence")) > _MAX_WORKER_PHASES
    ):
        return None
    try:
        started = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
        completed = datetime.fromisoformat(completed_at.replace("Z", "+00:00"))
    except ValueError:
        return None
    if started.tzinfo is None or completed.tzinfo is None:
        return None
    elapsed_ms = (completed - started).total_seconds() * 1000
    if elapsed_ms < 0 or abs(elapsed_ms - duration_ms) > 2:
        return None
    return {
        "span_id": span_id,
        "parent_span_id": None,
        "kind": "phase",
        "name": name,
        "status": status,
        "started_at": started_at,
        "completed_at": completed_at,
        "duration_ms": duration_ms,
        "attributes": {"host_phase_group_id": group_id},
    }


def _run_worker_in_private_hermes_home(
    worker_target: Callable[..., Any],
    request_queue: Queue[bytes],
    response_queue: Queue[bytes],
    hermes_home: str,
    session_profiles_root: str,
) -> None:
    """Give one worker a stable logger home and stop its queue before exit."""
    os.environ["HERMES_HOME"] = hermes_home
    os.environ[_WORKER_HOME_ENV] = hermes_home
    os.environ[_SESSION_PROFILES_ENV] = session_profiles_root
    try:
        worker_target(request_queue, response_queue)
    finally:
        # Hermes 0.18.2 registers its own atexit drain, but the host owns the
        # home lifetime. Drain and stop synchronously so the parent can safely
        # remove the directory after this process exits.
        hermes_logging = sys.modules.get("hermes_logging")
        if hermes_logging is not None:
            flush = getattr(hermes_logging, "flush_log_queue", None)
            stop = getattr(hermes_logging, "_stop_queue_listener", None)
            if callable(flush):
                flush()
            if callable(stop):
                stop()
        stderr_flush = getattr(sys.stderr, "flush", None)
        if callable(stderr_flush):
            stderr_flush()
        (Path(hermes_home) / _LOGGING_DRAINED_MARKER).touch(exist_ok=True)


_HOST_LOCK = threading.RLock()
_GLOBAL_HOST: HermesGraphAgentHost | None = None


def _host_error_result(
    *,
    error_code: HostErrorCode,
    error_message: str,
    hermes_session_id: str | None = None,
    model_calls: list[dict[str, Any]] | None = None,
    telemetry_warnings: list[str] | None = None,
) -> HermesGraphAgentTurnResult:
    return HermesGraphAgentTurnResult(
        status="error",
        final_response=None,
        messages=[],
        hermes_session_id=hermes_session_id or "",
        tool_events=[],
        error_code=error_code,
        error_message=error_message,
        process_isolation=PROCESS_ISOLATION_MODE,
        model_calls=list(model_calls or []),
        telemetry_warnings=list(telemetry_warnings or []),
    )


def _ingest_streamed_telemetry(
    message: Mapping[str, Any],
    *,
    request_id: str | None,
    telemetry_calls: list[dict[str, Any]] | None,
    telemetry_warnings: list[str] | None,
    telemetry_worker_phases: list[dict[str, Any]] | None = None,
) -> None:
    if telemetry_calls is None and telemetry_worker_phases is None:
        return
    if request_id is not None and str(message.get("requestId") or "") != request_id:
        return
    payload = message.get("payload")
    if not isinstance(payload, Mapping):
        if (
            telemetry_warnings is not None
            and "observer_payload_malformed" not in telemetry_warnings
        ):
            telemetry_warnings.append("observer_payload_malformed")
        return

    raw_calls = payload.get("modelCalls") or []
    if not isinstance(raw_calls, list):
        if (
            telemetry_warnings is not None
            and "observer_payload_malformed" not in telemetry_warnings
        ):
            telemetry_warnings.append("observer_payload_malformed")
        raw_calls = []
    for item in raw_calls:
        if telemetry_calls is None:
            break
        if len(telemetry_calls) >= MAX_MODEL_CALLS:
            if (
                telemetry_warnings is not None
                and "model_calls_truncated" not in telemetry_warnings
            ):
                telemetry_warnings.append("model_calls_truncated")
            break
        if not isinstance(item, Mapping):
            if (
                telemetry_warnings is not None
                and "observer_payload_malformed" not in telemetry_warnings
            ):
                telemetry_warnings.append("observer_payload_malformed")
            continue
        try:
            telemetry_calls.append(serialize_model_call(item))
        except Exception:
            if (
                telemetry_warnings is not None
                and "observer_payload_malformed" not in telemetry_warnings
            ):
                telemetry_warnings.append("observer_payload_malformed")

    raw_phases = payload.get("workerPhases", [])
    if not isinstance(raw_phases, list):
        if (
            telemetry_warnings is not None
            and "worker_phases_malformed" not in telemetry_warnings
        ):
            telemetry_warnings.append("worker_phases_malformed")
        return
    if telemetry_worker_phases is None:
        return
    for item in raw_phases:
        if len(telemetry_worker_phases) >= _MAX_WORKER_PHASES:
            break
        phase = _sanitize_worker_phase(item)
        if phase is None:
            if (
                telemetry_warnings is not None
                and "worker_phases_malformed" not in telemetry_warnings
            ):
                telemetry_warnings.append("worker_phases_malformed")
            continue
        telemetry_worker_phases.append(phase)


def _drain_streamed_telemetry(
    response_queue: Queue[bytes],
    *,
    request_id: str | None,
    telemetry_calls: list[dict[str, Any]] | None,
    telemetry_warnings: list[str] | None,
    telemetry_worker_phases: list[dict[str, Any]] | None = None,
) -> None:
    if telemetry_calls is None and telemetry_worker_phases is None:
        return
    while True:
        try:
            raw = response_queue.get_nowait()
        except Exception:
            return
        try:
            message = decode_json_wire(raw)
        except Exception:
            continue
        if message.get("type") == "telemetry":
            _ingest_streamed_telemetry(
                message,
                request_id=request_id,
                telemetry_calls=telemetry_calls,
                telemetry_worker_phases=telemetry_worker_phases,
                telemetry_warnings=telemetry_warnings,
            )


def _await_worker_proceed(
    request_queue: Queue[bytes],
    *,
    request_id: str,
) -> str:
    """Block until proceed for ``request_id`` or shutdown. Returns the type."""
    while True:
        raw = request_queue.get()
        try:
            message = decode_json_wire(raw)
        except Exception:
            continue
        msg_type = message.get("type")
        if msg_type == "shutdown":
            return "shutdown"
        if msg_type == "proceed" and str(message.get("requestId") or "") == request_id:
            return "proceed"


def hermes_graph_agent_worker_main(
    request_queue: Queue[bytes],
    response_queue: Queue[bytes],
) -> None:
    """Default worker entry: import and execute Rung 3 only in the child.

    Acceptance is a two-phase barrier: the worker emits ``accepted``, then waits
    for an explicit parent ``proceed`` before calling Rung 3. That keeps retries
    safe when ``accepted`` is lost — Rung 3 never starts without authorization.
    """
    from apps.live_control_server.services.hermes_graph_agent import (
        run_hermes_graph_agent_turn,
    )

    response_queue.put(
        encode_json_wire(
            {
                "type": "ready",
                "pid": os.getpid(),
            }
        )
    )
    while True:
        raw = request_queue.get()
        try:
            message = decode_json_wire(raw)
        except Exception:
            response_queue.put(
                encode_json_wire(
                    {
                        "type": "protocol_error",
                        "errorCode": "hermes_worker_protocol_error",
                        "errorMessage": "Worker received non-JSON command bytes.",
                    }
                )
            )
            continue
        msg_type = message.get("type")
        if msg_type == "shutdown":
            response_queue.put(
                encode_json_wire({"type": "shutdown_ack", "pid": os.getpid()})
            )
            return
        if msg_type == "proceed":
            # Orphan proceed (no matching wait) — ignore.
            continue
        if msg_type != "execute":
            response_queue.put(
                encode_json_wire(
                    {
                        "type": "protocol_error",
                        "errorCode": "hermes_worker_protocol_error",
                        "errorMessage": f"Unknown worker command type: {msg_type!r}",
                    }
                )
            )
            continue

        request_id = str(message.get("requestId") or "")
        response_queue.put(
            encode_json_wire(
                {
                    "type": "accepted",
                    "requestId": request_id,
                    "pid": os.getpid(),
                }
            )
        )
        authorization = _await_worker_proceed(request_queue, request_id=request_id)
        if authorization == "shutdown":
            response_queue.put(
                encode_json_wire({"type": "shutdown_ack", "pid": os.getpid()})
            )
            return
        try:
            payload = message.get("payload")
            if not isinstance(payload, Mapping):
                raise ValueError("execute payload must be a mapping")
            request = deserialize_hermes_graph_agent_turn_request(payload)

            def on_model_call(call: Mapping[str, Any]) -> None:
                try:
                    serialized = serialize_model_call(call)
                    response_queue.put(
                        encode_json_wire(
                            {
                                "type": "telemetry",
                                "requestId": request_id,
                                "pid": os.getpid(),
                                "payload": {"modelCalls": [serialized]},
                            }
                        )
                    )
                except Exception:
                    return

            def on_worker_phase(phase: Mapping[str, Any]) -> None:
                try:
                    safe_phase = _sanitize_worker_phase(phase)
                    if safe_phase is None:
                        return
                    response_queue.put(
                        encode_json_wire(
                            {
                                "type": "telemetry",
                                "requestId": request_id,
                                "pid": os.getpid(),
                                "payload": {"workerPhases": [safe_phase]},
                            }
                        )
                    )
                except Exception:
                    return

            authorization_sequence = 0

            def report_provider_lifecycle(event: Any) -> bool:
                if not request.provider_authorization_required:
                    return True
                if not isinstance(event, Mapping):
                    return False
                sequence = event.get("authorizationSequence")
                transition = event.get("transition")
                if (
                    isinstance(sequence, bool)
                    or not isinstance(sequence, int)
                    or sequence != authorization_sequence
                    or transition not in {"sdk_entered", "response_received", "outcome_unknown"}
                ):
                    return False
                try:
                    response_queue.put(encode_json_wire({
                        "type": "provider_lifecycle_request",
                        "requestId": request_id,
                        "authorizationId": f"{request_id}:{sequence}",
                        "transition": transition,
                    }))
                    message = decode_json_wire(request_queue.get(timeout=30.0))
                except Exception:
                    return False
                return (
                    message.get("type") == "provider_lifecycle_response"
                    and message.get("requestId") == request_id
                    and message.get("authorizationId") == f"{request_id}:{sequence}"
                    and message.get("acknowledged") is True
                )

            def authorize_provider_request(view: Any) -> bool:
                nonlocal authorization_sequence
                if not request.provider_authorization_required:
                    return True
                authorization_sequence += 1
                authorization_id = f"{request_id}:{authorization_sequence}"
                try:
                    response_queue.put(encode_json_wire({
                        "type": "provider_authorization_request",
                        "requestId": request_id,
                        "authorizationId": authorization_id,
                        "view": {
                            "provider": view.provider,
                            "model": view.model,
                            "apiMode": view.api_mode,
                            "baseUrl": view.base_url,
                            "payloadJson": view.payload_json,
                            "payloadSha256": view.payload_sha256,
                            "payloadUtf8Bytes": view.payload_utf8_bytes,
                        },
                    }))
                    message = decode_json_wire(request_queue.get(timeout=30.0))
                except Exception:
                    return False
                return (
                    message.get("type") == "provider_authorization_response"
                    and message.get("requestId") == request_id
                    and message.get("authorizationId") == authorization_id
                    and message.get("allowOnce") is True
                )

            graph_operation_sequence = 0

            def broker_graph_operation(
                tool_name: str, arguments: Mapping[str, Any]
            ) -> tuple[str, Mapping[str, Any] | None]:
                nonlocal graph_operation_sequence
                if not request.parent_graph_broker_required:
                    return (
                        '{"schema":"dmb_world_graph_retrieval_error_v1",'
                        '"code":"parent_graph_broker_unavailable",'
                        '"message":"Parent Graph broker is unavailable.",'
                        '"statusCode":503,"diagnostics":[]}',
                        None,
                    )
                graph_operation_sequence += 1
                operation_id = f"{request_id}:g{graph_operation_sequence}"
                if tool_name not in {"expand_graph_retrieval", "read_graph_source"}:
                    return (
                        '{"schema":"dmb_world_graph_retrieval_error_v1",'
                        '"code":"plan_graph_tool_not_permitted",'
                        '"message":"Only parent Graph interactions are permitted.",'
                        '"statusCode":403,"diagnostics":[]}',
                        None,
                    )
                try:
                    response_queue.put(encode_json_wire({
                        "type": "graph_operation_request",
                        "requestId": request_id,
                        "operationId": operation_id,
                        "toolName": tool_name,
                        "arguments": dict(arguments),
                    }))
                    message = decode_json_wire(request_queue.get(timeout=30.0))
                except Exception:
                    return (
                        '{"schema":"dmb_world_graph_retrieval_error_v1",'
                        '"code":"parent_graph_broker_unavailable",'
                        '"message":"Parent Graph broker did not respond.",'
                        '"statusCode":503,"diagnostics":[]}',
                        None,
                    )
                if (
                    message.get("type") != "graph_operation_response"
                    or message.get("requestId") != request_id
                    or message.get("operationId") != operation_id
                    or not isinstance(message.get("resultJson"), str)
                    or (
                        message.get("retrievalSession") is not None
                        and not isinstance(message.get("retrievalSession"), Mapping)
                    )
                ):
                    return (
                        '{"schema":"dmb_world_graph_retrieval_error_v1",'
                        '"code":"parent_graph_broker_protocol_error",'
                        '"message":"Parent Graph broker response was invalid.",'
                        '"statusCode":502,"diagnostics":[]}',
                        None,
                    )
                session_packet = message.get("retrievalSession")
                return message["resultJson"], session_packet

            result = run_hermes_graph_agent_turn(
                request,
                on_model_call=on_model_call,
                on_worker_phase=on_worker_phase,
                on_provider_authorization=authorize_provider_request,
                on_provider_lifecycle=report_provider_lifecycle,
                on_parent_graph_operation=broker_graph_operation,
            )
            response_queue.put(
                encode_json_wire(
                    {
                        "type": "result",
                        "requestId": request_id,
                        "pid": os.getpid(),
                        "payload": serialize_hermes_graph_agent_turn_result(result),
                    }
                )
            )
        except Exception as exc:
            response_queue.put(
                encode_json_wire(
                    {
                        "type": "result",
                        "requestId": request_id,
                        "pid": os.getpid(),
                        "payload": serialize_hermes_graph_agent_turn_result(
                            _host_error_result(
                                error_code="hermes_worker_protocol_error",
                                error_message=(
                                    "Hermes worker failed while executing a turn: "
                                    f"{type(exc).__name__}"
                                ),
                            )
                        ),
                    }
                )
            )


@dataclass(frozen=True, slots=True)
class _WorkerHandles:
    process: BaseProcess
    request_queue: Queue[bytes]
    response_queue: Queue[bytes]
    pid: int
    hermes_home: Path


class HermesGraphAgentHost:
    """Serialize Rung 3 turns through one reusable process-isolated worker."""

    def __init__(
        self,
        *,
        turn_timeout_s: float = DEFAULT_TURN_TIMEOUT_S,
        accept_timeout_s: float = DEFAULT_ACCEPT_TIMEOUT_S,
        ready_timeout_s: float = DEFAULT_READY_TIMEOUT_S,
        worker_target: Callable[..., Any] | None = None,
        context: BaseContext | None = None,
        session_profiles_root: Path | None = None,
    ) -> None:
        self._turn_timeout_s = float(turn_timeout_s)
        self._accept_timeout_s = float(accept_timeout_s)
        self._ready_timeout_s = float(ready_timeout_s)
        self._worker_target = worker_target or hermes_graph_agent_worker_main
        self._ctx = context or mp.get_context("spawn")
        self._session_profiles_root = (
            (
                session_profiles_root
                if session_profiles_root is not None
                else session_dir() / STRUCTURED_PROFILE_ROOT_NAME
            )
            .expanduser()
            .resolve()
        )
        # Serializes start() and execute() so only one thread consumes the
        # worker response queue at a time (ready vs accepted cannot cross-steal).
        self._turn_gate = threading.Lock()
        self._worker_lock = threading.RLock()
        self._worker: _WorkerHandles | None = None
        self._worker_ready = False
        self._started = False
        self._closed = False

    @property
    def start_method(self) -> str:
        return self._ctx.get_start_method()

    @property
    def worker_pid(self) -> int | None:
        with self._worker_lock:
            if self._worker is None:
                return None
            return self._worker.pid

    def start(self) -> None:
        """Ensure the host may create a worker (idempotent)."""
        with self._turn_gate:
            with self._worker_lock:
                self._closed = False
                self._started = True
                if self._worker is not None and not self._worker.process.is_alive():
                    self._stop_worker_locked(deadline=time.monotonic() + 1.0)
                if (
                    self._worker is not None
                    and self._worker.process.is_alive()
                    and self._worker_ready
                ):
                    return
            self._spawn_worker()

    def shutdown(self, *, timeout_s: float = DEFAULT_SHUTDOWN_TIMEOUT_S) -> bool:
        """Stop the worker within one total deadline.

        Returns True when no live worker remains tracked. If the process survives
        the deadline, the handle is retained and this returns False.
        """
        deadline = time.monotonic() + float(timeout_s)
        with self._worker_lock:
            self._closed = True
            self._started = False
            return self._stop_worker_locked(deadline=deadline)

    def execute(
        self,
        request: HermesGraphAgentTurnRequest,
        *,
        timeout_s: float | None = None,
        on_host_phase: Callable[[dict[str, Any]], None] | None = None,
        on_provider_authorization: Callable[[Mapping[str, Any]], bool] | None = None,
        on_provider_lifecycle: Callable[[Mapping[str, Any]], bool] | None = None,
        on_graph_operation: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
    ) -> HermesGraphAgentTurnResult:
        """Run one turn on the worker. Concurrent callers queue on the turn gate."""
        turn_timeout = self._turn_timeout_s if timeout_s is None else float(timeout_s)
        phase_group_id = uuid.uuid4().hex
        phase_count = 0

        def emit_phase(name: str, started: float, status: str = "ok") -> None:
            nonlocal phase_count
            if on_host_phase is None or phase_count >= 24:
                return
            phase_count += 1
            duration_ms = max(0, round((time.monotonic() - started) * 1000))
            completed_at = datetime.now(UTC)
            span = {
                "span_id": f"{phase_group_id}:{phase_count}",
                "parent_span_id": None,
                "kind": "phase",
                "name": name,
                "status": status,
                "started_at": datetime.fromtimestamp(
                    completed_at.timestamp() - duration_ms / 1000, UTC
                ).isoformat(),
                "completed_at": completed_at.isoformat(),
                "duration_ms": duration_ms,
                "attributes": {"host_phase_group_id": phase_group_id},
            }
            try:
                on_host_phase(span)
            except Exception:
                # Observability must never change turn behavior.
                pass

        def emit_worker_phase(span: dict[str, Any]) -> None:
            nonlocal phase_count
            if on_host_phase is None or phase_count >= 24:
                return
            phase_count += 1
            try:
                on_host_phase(span)
            except Exception:
                pass

        started = time.monotonic()
        try:
            wire_payload = serialize_hermes_graph_agent_turn_request(request)
        except Exception:
            emit_phase("host_request_serialize", started, "error")
            return _host_error_result(
                error_code="hermes_worker_protocol_error",
                error_message="Hermes graph-agent request could not be serialized.",
            )
        emit_phase("host_request_serialize", started)
        gate_started = time.monotonic()
        with self._turn_gate:
            emit_phase("host_turn_gate_wait", gate_started)
            return self._execute_turn(
                wire_payload,
                turn_timeout_s=turn_timeout,
                emit_phase=emit_phase,
                emit_worker_phase=emit_worker_phase,
                on_provider_authorization=on_provider_authorization,
                on_provider_lifecycle=on_provider_lifecycle,
                on_graph_operation=on_graph_operation,
            )

    def _execute_turn(
        self,
        wire_payload: dict[str, Any],
        *,
        turn_timeout_s: float,
        emit_phase: Callable[[str, float, str], None],
        emit_worker_phase: Callable[[dict[str, Any]], None],
        on_provider_authorization: Callable[[Mapping[str, Any]], bool] | None,
        on_provider_lifecycle: Callable[[Mapping[str, Any]], bool] | None,
        on_graph_operation: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None,
    ) -> HermesGraphAgentTurnResult:
        self._started = True
        # Retry only covers pre-enqueue / start failures. After enqueue, two-phase
        # proceed keeps Rung 3 unstarted until accept is observed; a lost accept
        # kills the worker (no proceed) and may retry once safely.
        for attempt in (1, 2):
            phase_started = time.monotonic()
            try:
                worker = self._acquire_worker_for_turn()
            except Exception:
                emit_phase("host_worker_acquire_ready", phase_started, "error")
                if attempt == 1:
                    with self._worker_lock:
                        self._stop_worker_locked(deadline=time.monotonic() + 1.0)
                    continue
                return _host_error_result(
                    error_code="hermes_worker_start_failed",
                    error_message="Hermes graph-agent worker failed to start.",
                )
            emit_phase("host_worker_acquire_ready", phase_started, "ok")

            request_id = str(uuid.uuid4())
            message = {
                "type": "execute",
                "requestId": request_id,
                "payload": wire_payload,
            }
            phase_started = time.monotonic()
            try:
                wire_bytes = encode_json_wire(message)
            except Exception:
                emit_phase("host_request_wire_encode", phase_started, "error")
                return _host_error_result(
                    error_code="hermes_worker_protocol_error",
                    error_message="Hermes graph-agent request wire encoding failed.",
                )
            emit_phase("host_request_wire_encode", phase_started, "ok")

            with self._worker_lock:
                if self._closed or self._worker is not worker or not self._worker_ready:
                    if attempt == 1:
                        continue
                    return _host_error_result(
                        error_code="hermes_worker_start_failed",
                        error_message=(
                            "Hermes graph-agent host is shut down and cannot start a worker."
                        ),
                    )
                phase_started = time.monotonic()
                try:
                    worker.request_queue.put(wire_bytes)
                except Exception:
                    self._stop_worker_if_current_locked(
                        worker, deadline=time.monotonic() + 1.0
                    )
                    if attempt == 1:
                        continue
                    return _host_error_result(
                        error_code="hermes_worker_lost",
                        error_message="Hermes graph-agent worker was lost before accept.",
                    )
                emit_phase("host_request_queue_put", phase_started, "ok")
                local_worker = worker

            phase_started = time.monotonic()
            accepted = self._recv_until(
                local_worker.response_queue,
                local_worker.process,
                expected_types={"accepted"},
                request_id=request_id,
                timeout_s=self._accept_timeout_s,
            )
            emit_phase(
                "host_accept_wait",
                phase_started,
                "ok"
                if accepted is not None and accepted.get("type") == "accepted"
                else "error",
            )
            if accepted is None or accepted.get("type") != "accepted":
                # No proceed was sent, so two-phase workers cannot have started
                # Rung 3. Discard and optionally retry once.
                with self._worker_lock:
                    self._stop_worker_if_current_locked(
                        local_worker, deadline=time.monotonic() + 1.0
                    )
                if attempt == 1:
                    continue
                return _host_error_result(
                    error_code="hermes_worker_lost",
                    error_message="Hermes graph-agent worker did not accept the request.",
                )

            # Acceptance observed — authorize execution. No further automatic retry.
            streamed_calls: list[dict[str, Any]] = []
            streamed_worker_phases: list[dict[str, Any]] = []
            streamed_warnings: list[str] = []
            authorization_sequence = 0
            graph_operation_sequence = 0

            def handle_provider_authorization(message: dict[str, Any]) -> None:
                nonlocal authorization_sequence
                authorization_id = message.get("authorizationId")
                view = message.get("view")
                expected_id = f"{request_id}:{authorization_sequence + 1}"
                allow = False
                valid_view = False
                if (
                    authorization_id == expected_id
                    and isinstance(view, Mapping)
                    and set(view) == {
                        "provider", "model", "apiMode", "baseUrl",
                        "payloadJson", "payloadSha256", "payloadUtf8Bytes",
                    }
                ):
                    raw_json = view.get("payloadJson")
                    raw_digest = view.get("payloadSha256")
                    raw_size = view.get("payloadUtf8Bytes")
                    valid_view = (
                        all(isinstance(view.get(key), str) and view[key].strip()
                            for key in ("provider", "model", "apiMode"))
                        and (view.get("baseUrl") is None or isinstance(view.get("baseUrl"), str))
                        and isinstance(raw_json, str)
                        and len(raw_json.encode("utf-8")) <= 256_000
                        and isinstance(raw_digest, str)
                        and re.fullmatch(r"[0-9a-f]{64}", raw_digest) is not None
                        and isinstance(raw_size, int)
                        and not isinstance(raw_size, bool)
                        and raw_size == len(raw_json.encode("utf-8"))
                        and hashlib.sha256(raw_json.encode("utf-8")).hexdigest() == raw_digest
                    )
                if valid_view:
                    authorization_sequence += 1
                    try:
                        allow = bool(
                            on_provider_authorization is not None
                            and on_provider_authorization(view) is True
                        )
                    except Exception:
                        allow = False
                try:
                    local_worker.request_queue.put(
                        encode_json_wire({
                            "type": "provider_authorization_response",
                            "requestId": request_id,
                            "authorizationId": authorization_id,
                            "allowOnce": allow,
                        })
                    )
                except Exception:
                    allow = False

            def handle_graph_operation(message: dict[str, Any]) -> None:
                nonlocal graph_operation_sequence
                operation_id = message.get("operationId")
                tool_name = message.get("toolName")
                arguments = message.get("arguments")
                expected_id = f"{request_id}:g{graph_operation_sequence + 1}"
                result: Mapping[str, Any] = {
                    "resultJson": (
                        '{"schema":"dmb_world_graph_retrieval_error_v1",'
                        '"code":"parent_graph_broker_unavailable",'
                        '"message":"Parent Graph broker is unavailable.",'
                        '"statusCode":503,"diagnostics":[]}'
                    ),
                    "retrievalSession": None,
                }
                if (
                    operation_id == expected_id
                    and tool_name in {"expand_graph_retrieval", "read_graph_source"}
                    and isinstance(arguments, Mapping)
                    and on_graph_operation is not None
                ):
                    graph_operation_sequence += 1
                    try:
                        candidate = on_graph_operation(message)
                        if (
                            isinstance(candidate, Mapping)
                            and isinstance(candidate.get("resultJson"), str)
                            and (
                                candidate.get("retrievalSession") is None
                                or isinstance(candidate.get("retrievalSession"), Mapping)
                            )
                        ):
                            result = candidate
                    except Exception:
                        pass
                try:
                    local_worker.request_queue.put(encode_json_wire({
                        "type": "graph_operation_response",
                        "requestId": request_id,
                        "operationId": operation_id,
                        "resultJson": result["resultJson"],
                        "retrievalSession": result.get("retrievalSession"),
                    }))
                except Exception:
                    return

            def handle_provider_lifecycle(message: dict[str, Any]) -> None:
                authorization_id = message.get("authorizationId")
                transition = message.get("transition")
                acknowledged = False
                if (
                    authorization_id == f"{request_id}:{authorization_sequence}"
                    and transition in {"sdk_entered", "response_received", "outcome_unknown"}
                ):
                    try:
                        acknowledged = bool(
                            on_provider_lifecycle is not None
                            and on_provider_lifecycle({
                                "authorizationId": authorization_id,
                                "transition": transition,
                            }) is True
                        )
                    except Exception:
                        acknowledged = False
                try:
                    local_worker.request_queue.put(encode_json_wire({
                        "type": "provider_lifecycle_response",
                        "requestId": request_id,
                        "authorizationId": authorization_id,
                        "acknowledged": acknowledged,
                    }))
                except Exception:
                    return

            phase_started = time.monotonic()
            try:
                local_worker.request_queue.put(
                    encode_json_wire({"type": "proceed", "requestId": request_id})
                )
            except Exception:
                with self._worker_lock:
                    self._stop_worker_if_current_locked(
                        local_worker, deadline=time.monotonic() + 1.0
                    )
                return _host_error_result(
                    error_code="hermes_worker_lost",
                    error_message=(
                        "Hermes graph-agent worker was lost after accepting the request."
                    ),
                )
            emit_phase("host_proceed_queue_put", phase_started, "ok")

            phase_started = time.monotonic()
            result_message = self._recv_until(
                local_worker.response_queue,
                local_worker.process,
                expected_types={"result"},
                request_id=request_id,
                timeout_s=turn_timeout_s,
                telemetry_calls=streamed_calls,
                telemetry_warnings=streamed_warnings,
                telemetry_worker_phases=streamed_worker_phases,
                on_provider_authorization=handle_provider_authorization,
                on_provider_lifecycle=handle_provider_lifecycle,
                on_graph_operation=handle_graph_operation,
            )
            emit_phase(
                "host_worker_result_wait",
                phase_started,
                "ok"
                if result_message is not None and result_message.get("type") == "result"
                else "error",
            )
            for span in streamed_worker_phases:
                emit_worker_phase(span)
            if result_message is None:
                alive = local_worker.process.is_alive()
                with self._worker_lock:
                    self._stop_worker_if_current_locked(
                        local_worker, deadline=time.monotonic() + 1.0
                    )
                if alive:
                    return _host_error_result(
                        error_code="hermes_worker_timeout",
                        error_message=(
                            "Hermes graph-agent worker exceeded the turn timeout."
                        ),
                        model_calls=streamed_calls,
                        telemetry_warnings=streamed_warnings,
                    )
                return _host_error_result(
                    error_code="hermes_worker_lost",
                    error_message=(
                        "Hermes graph-agent worker was lost after accepting the request."
                    ),
                    model_calls=streamed_calls,
                    telemetry_warnings=streamed_warnings,
                )
            payload = result_message.get("payload")
            if not isinstance(payload, Mapping):
                with self._worker_lock:
                    self._stop_worker_if_current_locked(
                        local_worker, deadline=time.monotonic() + 1.0
                    )
                return _host_error_result(
                    error_code="hermes_worker_protocol_error",
                    error_message="Hermes worker result payload was malformed.",
                    model_calls=streamed_calls,
                    telemetry_warnings=streamed_warnings,
                )
            try:
                phase_started = time.monotonic()
                result = deserialize_hermes_graph_agent_turn_result(payload)
                emit_phase("host_result_decode", phase_started, "ok")
                return result
            except Exception:
                emit_phase(
                    "host_result_decode",
                    locals().get("phase_started", time.monotonic()),
                    "error",
                )
                with self._worker_lock:
                    self._stop_worker_if_current_locked(
                        local_worker, deadline=time.monotonic() + 1.0
                    )
                return _host_error_result(
                    error_code="hermes_worker_protocol_error",
                    error_message="Hermes worker result could not be deserialized.",
                    model_calls=streamed_calls,
                    telemetry_warnings=streamed_warnings,
                )

        return _host_error_result(
            error_code="hermes_worker_start_failed",
            error_message="Hermes graph-agent worker failed before accept.",
        )

    def _acquire_worker_for_turn(self) -> _WorkerHandles:
        with self._worker_lock:
            if self._closed:
                raise RuntimeError("Hermes host is shut down")
            if (
                self._worker is not None
                and self._worker.process.is_alive()
                and self._worker_ready
            ):
                return self._worker
            if not self._stop_worker_locked(deadline=time.monotonic() + 1.0):
                raise RuntimeError(
                    "Hermes worker still alive; refusing to spawn replacement"
                )
        return self._spawn_worker()

    def _spawn_worker(self) -> _WorkerHandles:
        """Start a worker and wait for ready without holding the lifecycle lock."""
        with self._worker_lock:
            if self._closed:
                raise RuntimeError("Hermes host is shut down")
            if (
                self._worker is not None
                and self._worker.process.is_alive()
                and self._worker_ready
            ):
                return self._worker
            if not self._stop_worker_locked(deadline=time.monotonic() + 1.0):
                raise RuntimeError(
                    "Hermes worker still alive; refusing to spawn replacement"
                )
            request_queue: Queue[bytes] = self._ctx.Queue()
            response_queue: Queue[bytes] = self._ctx.Queue()
            hermes_home = Path(tempfile.mkdtemp(prefix=_WORKER_HOME_PREFIX))
            process = self._ctx.Process(
                target=_run_worker_in_private_hermes_home,
                args=(
                    self._worker_target,
                    request_queue,
                    response_queue,
                    str(hermes_home),
                    str(self._session_profiles_root),
                ),
                name="dmb-hermes-graph-agent-worker",
                daemon=True,
            )
            try:
                process.start()
            except BaseException:
                shutil.rmtree(hermes_home, ignore_errors=True)
                try:
                    request_queue.close()
                except Exception:
                    pass
                try:
                    response_queue.close()
                except Exception:
                    pass
                raise
            provisional = _WorkerHandles(
                process=process,
                request_queue=request_queue,
                response_queue=response_queue,
                pid=int(process.pid or 0),
                hermes_home=hermes_home,
            )
            self._worker = provisional
            self._worker_ready = False
            local = provisional
            ready_timeout = self._ready_timeout_s

        # Only the turn-gate holder may consume this queue during ready wait.
        ready = self._recv_until(
            local.response_queue,
            local.process,
            expected_types={"ready"},
            request_id=None,
            timeout_s=ready_timeout,
        )

        with self._worker_lock:
            if self._worker is not local:
                self._discard_handles(local, deadline=time.monotonic() + 1.0)
                raise RuntimeError("Hermes worker spawn aborted")
            if self._closed:
                if not self._stop_worker_locked(deadline=time.monotonic() + 1.0):
                    raise RuntimeError(
                        "Hermes worker spawn aborted by shutdown; prior worker still alive"
                    )
                raise RuntimeError("Hermes worker spawn aborted by shutdown")
            if ready is None or ready.get("type") != "ready":
                if not self._stop_worker_locked(deadline=time.monotonic() + 1.0):
                    raise RuntimeError(
                        "Hermes worker did not become ready and remains alive"
                    )
                raise RuntimeError("Hermes worker did not become ready")
            self._worker_ready = True
            return local

    def _stop_worker_if_current_locked(
        self,
        local_worker: _WorkerHandles,
        *,
        deadline: float,
    ) -> bool:
        if self._worker is local_worker:
            return self._stop_worker_locked(deadline=deadline)
        return True

    def _stop_worker_locked(self, *, deadline: float) -> bool:
        """Stop the current worker. Return True only when confirmed dead/absent."""
        worker = self._worker
        if worker is None:
            self._worker_ready = False
            return True
        stopped = self._discard_handles(worker, deadline=deadline)
        if stopped:
            self._worker = None
            self._worker_ready = False
            return True
        # Process still alive after the deadline — retain the handle so we do
        # not orphan a live worker from host tracking, and refuse replacement.
        return False

    def _discard_handles(self, worker: _WorkerHandles, *, deadline: float) -> bool:
        """Attempt graceful → SIGTERM → SIGKILL within ``deadline``. Return True if dead."""

        def remaining() -> float:
            return max(0.0, deadline - time.monotonic())

        try:
            if worker.process.is_alive():
                try:
                    worker.request_queue.put(encode_json_wire({"type": "shutdown"}))
                except Exception:
                    pass
                worker.process.join(timeout=remaining())
        finally:
            if worker.process.is_alive():
                self._terminate_process(worker.process, deadline=deadline)
            if not worker.process.is_alive():
                try:
                    worker.request_queue.close()
                except Exception:
                    pass
                try:
                    worker.response_queue.close()
                except Exception:
                    pass
                # The worker wrapper drains/stops Hermes' asynchronous file
                # logger before exiting. Joining above ensures no handler can
                # still write while the worker-owned home is being removed.
                log_dir = worker.hermes_home / "logs"
                logging_drained = (
                    worker.hermes_home / _LOGGING_DRAINED_MARKER
                ).is_file()
                if logging_drained or not log_dir.exists():
                    shutil.rmtree(worker.hermes_home, ignore_errors=True)
                return True
            return False

    def _recv_until(
        self,
        response_queue: Queue[bytes],
        process: BaseProcess,
        *,
        expected_types: set[str],
        request_id: str | None,
        timeout_s: float,
        telemetry_calls: list[dict[str, Any]] | None = None,
        telemetry_warnings: list[str] | None = None,
        telemetry_worker_phases: list[dict[str, Any]] | None = None,
        on_provider_authorization: Callable[[dict[str, Any]], None] | None = None,
        on_provider_lifecycle: Callable[[dict[str, Any]], None] | None = None,
        on_graph_operation: Callable[[dict[str, Any]], None] | None = None,
    ) -> dict[str, Any] | None:
        deadline = time.monotonic() + timeout_s
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                _drain_streamed_telemetry(
                    response_queue,
                    request_id=request_id,
                    telemetry_calls=telemetry_calls,
                    telemetry_warnings=telemetry_warnings,
                    telemetry_worker_phases=telemetry_worker_phases,
                )
                return None
            try:
                raw = response_queue.get(timeout=min(remaining, 0.25))
            except Exception:
                if not process.is_alive():
                    _drain_streamed_telemetry(
                        response_queue,
                        request_id=request_id,
                        telemetry_calls=telemetry_calls,
                        telemetry_warnings=telemetry_warnings,
                        telemetry_worker_phases=telemetry_worker_phases,
                    )
                    return None
                continue
            try:
                message = decode_json_wire(raw)
            except Exception:
                if not process.is_alive():
                    _drain_streamed_telemetry(
                        response_queue,
                        request_id=request_id,
                        telemetry_calls=telemetry_calls,
                        telemetry_warnings=telemetry_warnings,
                        telemetry_worker_phases=telemetry_worker_phases,
                    )
                    return None
                continue
            msg_type = message.get("type")
            if msg_type == "telemetry":
                _ingest_streamed_telemetry(
                    message,
                    request_id=request_id,
                    telemetry_calls=telemetry_calls,
                    telemetry_warnings=telemetry_warnings,
                    telemetry_worker_phases=telemetry_worker_phases,
                )
                continue
            if msg_type == "provider_authorization_request":
                if (
                    request_id is not None
                    and str(message.get("requestId") or "") == request_id
                    and on_provider_authorization is not None
                ):
                    on_provider_authorization(message)
                continue
            if msg_type == "provider_lifecycle_request":
                if (
                    request_id is not None
                    and str(message.get("requestId") or "") == request_id
                    and on_provider_lifecycle is not None
                ):
                    on_provider_lifecycle(message)
                continue
            if msg_type == "graph_operation_request":
                if (
                    request_id is not None
                    and str(message.get("requestId") or "") == request_id
                    and on_graph_operation is not None
                ):
                    on_graph_operation(message)
                continue
            if msg_type not in expected_types:
                if not process.is_alive():
                    _drain_streamed_telemetry(
                        response_queue,
                        request_id=request_id,
                        telemetry_calls=telemetry_calls,
                        telemetry_warnings=telemetry_warnings,
                        telemetry_worker_phases=telemetry_worker_phases,
                    )
                    return None
                continue
            if (
                request_id is not None
                and str(message.get("requestId") or "") != request_id
            ):
                continue
            return message

    @staticmethod
    def _terminate_process(process: BaseProcess, *, deadline: float) -> None:
        if not process.is_alive():
            return

        def remaining() -> float:
            return max(0.0, deadline - time.monotonic())

        process.terminate()
        process.join(timeout=remaining())
        if process.is_alive():
            process.kill()
            # SIGKILL is immediate; allow a short reap window even if the
            # shared deadline has already elapsed so we do not abandon a live pid.
            process.join(timeout=max(remaining(), 0.25))


def get_hermes_graph_agent_host() -> HermesGraphAgentHost:
    """Return the process-wide host singleton used by the live-control app."""
    global _GLOBAL_HOST
    with _HOST_LOCK:
        if _GLOBAL_HOST is None:
            _GLOBAL_HOST = HermesGraphAgentHost()
        return _GLOBAL_HOST


def shutdown_hermes_graph_agent_host(
    *,
    timeout_s: float = DEFAULT_SHUTDOWN_TIMEOUT_S,
) -> bool:
    """Shut down the process-wide host; clear the singleton only if terminated.

    Returns True when no live tracked worker remains. If termination fails, the
    host stays registered under ``_GLOBAL_HOST`` so a later
    :func:`get_hermes_graph_agent_host` cannot create a second worker.
    """
    global _GLOBAL_HOST
    with _HOST_LOCK:
        host = _GLOBAL_HOST
    if host is None:
        return True
    stopped = host.shutdown(timeout_s=timeout_s)
    if stopped:
        with _HOST_LOCK:
            if _GLOBAL_HOST is host:
                _GLOBAL_HOST = None
        return True
    return False


__all__ = [
    "DEFAULT_TURN_TIMEOUT_S",
    "HermesGraphAgentHost",
    "get_hermes_graph_agent_host",
    "hermes_graph_agent_worker_main",
    "shutdown_hermes_graph_agent_host",
]
