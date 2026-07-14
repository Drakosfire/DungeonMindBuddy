"""Process-isolated host for Rung 3 Hermes graph-agent turns (PR010B Rung 4 / PR353).

FastAPI must not call :func:`run_hermes_graph_agent_turn` in-process. This host
owns a reusable ``spawn`` worker that imports and executes Rung 3 only inside
the child process, communicating through a bounded typed request/result wire.
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

from apps.live_control_server.services.hermes_graph_agent import (
    PROCESS_ISOLATION_MODE,
    HermesGraphAgentTurnRequest,
    HermesGraphAgentTurnResult,
    deserialize_hermes_graph_agent_turn_request,
    deserialize_hermes_graph_agent_turn_result,
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
    request_queue: Queue[dict[str, Any]],
    response_queue: Queue[dict[str, Any]],
) -> None:
    """Default worker entry: import and execute Rung 3 only in the child."""
    # Import inside the worker so the parent never executes the turn runtime.
    from apps.live_control_server.services.hermes_graph_agent import (
        run_hermes_graph_agent_turn,
    )

    response_queue.put(
        {
            "type": "ready",
            "pid": os.getpid(),
        }
    )
    while True:
        message = request_queue.get()
        if not isinstance(message, Mapping):
            response_queue.put(
                {
                    "type": "protocol_error",
                    "errorCode": "hermes_worker_protocol_error",
                    "errorMessage": "Worker received a non-mapping command.",
                }
            )
            continue
        msg_type = message.get("type")
        if msg_type == "shutdown":
            response_queue.put({"type": "shutdown_ack", "pid": os.getpid()})
            return
        if msg_type != "execute":
            response_queue.put(
                {
                    "type": "protocol_error",
                    "errorCode": "hermes_worker_protocol_error",
                    "errorMessage": f"Unknown worker command type: {msg_type!r}",
                }
            )
            continue

        request_id = str(message.get("requestId") or "")
        # Acceptance is the no-replay boundary: after this message, the host
        # must not transparently retry the turn.
        response_queue.put(
            {
                "type": "accepted",
                "requestId": request_id,
                "pid": os.getpid(),
            }
        )
        try:
            payload = message.get("payload")
            if not isinstance(payload, Mapping):
                raise ValueError("execute payload must be a mapping")
            request = deserialize_hermes_graph_agent_turn_request(payload)
            result = run_hermes_graph_agent_turn(request)
            response_queue.put(
                {
                    "type": "result",
                    "requestId": request_id,
                    "pid": os.getpid(),
                    "payload": serialize_hermes_graph_agent_turn_result(result),
                }
            )
        except Exception as exc:
            response_queue.put(
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


@dataclass(frozen=True, slots=True)
class _WorkerHandles:
    process: BaseProcess
    request_queue: Queue[dict[str, Any]]
    response_queue: Queue[dict[str, Any]]
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
        self._lock = threading.RLock()
        self._worker: _WorkerHandles | None = None
        self._started = False

    @property
    def start_method(self) -> str:
        return self._ctx.get_start_method()

    @property
    def worker_pid(self) -> int | None:
        with self._lock:
            if self._worker is None:
                return None
            return self._worker.pid

    def start(self) -> None:
        """Ensure the host may create a worker (idempotent)."""
        with self._lock:
            self._started = True
            if self._worker is None or not self._worker.process.is_alive():
                self._spawn_worker_locked()

    def shutdown(self, *, timeout_s: float = DEFAULT_SHUTDOWN_TIMEOUT_S) -> None:
        """Stop the worker and release IPC resources."""
        with self._lock:
            self._started = False
            self._stop_worker_locked(timeout_s=timeout_s)

    def execute(
        self,
        request: HermesGraphAgentTurnRequest,
        *,
        timeout_s: float | None = None,
    ) -> HermesGraphAgentTurnResult:
        """Run one turn on the worker. Concurrent callers queue on the host lock."""
        turn_timeout = self._turn_timeout_s if timeout_s is None else float(timeout_s)
        wire = serialize_hermes_graph_agent_turn_request(request)
        with self._lock:
            return self._execute_locked(wire, turn_timeout_s=turn_timeout)

    def _execute_locked(
        self,
        wire: dict[str, Any],
        *,
        turn_timeout_s: float,
    ) -> HermesGraphAgentTurnResult:
        self._started = True
        # Pre-accept: one restart/retry is allowed.
        for attempt in (1, 2):
            try:
                worker = self._ensure_worker_locked()
            except Exception:
                if attempt == 1:
                    self._stop_worker_locked(timeout_s=1.0)
                    continue
                return _host_error_result(
                    error_code="hermes_worker_start_failed",
                    error_message="Hermes graph-agent worker failed to start.",
                )

            request_id = str(uuid.uuid4())
            try:
                worker.request_queue.put(
                    {
                        "type": "execute",
                        "requestId": request_id,
                        "payload": wire,
                    }
                )
            except Exception:
                self._stop_worker_locked(timeout_s=1.0)
                if attempt == 1:
                    continue
                return _host_error_result(
                    error_code="hermes_worker_lost",
                    error_message="Hermes graph-agent worker was lost before accept.",
                )

            accepted = self._wait_for_message_locked(
                worker,
                expected_types={"accepted"},
                request_id=request_id,
                timeout_s=self._accept_timeout_s,
            )
            if accepted is None:
                self._stop_worker_locked(timeout_s=1.0)
                if attempt == 1:
                    continue
                return _host_error_result(
                    error_code="hermes_worker_lost",
                    error_message=(
                        "Hermes graph-agent worker did not accept the request."
                    ),
                )
            if accepted.get("type") != "accepted":
                self._stop_worker_locked(timeout_s=1.0)
                if attempt == 1:
                    continue
                return _host_error_result(
                    error_code="hermes_worker_protocol_error",
                    error_message="Hermes graph-agent worker returned a bad accept.",
                )

            # Post-accept: never replay.
            result_message = self._wait_for_message_locked(
                worker,
                expected_types={"result"},
                request_id=request_id,
                timeout_s=turn_timeout_s,
            )
            if result_message is None:
                alive = worker.process.is_alive()
                self._stop_worker_locked(timeout_s=1.0)
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
                self._stop_worker_locked(timeout_s=1.0)
                return _host_error_result(
                    error_code="hermes_worker_protocol_error",
                    error_message="Hermes worker result payload was malformed.",
                )
            try:
                return deserialize_hermes_graph_agent_turn_result(payload)
            except Exception:
                self._stop_worker_locked(timeout_s=1.0)
                return _host_error_result(
                    error_code="hermes_worker_protocol_error",
                    error_message="Hermes worker result could not be deserialized.",
                )

        return _host_error_result(
            error_code="hermes_worker_start_failed",
            error_message="Hermes graph-agent worker failed before accept.",
        )

    def _ensure_worker_locked(self) -> _WorkerHandles:
        if self._worker is not None and self._worker.process.is_alive():
            return self._worker
        self._stop_worker_locked(timeout_s=1.0)
        return self._spawn_worker_locked()

    def _spawn_worker_locked(self) -> _WorkerHandles:
        request_queue: Queue[dict[str, Any]] = self._ctx.Queue()
        response_queue: Queue[dict[str, Any]] = self._ctx.Queue()
        process = self._ctx.Process(
            target=self._worker_target,
            args=(request_queue, response_queue),
            name="dmb-hermes-graph-agent-worker",
            daemon=True,
        )
        process.start()
        ready = self._recv_until_locked(
            response_queue,
            process,
            expected_types={"ready"},
            request_id=None,
            timeout_s=self._ready_timeout_s,
        )
        if ready is None or ready.get("type") != "ready":
            self._terminate_process(process, timeout_s=1.0)
            request_queue.close()
            response_queue.close()
            raise RuntimeError("Hermes worker did not become ready")
        pid = int(ready.get("pid") or process.pid or 0)
        handles = _WorkerHandles(
            process=process,
            request_queue=request_queue,
            response_queue=response_queue,
            pid=pid,
        )
        self._worker = handles
        return handles

    def _stop_worker_locked(self, *, timeout_s: float) -> None:
        worker = self._worker
        self._worker = None
        if worker is None:
            return
        try:
            if worker.process.is_alive():
                try:
                    worker.request_queue.put({"type": "shutdown"})
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

    def _wait_for_message_locked(
        self,
        worker: _WorkerHandles,
        *,
        expected_types: set[str],
        request_id: str | None,
        timeout_s: float,
    ) -> dict[str, Any] | None:
        return self._recv_until_locked(
            worker.response_queue,
            worker.process,
            expected_types=expected_types,
            request_id=request_id,
            timeout_s=timeout_s,
        )

    def _recv_until_locked(
        self,
        response_queue: Queue[dict[str, Any]],
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
                message = response_queue.get(timeout=min(remaining, 0.25))
            except Exception:
                if not process.is_alive():
                    return None
                continue
            if not isinstance(message, Mapping):
                continue
            msg_type = message.get("type")
            if msg_type not in expected_types:
                # Ignore unrelated protocol noise rather than wedging the host.
                if not process.is_alive():
                    return None
                continue
            if request_id is not None and str(message.get("requestId") or "") != request_id:
                continue
            return dict(message)

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
