"""Private process supervision; GenerationEngine alone performs inference IO."""

from __future__ import annotations

import asyncio
import json
import multiprocessing
import os
import time
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any


@dataclass(frozen=True)
class _WorkerOutcome:
    receipt: dict[str, Any] | None
    terminated: bool


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


def _worker_entry(factory, request: dict[str, Any], receipt_path: str) -> None:
    from generationengine.types import GenerationEngineError, TextRequest

    path = Path(receipt_path)

    async def execute() -> None:
        engine = factory()
        try:
            try:
                result = await engine.generate_text(TextRequest.model_validate(request))
            except GenerationEngineError as exc:
                _write_receipt(path, {
                    "kind": "provider_failure",
                    "failure_code": exc.failure.code.value,
                    "observation": exc.observation.model_dump(mode="json"),
                })
            except Exception as exc:
                _write_receipt(path, {
                    "kind": "worker_failure", "error_type": type(exc).__name__,
                })
            else:
                # Preserve raw response and GE receipt before aclose, executor
                # shutdown, and any consumer/schema validation in the parent.
                _write_receipt(path, {
                    "kind": "result", "result": result.model_dump(mode="json"),
                })
        finally:
            await engine.aclose()

    try:
        asyncio.run(execute())
    except BaseException as exc:
        _write_receipt(path, {
            "kind": "worker_failure", "error_type": type(exc).__name__,
        })


def _execute_in_owned_process(factory, request: dict[str, Any], *, deadline: float) -> _WorkerOutcome:
    # Spawn avoids inheriting caller threads, event loops, SDK resources or locks.
    # Factories supplied by callers must consequently be pickleable.
    context = multiprocessing.get_context("spawn")
    with TemporaryDirectory(prefix="dmb-recap-inference-") as directory:
        path = Path(directory) / "receipt.json"
        process = context.Process(
            target=_worker_entry, args=(factory, request, str(path)),
            name="dmb-recap-inference", daemon=True,
        )
        terminated = False
        try:
            if time.monotonic() >= deadline:
                return _WorkerOutcome(None, True)
            try:
                process.start()
            except Exception:
                raise _WorkerStartFailure("inference worker could not start") from None
            # Reserve time to kill/reap within the configured wall-clock budget.
            remaining = max(0.0, deadline - time.monotonic())
            reap_reserve = min(0.05, remaining / 4)
            process.join(max(0.0, remaining - reap_reserve))
            if process.is_alive():
                # Kill/reap precisely the owned child. Do not await its async or
                # thread cleanup after the deadline, and do not redispatch.
                terminated = True
                process.kill()
                process.join()
            receipt = json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
            return _WorkerOutcome(receipt, terminated)
        finally:
            if process.pid is not None:
                if process.is_alive():
                    process.kill()
                process.join()
            process.close()
