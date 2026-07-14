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
    PROCESS_ISOLATION_MODE,
    HermesGraphAgentTurnRequest,
    HermesGraphAgentTurnResult,
    decode_json_wire,
    deserialize_hermes_graph_agent_turn_request,
    deserialize_hermes_graph_agent_turn_result,
    encode_json_wire,
    serialize_hermes_graph_agent_turn_request,
    serialize_hermes_graph_agent_turn_result,
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
    )


def hermes_graph_agent_worker_main(
    request_queue: Queue[bytes],
    response_queue: Queue[bytes],
) -> None:
    """Default worker entry: import and execute Rung 3 only in the child."""
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
        try:
            payload = message.get("payload")
            if not isinstance(payload, Mapping):
                raise ValueError("execute payload must be a mapping")
            request = deserialize_hermes_graph_agent_turn_request(payload)
            result = run_hermes_graph_agent_turn(request)
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
        self._turn_gate = threading.Lock()
        self._worker_lock = threading.RLock()
        self._worker: _WorkerHandles | None = None
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
        with self._worker_lock:
            self._closed = False
            self._started = True
            if self._worker is not None and not self._worker.process.is_alive():
                self._stop_worker_locked(timeout_s=1.0)
            if self._worker is not None and self._worker.process.is_alive():
                return
        self._spawn_worker()

    def shutdown(self, *, timeout_s: float = DEFAULT_SHUTDOWN_TIMEOUT_S) -> None:
        """Stop the worker and release IPC resources."""
        with self._worker_lock:
            self._closed = True
            self._started = False
            self._stop_worker_locked(timeout_s=timeout_s)

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
        for attempt in (1, 2):
            try:
                worker = self._acquire_worker_for_turn()
            except Exception:
                if attempt == 1:
                    with self._worker_lock:
                        self._stop_worker_locked(timeout_s=1.0)
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
                if self._closed or self._worker is not worker:
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
                    self._stop_worker_if_current_locked(worker, timeout_s=1.0)
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
            if accepted is None:
                with self._worker_lock:
                    self._stop_worker_if_current_locked(local_worker, timeout_s=1.0)
                if attempt == 1:
                    continue
                return _host_error_result(
                    error_code="hermes_worker_lost",
                    error_message="Hermes graph-agent worker did not accept the request.",
                )
            if accepted.get("type") != "accepted":
                with self._worker_lock:
                    self._stop_worker_if_current_locked(local_worker, timeout_s=1.0)
                if attempt == 1:
                    continue
                return _host_error_result(
                    error_code="hermes_worker_protocol_error",
                    error_message="Hermes graph-agent worker returned a bad accept.",
                )

            result_message = self._recv_until(
                local_worker.response_queue,
                local_worker.process,
                expected_types={"result"},
                request_id=request_id,
                timeout_s=turn_timeout_s,
            )
            if result_message is None:
                alive = local_worker.process.is_alive()
                with self._worker_lock:
                    self._stop_worker_if_current_locked(local_worker, timeout_s=1.0)
                if alive:
                    return _host_error_result(
                        error_code="hermes_worker_timeout",
                        error_message=(
                            "Hermes graph-agent worker exceeded the turn timeout."
                        ),
                    )
                return _host_error_result(
                    error_code="hermes_worker_lost",
                    error_message=(
                        "Hermes graph-agent worker was lost after accepting the request."
                    ),
                )
            payload = result_message.get("payload")
            if not isinstance(payload, Mapping):
                with self._worker_lock:
                    self._stop_worker_if_current_locked(local_worker, timeout_s=1.0)
                return _host_error_result(
                    error_code="hermes_worker_protocol_error",
                    error_message="Hermes worker result payload was malformed.",
                )
            try:
                return deserialize_hermes_graph_agent_turn_result(payload)
            except Exception:
                with self._worker_lock:
                    self._stop_worker_if_current_locked(local_worker, timeout_s=1.0)
                return _host_error_result(
                    error_code="hermes_worker_protocol_error",
                    error_message="Hermes worker result could not be deserialized.",
                )

        return _host_error_result(
            error_code="hermes_worker_start_failed",
            error_message="Hermes graph-agent worker failed before accept.",
        )

    def _acquire_worker_for_turn(self) -> _WorkerHandles:
        with self._worker_lock:
            if self._closed:
                raise RuntimeError("Hermes host is shut down")
            if self._worker is not None and self._worker.process.is_alive():
                return self._worker
            self._stop_worker_locked(timeout_s=1.0)
        return self._spawn_worker()

    def _spawn_worker(self) -> _WorkerHandles:
        """Start a worker and wait for ready without holding the lifecycle lock."""
        with self._worker_lock:
            if self._closed:
                raise RuntimeError("Hermes host is shut down")
            if self._worker is not None and self._worker.process.is_alive():
                return self._worker
            self._stop_worker_locked(timeout_s=1.0)
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
            local = provisional
            ready_timeout = self._ready_timeout_s

        ready = self._recv_until(
            local.response_queue,
            local.process,
            expected_types={"ready"},
            request_id=None,
            timeout_s=ready_timeout,
        )

        with self._worker_lock:
            if self._worker is not local:
                self._discard_handles(local, timeout_s=1.0)
                raise RuntimeError("Hermes worker spawn aborted")
            if self._closed:
                self._stop_worker_locked(timeout_s=1.0)
                raise RuntimeError("Hermes worker spawn aborted by shutdown")
            if ready is None or ready.get("type") != "ready":
                self._stop_worker_locked(timeout_s=1.0)
                raise RuntimeError("Hermes worker did not become ready")
            # Keep the same handles object so execute cleanup can identity-match
            # against self._worker after the ready wait released the lock.
            return local

    def _stop_worker_if_current_locked(
        self,
        local_worker: _WorkerHandles,
        *,
        timeout_s: float,
    ) -> None:
        if self._worker is local_worker:
            self._stop_worker_locked(timeout_s=timeout_s)

    def _stop_worker_locked(self, *, timeout_s: float) -> None:
        worker = self._worker
        self._worker = None
        if worker is None:
            return
        self._discard_handles(worker, timeout_s=timeout_s)

    def _discard_handles(self, worker: _WorkerHandles, *, timeout_s: float) -> None:
        try:
            if worker.process.is_alive():
                try:
                    worker.request_queue.put(
                        encode_json_wire({"type": "shutdown"})
                    )
                except Exception:
                    pass
                worker.process.join(timeout=timeout_s)
        finally:
            if worker.process.is_alive():
                self._terminate_process(worker.process, timeout_s=timeout_s)
            try:
                worker.request_queue.close()
            except Exception:
                pass
            try:
                worker.response_queue.close()
            except Exception:
                pass

    def _recv_until(
        self,
        response_queue: Queue[bytes],
        process: BaseProcess,
        *,
        expected_types: set[str],
        request_id: str | None,
        timeout_s: float,
    ) -> dict[str, Any] | None:
        deadline = time.monotonic() + timeout_s
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return None
            try:
                raw = response_queue.get(timeout=min(remaining, 0.25))
            except Exception:
                if not process.is_alive():
                    return None
                continue
            try:
                message = decode_json_wire(raw)
            except Exception:
                if not process.is_alive():
                    return None
                continue
            msg_type = message.get("type")
            if msg_type not in expected_types:
                if not process.is_alive():
                    return None
                continue
            if request_id is not None and str(message.get("requestId") or "") != request_id:
                continue
            return message

    @staticmethod
    def _terminate_process(process: BaseProcess, *, timeout_s: float) -> None:
        if not process.is_alive():
            return
        process.terminate()
        process.join(timeout=timeout_s)
        if process.is_alive():
            process.kill()
            process.join(timeout=timeout_s)


def get_hermes_graph_agent_host() -> HermesGraphAgentHost:
    """Return the process-wide host singleton used by the live-control app."""
    global _GLOBAL_HOST
    with _HOST_LOCK:
        if _GLOBAL_HOST is None:
            _GLOBAL_HOST = HermesGraphAgentHost()
        return _GLOBAL_HOST


def shutdown_hermes_graph_agent_host() -> None:
    """Shut down and drop the process-wide host singleton."""
    global _GLOBAL_HOST
    with _HOST_LOCK:
        host = _GLOBAL_HOST
        _GLOBAL_HOST = None
    if host is not None:
        host.shutdown()


__all__ = [
    "DEFAULT_TURN_TIMEOUT_S",
    "HermesGraphAgentHost",
    "get_hermes_graph_agent_host",
    "hermes_graph_agent_worker_main",
    "shutdown_hermes_graph_agent_host",
]
