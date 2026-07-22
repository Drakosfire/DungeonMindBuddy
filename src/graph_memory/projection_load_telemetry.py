"""Bounded graph-load telemetry for projection / catalog / retrieval paths.

Emits structured stage timings and counts. Never logs corpus prose, labels,
aliases, summaries, or source-markdown content.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass, field
from typing import Any, Iterator, Mapping

_LOGGER = logging.getLogger("dmb.graph_load")

_active_trace: ContextVar["ProjectionLoadTrace | None"] = ContextVar(
    "dmb_projection_load_trace",
    default=None,
)


@dataclass
class ProjectionLoadTrace:
    """Request-scoped timing + contribution-load counters."""

    pipeline: str
    started_at: float = field(default_factory=time.perf_counter)
    stages: list[dict[str, Any]] = field(default_factory=list)
    counts: dict[str, int] = field(default_factory=dict)
    meta: dict[str, Any] = field(default_factory=dict)
    contribution_cache_hits: int = 0
    contribution_cache_misses: int = 0
    contribution_load_ms: float = 0.0
    _contribution_cache: dict[tuple[str, str], Any] = field(default_factory=dict, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def bump(self, key: str, amount: int = 1) -> None:
        with self._lock:
            self.counts[key] = int(self.counts.get(key, 0)) + amount

    def set_meta(self, **kwargs: Any) -> None:
        with self._lock:
            for key, value in kwargs.items():
                if value is None:
                    continue
                if isinstance(value, str) and not value.strip():
                    continue
                self.meta[key] = value

    def add_stage(self, stage: str, elapsed_ms: float, **extra: Any) -> None:
        row: dict[str, Any] = {
            "stage": stage,
            "elapsed_ms": round(float(elapsed_ms), 3),
        }
        for key, value in extra.items():
            if value is None:
                continue
            row[key] = value
        with self._lock:
            self.stages.append(row)

    def get_cached_contribution(self, world_id: str, contribution_id: str) -> Any | None:
        key = (world_id, contribution_id)
        with self._lock:
            if key in self._contribution_cache:
                self.contribution_cache_hits += 1
                return self._contribution_cache[key]
        return None

    def put_cached_contribution(
        self,
        world_id: str,
        contribution_id: str,
        contribution: Any,
        *,
        load_ms: float,
    ) -> Any:
        key = (world_id, contribution_id)
        with self._lock:
            self.contribution_cache_misses += 1
            self.contribution_load_ms += float(load_ms)
            self._contribution_cache[key] = contribution
            return contribution

    def to_payload(self, *, outcome: str = "ok", error_code: str | None = None) -> dict[str, Any]:
        elapsed_ms = (time.perf_counter() - self.started_at) * 1000.0
        payload: dict[str, Any] = {
            "pipeline": self.pipeline,
            "elapsed_ms": round(elapsed_ms, 3),
            "outcome": outcome,
            "stages": list(self.stages),
            "counts": dict(self.counts),
            "contribution_cache_hits": self.contribution_cache_hits,
            "contribution_cache_misses": self.contribution_cache_misses,
            "contribution_load_ms": round(self.contribution_load_ms, 3),
        }
        if error_code:
            payload["error_code"] = error_code
        if self.meta:
            payload["meta"] = dict(self.meta)
        return payload


def current_projection_load_trace() -> ProjectionLoadTrace | None:
    return _active_trace.get()


@contextmanager
def projection_load_trace(
    pipeline: str,
    *,
    emit: bool = True,
    nest: bool = True,
    **meta: Any,
) -> Iterator[ProjectionLoadTrace]:
    """Bind a request-scoped trace and optionally emit a structured log line.

    When ``nest`` is true and a parent trace already exists, stages attach to
    the parent (preserving contribution-cache hits across nested projection
    builds such as recap standing-node world-scope reload).
    """
    parent = _active_trace.get() if nest else None
    if parent is not None:
        parent.set_meta(**{f"nested_{pipeline}_{k}": v for k, v in meta.items()})
        yield parent
        return

    trace = ProjectionLoadTrace(pipeline=pipeline)
    if meta:
        trace.set_meta(**meta)
    token: Token[ProjectionLoadTrace | None] = _active_trace.set(trace)
    outcome = "ok"
    error_code: str | None = None
    try:
        yield trace
    except Exception as exc:
        outcome = "error"
        error_code = type(exc).__name__
        raise
    finally:
        if emit:
            emit_projection_load_trace(trace, outcome=outcome, error_code=error_code)
        _active_trace.reset(token)


@contextmanager
def timed_stage(stage: str, **extra: Any) -> Iterator[dict[str, Any]]:
    """Time a nested stage and attach it to the active trace when present."""
    started = time.perf_counter()
    extras: dict[str, Any] = dict(extra)
    try:
        yield extras
    finally:
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        trace = current_projection_load_trace()
        if trace is not None:
            trace.add_stage(stage, elapsed_ms, **extras)


def emit_projection_load_trace(
    trace: ProjectionLoadTrace,
    *,
    outcome: str = "ok",
    error_code: str | None = None,
) -> dict[str, Any]:
    payload = trace.to_payload(outcome=outcome, error_code=error_code)
    _LOGGER.info("graph_load %s", json.dumps(payload, sort_keys=True, default=str))
    return payload


def stage_share(payload: Mapping[str, Any]) -> dict[str, float]:
    """Return stage elapsed_ms shares of total elapsed_ms (0..1)."""
    total = float(payload.get("elapsed_ms") or 0.0)
    if total <= 0:
        return {}
    shares: dict[str, float] = {}
    for stage in payload.get("stages") or []:
        if not isinstance(stage, Mapping):
            continue
        name = str(stage.get("stage") or "").strip()
        if not name:
            continue
        shares[name] = float(stage.get("elapsed_ms") or 0.0) / total
    return shares


__all__ = [
    "ProjectionLoadTrace",
    "current_projection_load_trace",
    "emit_projection_load_trace",
    "projection_load_trace",
    "stage_share",
    "timed_stage",
]
