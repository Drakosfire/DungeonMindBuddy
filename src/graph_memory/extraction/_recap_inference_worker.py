"""Private process supervision; GenerationEngine alone performs inference IO."""

from __future__ import annotations

import asyncio
import json
import multiprocessing
import os
import re
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


def _provider_failure_diagnostics(exc: BaseException) -> dict[str, Any]:
    """Internal transport metadata only; never stringify an exception/body."""
    names: list[str] = []
    statuses: list[int] = []
    seen: set[int] = set()
    current: BaseException | None = exc
    while current is not None and id(current) not in seen and len(seen) < 8:
        seen.add(id(current))
        name = type(current).__name__
        names.append(name if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,95}", name) else "Exception")
        try:
            status = getattr(current, "status_code", None)
            if status is None:
                status = getattr(getattr(current, "response", None), "status_code", None)
        except Exception:
            status = None
        if type(status) is int and 100 <= status <= 599 and status not in statuses:
            statuses.append(status)
        current = current.__cause__ or current.__context__
    return {"exception_types": names, "http_statuses": statuses,
            "chain_truncated": current is not None and id(current) not in seen}


def _worker_entry(
    factory,
    request: dict[str, Any],
    receipt_path: str,
    attempt_evidence: dict[str, Any] | None = None,
) -> None:
    from generationengine.types import GenerationEngineError, TextRequest

    path = Path(receipt_path)
    attempt_records: list[dict[str, Any]] = []

    async def execute() -> None:
        engine = factory()
        try:
            try:
                typed_request = TextRequest.model_validate(request)
                callback = None
                if attempt_evidence is not None:
                    async def on_attempt_completed(event) -> None:
                        from src.graph_memory.extraction.bounded_recap_execution import (
                            _write_private_response_evidence,
                        )

                        event_payload = event.model_dump(mode="json")
                        response_path, response_digest = _write_private_response_evidence(
                            Path(attempt_evidence["directory"]),
                            ordinal=attempt_evidence["pass_ordinal"],
                            pass_name=attempt_evidence["pass_name"],
                            request=request,
                            context_hashes=attempt_evidence["context_hashes"],
                            raw_observation=event_payload,
                            response_text=event.text,
                            attempt_event=event_payload,
                        )
                        attempt_records.append(
                            {
                                "event_id": event.event_id,
                                "ordinal": event.ordinal,
                                "kind": event.kind,
                                "response_status": event.response_status,
                                "path": str(response_path),
                                "sha256": response_digest,
                            }
                        )

                    callback = on_attempt_completed
                result = await engine.generate_structured(
                    typed_request,
                    on_attempt_completed=callback,
                )
            except GenerationEngineError as exc:
                _write_receipt(path, {
                    "kind": "provider_failure",
                    "failure_code": exc.failure.code.value,
                    "provider_failure_diagnostics": _provider_failure_diagnostics(exc),
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
    # Spawn avoids inheriting caller threads, event loops, SDK resources or locks.
    # Factories supplied by callers must consequently be pickleable.
    context = multiprocessing.get_context("spawn")
    with TemporaryDirectory(prefix="dmb-recap-inference-") as directory:
        path = Path(directory) / "receipt.json"
        process = context.Process(
            target=_worker_entry,
            args=(factory, request, str(path), attempt_evidence),
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
