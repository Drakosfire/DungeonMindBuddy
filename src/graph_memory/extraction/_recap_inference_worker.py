"""Private process supervision; GenerationEngine alone performs inference IO."""

from __future__ import annotations

import asyncio
import json
import math
import multiprocessing
import os
import shutil
from contextlib import contextmanager
import time
from dataclasses import dataclass
from pathlib import Path
from tempfile import mkdtemp
from typing import Any


@dataclass(frozen=True)
class _WorkerOutcome:
    receipt: dict[str, Any] | None
    terminated: bool
    cleanup_confirmed: bool = True
    deadline_exceeded: bool = False


# Retain both the live handle and its private receipt directory on OS failure.
_UNREAPED_WORKERS: list[tuple[Any, str]] = []


@contextmanager
def _receipt_directory():
    directory = mkdtemp(prefix="dmb-recap-inference-")
    try:
        yield directory
    finally:
        if not any(retained == directory for _, retained in _UNREAPED_WORKERS):
            shutil.rmtree(directory)


class _WorkerStartFailure(RuntimeError):
    """The owned process was not started; no external dispatch occurred."""


def _write_receipt(path: Path, receipt: dict[str, Any]) -> None:
    # Private owned directory; publish only a complete JSON record. In particular,
    # never let cleanup overwrite a completed response with a later close error.
    if path.exists():
        return
    temporary = path.with_suffix(".pending")
    with temporary.open("x", encoding="utf-8") as stream:
        json.dump(receipt, stream)
    os.replace(temporary, path)


def _worker_entry(
    factory,
    request: dict[str, Any],
    receipt_path: str,
    attempt_evidence: dict[str, Any] | None = None,
    deadline: float | None = None,
    phase_reserve: float = 0.0,
) -> None:
    from generationengine.types import GenerationEngineError, TextRequest

    path = Path(receipt_path)
    attempt_records: list[dict[str, Any]] = []

    def usable_ms() -> int:
        if deadline is None:
            return request["deadline_ms"]
        return min(request["deadline_ms"], math.floor(
            (deadline - 2 * phase_reserve - time.monotonic()) * 1000
        ))

    def not_started() -> None:
        _write_receipt(path, {"kind": "not_started", "attempt_evidence": []})

    async def execute() -> None:
        if usable_ms() <= 0:
            not_started()
            return
        engine = factory()
        try:
            try:
                remaining_ms = usable_ms()
                if remaining_ms <= 0:
                    not_started()
                    return
                effective_request = {**request, "deadline_ms": remaining_ms}
                typed_request = TextRequest.model_validate(effective_request)
                callback = None
                if attempt_evidence is not None:
                    async def on_attempt_completed(event) -> None:
                        from src.graph_memory.extraction.bounded_recap_execution import (
                            _persist_attempt_response,
                        )

                        attempt_records.append(_persist_attempt_response(attempt_evidence, effective_request, event))

                    callback = on_attempt_completed
                result = await engine.generate_structured(
                    typed_request,
                    on_attempt_completed=callback,
                )
            except GenerationEngineError as exc:
                _write_receipt(path, {
                    "kind": "provider_failure",
                    "failure_code": exc.failure.code.value,
                    "observation": exc.observation.model_dump(mode="json"),
                    "attempt_evidence": attempt_records,
                })
            except Exception as exc:
                _write_receipt(path, {
                    "kind": "worker_failure",
                    "error_type": type(exc).__name__,
                    "attempt_evidence": attempt_records,
                })
            else:
                # Preserve raw response and GE receipt before aclose, executor
                # shutdown, and any consumer/schema validation in the parent.
                _write_receipt(path, {
                    "kind": "result",
                    "completed_at": time.monotonic(),
                    "result": result.model_dump(mode="json"),
                    "attempt_evidence": attempt_records,
                })
        finally:
            await engine.aclose()

    try:
        asyncio.run(execute())
    except BaseException as exc:
        _write_receipt(path, {
            "kind": "worker_failure",
            "error_type": type(exc).__name__,
            "attempt_evidence": attempt_records,
        })


def _execute_in_owned_process(
    factory,
    request: dict[str, Any],
    *,
    deadline: float,
    attempt_evidence: dict[str, Any] | None = None,
) -> _WorkerOutcome:
    # Keep any unreaped process owned; never silently redispatch after failed cleanup.
    for owned, retained_directory in list(_UNREAPED_WORKERS):
        if owned.is_alive():
            raise _WorkerStartFailure("inference worker cleanup remains unconfirmed; dispatch blocked")
        owned.join(0)
        owned.close()
        _UNREAPED_WORKERS.remove((owned, retained_directory))
        shutil.rmtree(retained_directory)
    started = time.monotonic()
    if started >= deadline:
        raise _WorkerStartFailure("inference budget expired before worker start")
    reserve = min(0.05, (deadline - started) / 4)
    # Spawn avoids inheriting caller threads, event loops, SDK resources or locks.
    # Factories supplied by callers must consequently be pickleable.
    context = multiprocessing.get_context("spawn")
    with _receipt_directory() as directory:
        path = Path(directory) / "receipt.json"
        process = context.Process(
            target=_worker_entry,
            args=(factory, request, str(path), attempt_evidence, deadline, reserve),
            name="dmb-recap-inference", daemon=True,
        )
        terminated = False
        try:
            if time.monotonic() >= deadline:
                raise _WorkerStartFailure("inference budget expired before worker start")
            try:
                process.start()
            except Exception:
                raise _WorkerStartFailure("inference worker could not start") from None
            # Reserve time to kill/reap within the configured wall-clock budget.
            process.join(max(0.0, deadline - reserve - time.monotonic()))
            if process.is_alive():
                # Kill/reap precisely the owned child. Do not await its async or
                # thread cleanup after the deadline, and do not redispatch.
                terminated = True
                process.kill()
                process.join(max(0.0, deadline - time.monotonic()))
            receipt = json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
            receipt_observed_at = time.monotonic()
            completed_at = receipt.get("completed_at") if isinstance(receipt, dict) else None
            late = bool(receipt and receipt.get("kind") == "result" and (
                not isinstance(completed_at, (int, float))
                or isinstance(completed_at, bool)
                or not math.isfinite(completed_at)
                or completed_at > deadline - 2 * reserve
                or receipt_observed_at > deadline
            ))
            return _WorkerOutcome(receipt, terminated, not process.is_alive(), late)
        finally:
            if process.pid is not None:
                if process.is_alive():
                    process.kill()
                process.join(max(0.0, deadline - time.monotonic()))
                if process.is_alive():
                    _UNREAPED_WORKERS.append((process, directory))
                else:
                    process.close()
            else:
                process.close()
