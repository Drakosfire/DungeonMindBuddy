"""Process-isolated host for Rung 3 Hermes graph-agent turns (PR010B Rung 4 / PR353).

FastAPI must not call :func:`run_hermes_graph_agent_turn` in-process. This host
owns a reusable ``spawn`` worker that imports and executes Rung 3 only inside
the child process, communicating through bounded JSON wire bytes.
"""

from __future__ import annotations

import multiprocessing as mp
import os
import threading
import time
import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from multiprocessing.context import BaseContext
from multiprocessing.process import BaseProcess
from multiprocessing.queues import Queue
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
) -> None:
    if telemetry_calls is None:
        return
    if request_id is not None and str(message.get("requestId") or "") != request_id:
        return
    payload = message.get("payload")
    if not isinstance(payload, Mapping):
        if telemetry_warnings is not None and "observer_payload_malformed" not in telemetry_warnings:
            telemetry_warnings.append("observer_payload_malformed")
        return
    raw_calls = payload.get("modelCalls") or []
    if not isinstance(raw_calls, list):
        if telemetry_warnings is not None and "observer_payload_malformed" not in telemetry_warnings:
            telemetry_warnings.append("observer_payload_malformed")
        return
    for item in raw_calls:
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


def _drain_streamed_telemetry(
    response_queue: Queue[bytes],
    *,
    request_id: str | None,
    telemetry_calls: list[dict[str, Any]] | None,
    telemetry_warnings: list[str] | None,
) -> None:
    if telemetry_calls is None:
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

            result = run_hermes_graph_agent_turn(
                request,
                on_model_call=on_model_call,
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
    ) -> None:
        self._turn_timeout_s = float(turn_timeout_s)
        self._accept_timeout_s = float(accept_timeout_s)
        self._ready_timeout_s = float(ready_timeout_s)
        self._worker_target = worker_target or hermes_graph_agent_worker_main
        self._ctx = context or mp.get_context("spawn")
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
    ) -> HermesGraphAgentTurnResult:
        """Run one turn on the worker. Concurrent callers queue on the turn gate."""
        turn_timeout = self._turn_timeout_s if timeout_s is None else float(timeout_s)
        try:
            wire_payload = serialize_hermes_graph_agent_turn_request(request)
        except Exception:
            return _host_error_result(
                error_code="hermes_worker_protocol_error",
                error_message="Hermes graph-agent request could not be serialized.",
            )
        with self._turn_gate:
            return self._execute_turn(wire_payload, turn_timeout_s=turn_timeout)

    def _execute_turn(
        self,
        wire_payload: dict[str, Any],
        *,
        turn_timeout_s: float,
    ) -> HermesGraphAgentTurnResult:
        self._started = True
        # Retry only covers pre-enqueue / start failures. After enqueue, two-phase
        # proceed keeps Rung 3 unstarted until accept is observed; a lost accept
        # kills the worker (no proceed) and may retry once safely.
        for attempt in (1, 2):
            try:
                worker = self._acquire_worker_for_turn()
            except Exception:
                if attempt == 1:
                    with self._worker_lock:
                        self._stop_worker_locked(deadline=time.monotonic() + 1.0)
                    continue
                return _host_error_result(
                    error_code="hermes_worker_start_failed",
                    error_message="Hermes graph-agent worker failed to start.",
                )

            request_id = str(uuid.uuid4())
            message = {
                "type": "execute",
                "requestId": request_id,
                "payload": wire_payload,
            }
            try:
                wire_bytes = encode_json_wire(message)
            except Exception:
                return _host_error_result(
                    error_code="hermes_worker_protocol_error",
                    error_message="Hermes graph-agent request wire encoding failed.",
                )

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
                local_worker = worker

            accepted = self._recv_until(
                local_worker.response_queue,
                local_worker.process,
                expected_types={"accepted"},
                request_id=request_id,
                timeout_s=self._accept_timeout_s,
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
            streamed_warnings: list[str] = []
            try:
                local_worker.request_queue.put(
                    encode_json_wire(
                        {"type": "proceed", "requestId": request_id}
                    )
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

            result_message = self._recv_until(
                local_worker.response_queue,
                local_worker.process,
                expected_types={"result"},
                request_id=request_id,
                timeout_s=turn_timeout_s,
                telemetry_calls=streamed_calls,
                telemetry_warnings=streamed_warnings,
            )
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
                return deserialize_hermes_graph_agent_turn_result(payload)
            except Exception:
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
            process = self._ctx.Process(
                target=self._worker_target,
                args=(request_queue, response_queue),
                name="dmb-hermes-graph-agent-worker",
                daemon=True,
            )
            process.start()
            provisional = _WorkerHandles(
                process=process,
                request_queue=request_queue,
                response_queue=response_queue,
                pid=int(process.pid or 0),
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
                    worker.request_queue.put(
                        encode_json_wire({"type": "shutdown"})
                    )
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
                )
                continue
            if msg_type not in expected_types:
                if not process.is_alive():
                    _drain_streamed_telemetry(
                        response_queue,
                        request_id=request_id,
                        telemetry_calls=telemetry_calls,
                        telemetry_warnings=telemetry_warnings,
                    )
                    return None
                continue
            if request_id is not None and str(message.get("requestId") or "") != request_id:
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
