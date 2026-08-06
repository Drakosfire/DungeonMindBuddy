"""Process-local verified resident world graph revision runtime (OPT01).

Loads immutable revision stores with integrity attestation, coalesces concurrent
cold loads per ``ResidentKey``, LRU-evicts registry entries (held references stay
valid), and exposes request-scoped I/O counters via ``contextvars``.

``clear_world_read_runtime`` / ``WorldReadRuntime.clear`` evict **resident**
entries only. Callers that also maintain a projection payload cache must pair
clear with ``clear_projection_cache`` separately — this module does not touch
secondary caches.
"""

from __future__ import annotations

import contextvars
import json
import os
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, replace
from pathlib import Path
from types import MappingProxyType
from typing import Any, Literal, Mapping

from pydantic import ValidationError

from graph_memory.evidence.assertion_support import DurableAssertionSupport
from graph_memory.kernel.contribution_models import GraphContribution
from graph_memory.kernel.world_graph import (
    WorldGraphNotFoundError,
    open_world_graph_head,
)
from graph_memory.kernel.world_projection import (
    WorldGraphProjectionError,
    _diagnostic,
    _integrity_error,
    _load_revision_store_with_integrity,
    _load_source_span_paragraph_text_index,
    _load_validated_contribution_from_disk,
    _parse_support,
    _resolve_repo_uri_file,
)
from graph_memory.projection.world_projection import WorldGraphProjectionRequest
from graph_memory.union_supergraph.model import UnionSupergraphStore
from graph_memory.union_supergraph.projection_identity import (
    UnionProjectionIdentityContext,
    build_union_projection_identity_context,
)
from graph_memory.world_supergraph import paths as world_paths
from graph_memory.world_supergraph.model import WorldGraphHead

_DEFAULT_RESIDENT_CAPACITY = 8
_MIN_RESIDENT_CAPACITY = 2

BackingHealth = Literal["unknown", "healthy", "unhealthy"]


@dataclass(frozen=True)
class ResidentKey:
    resolved_root: str
    world_id: str
    revision_id: str


@dataclass(frozen=True)
class ResidentRevision:
    key: ResidentKey
    generation: int
    store: UnionSupergraphStore
    contributions: Mapping[str, GraphContribution]
    supports_by_graph_object: Mapping[str, tuple[DurableAssertionSupport, ...]]
    identity_context: UnionProjectionIdentityContext
    source_span_paragraph_text: Mapping[str, str]
    backing_health: BackingHealth
    unhealthy_diagnostics: tuple[str, ...] = ()


@dataclass(frozen=True)
class ProjectionReadContext:
    selected: ResidentRevision
    head: ResidentRevision
    selected_revision_id: str
    head_revision_id: str


@dataclass
class RequestIoCounters:
    graph_payload_reads: int = 0
    revision_manifest_reads: int = 0
    contribution_reads: int = 0
    source_index_reads: int = 0
    head_json_reads: int = 0
    # Last get_or_load outcome observed on this request (selected/head loads).
    last_resident_status: Literal["hit", "miss", "coalesced"] = "miss"
    cold_load_ms: float | None = None
    resident_wait_ms: float = 0.0


_REQUEST_IO: contextvars.ContextVar[RequestIoCounters | None] = contextvars.ContextVar(
    "dmb_world_read_request_io",
    default=None,
)


def begin_request_io() -> RequestIoCounters:
    counters = RequestIoCounters()
    _REQUEST_IO.set(counters)
    return counters


def get_request_io() -> RequestIoCounters | None:
    return _REQUEST_IO.get()


def reset_request_io() -> None:
    _REQUEST_IO.set(None)


def _default_resident_capacity() -> int:
    raw = os.environ.get("DMB_WORLD_GRAPH_RESIDENT_CAPACITY", str(_DEFAULT_RESIDENT_CAPACITY))
    try:
        parsed = int(raw)
    except ValueError:
        parsed = _DEFAULT_RESIDENT_CAPACITY
    return max(_MIN_RESIDENT_CAPACITY, parsed)


def _increment_io(field: str) -> None:
    counters = _REQUEST_IO.get()
    if counters is None:
        return
    current = getattr(counters, field)
    setattr(counters, field, current + 1)


def _active_contribution_ids(store: UnionSupergraphStore) -> set[str]:
    ids: set[str] = set()
    for raw_support in store.assertion_support.values():
        support = _parse_support(raw_support)
        if support.support_state != "supported" or not support.active_contribution_ids:
            continue
        ids.update(support.active_contribution_ids)
    return ids


def _build_supports_by_graph_object(
    store: UnionSupergraphStore,
) -> dict[str, tuple[DurableAssertionSupport, ...]]:
    """Index active (supported + non-empty) supports by graph object id."""
    grouped: dict[str, list[DurableAssertionSupport]] = {}
    for raw_support in store.assertion_support.values():
        support = _parse_support(raw_support)
        if support.support_state != "supported" or not support.active_contribution_ids:
            continue
        grouped.setdefault(support.graph_object_id, []).append(support)
    return {key: tuple(supports) for key, supports in grouped.items()}


def _load_source_span_paragraph_text_indexed(
    root: Path,
    store: UnionSupergraphStore,
) -> dict[str, str]:
    paragraph_text_by_span_id: dict[str, str] = {}
    for artifact in store.source_artifacts.values():
        uri = getattr(artifact, "uri", None)
        if not isinstance(uri, str) or not uri.strip():
            continue
        artifact_path = _resolve_repo_uri_file(uri, root)
        if artifact_path is None:
            continue
        index_path = artifact_path.parent / "source_span_index.json"
        if not index_path.is_file():
            continue
        _increment_io("source_index_reads")
        for span_id, text in _load_source_span_paragraph_text_index(index_path).items():
            paragraph_text_by_span_id.setdefault(span_id, text)
    return paragraph_text_by_span_id


def _observe_head(root: Path, world_id: str) -> WorldGraphHead:
    _increment_io("head_json_reads")
    try:
        head = open_world_graph_head(root, world_id)
    except WorldGraphNotFoundError as exc:
        raise WorldGraphProjectionError(
            f"World graph unavailable for world_id={world_id!r}",
            code="world_graph_unavailable",
            status_code=404,
            diagnostics=[_diagnostic("world_graph_unavailable", str(exc))],
        ) from exc
    except (ValidationError, json.JSONDecodeError, TypeError, ValueError, OSError) as exc:
        raise _integrity_error(
            "World graph head is malformed.",
            detail=f"head validation failed: {exc}",
        ) from exc
    if head.world_id != world_id:
        raise _integrity_error(
            "World graph head world_id does not match requested world.",
            detail=f"head world_id={head.world_id!r} requested={world_id!r}",
        )
    try:
        world_paths.assert_safe_revision_id(head.head_revision_id)
    except ValueError as exc:
        raise _integrity_error(
            "World graph head references an unsafe revision id.",
            detail=f"head revision id validation failed: {exc}",
        ) from exc
    return head


@dataclass
class _LoadCompletion:
    resident: ResidentRevision | None = None
    error: BaseException | None = None


@dataclass
class _InflightLoad:
    epoch: int
    event: threading.Event
    completion: _LoadCompletion


class WorldReadRuntime:
    """LRU resident registry with coalesced cold loads."""

    def __init__(self, *, capacity: int | None = None) -> None:
        self._capacity = capacity if capacity is not None else _default_resident_capacity()
        self._capacity = max(_MIN_RESIDENT_CAPACITY, int(self._capacity))
        self._lock = threading.Lock()
        self._ready: OrderedDict[ResidentKey, ResidentRevision] = OrderedDict()
        self._inflight: dict[ResidentKey, _InflightLoad] = {}
        self._epoch = 0
        self._generation = 0

    def clear(self) -> None:
        with self._lock:
            self._epoch += 1
            self._ready.clear()

    def resident_count(self) -> int:
        with self._lock:
            return len(self._ready)

    def get_or_load_resident(
        self,
        root: Path,
        world_id: str,
        revision_id: str,
        *,
        not_found_code: str = "revision_not_found",
        not_found_message: str | None = None,
        not_found_as_integrity_error: bool = False,
    ) -> ResidentRevision:
        resolved_root = str(root.resolve())
        key = ResidentKey(resolved_root, world_id, revision_id)
        message = not_found_message or f"Revision not found: {revision_id!r}"

        while True:
            with self._lock:
                ready = self._ready.get(key)
                if ready is not None:
                    self._ready.move_to_end(key)
                    counters = _REQUEST_IO.get()
                    if counters is not None:
                        counters.last_resident_status = "hit"
                    return ready

                inflight = self._inflight.get(key)
                if inflight is not None:
                    wait_target = inflight
                    is_loader = False
                else:
                    load_epoch = self._epoch
                    wait_target = _InflightLoad(
                        epoch=load_epoch,
                        event=threading.Event(),
                        completion=_LoadCompletion(),
                    )
                    self._inflight[key] = wait_target
                    is_loader = True

            if not is_loader:
                wait_started = time.perf_counter()
                wait_target.event.wait()
                wait_ms = (time.perf_counter() - wait_started) * 1000.0
                counters = _REQUEST_IO.get()
                if counters is not None:
                    counters.last_resident_status = "coalesced"
                    counters.resident_wait_ms += wait_ms
                if wait_target.completion.error is not None:
                    raise wait_target.completion.error
                assert wait_target.completion.resident is not None
                return wait_target.completion.resident

            load_started = time.perf_counter()
            try:
                resident = self._cold_load(
                    Path(resolved_root),
                    world_id,
                    revision_id,
                    key=key,
                    not_found_code=not_found_code,
                    not_found_message=message,
                    not_found_as_integrity_error=not_found_as_integrity_error,
                )
            except BaseException as exc:
                wait_target.completion.error = exc
                wait_target.event.set()
                with self._lock:
                    self._inflight.pop(key, None)
                raise

            load_ms = (time.perf_counter() - load_started) * 1000.0
            counters = _REQUEST_IO.get()
            if counters is not None:
                counters.last_resident_status = "miss"
                counters.cold_load_ms = (
                    load_ms
                    if counters.cold_load_ms is None
                    else counters.cold_load_ms + load_ms
                )

            with self._lock:
                if wait_target.epoch == self._epoch:
                    self._ready[key] = resident
                    self._ready.move_to_end(key)
                    while len(self._ready) > self._capacity:
                        self._ready.popitem(last=False)
                wait_target.completion.resident = resident
                wait_target.event.set()
                self._inflight.pop(key, None)
            return resident

    def scrub_resident(
        self,
        root: Path,
        world_id: str,
        revision_id: str,
    ) -> dict[str, Any]:
        key = ResidentKey(str(root.resolve()), world_id, revision_id)
        with self._lock:
            resident = self._ready.get(key)

        if resident is None:
            return {"status": "miss", "diagnostics": ["resident not loaded"]}

        try:
            self._verify_backing_integrity(
                root,
                world_id,
                revision_id,
                resident,
            )
        except WorldGraphProjectionError as exc:
            diagnostics = [str(exc)]
            updated = replace(
                resident,
                backing_health="unhealthy",
                unhealthy_diagnostics=tuple(diagnostics),
            )
            with self._lock:
                if key in self._ready:
                    self._ready[key] = updated
            return {"status": "unhealthy", "diagnostics": diagnostics}

        updated = replace(
            resident,
            backing_health="healthy",
            unhealthy_diagnostics=(),
        )
        with self._lock:
            if key in self._ready:
                self._ready[key] = updated
        return {"status": "healthy", "diagnostics": []}

    def resolve_projection_read_context(
        self,
        root: Path,
        request: WorldGraphProjectionRequest,
    ) -> ProjectionReadContext:
        world_id = request.world_id
        if request.revision_pin:
            try:
                world_paths.assert_safe_revision_id(request.revision_pin)
            except ValueError as exc:
                raise WorldGraphProjectionError(
                    f"Revision pin is invalid: {request.revision_pin!r}",
                    code="invalid_request",
                    status_code=422,
                    diagnostics=[_diagnostic("invalid_revision_pin", str(exc))],
                ) from exc

        head = _observe_head(root, world_id)
        head_resident = self.get_or_load_resident(
            root,
            world_id,
            head.head_revision_id,
            not_found_code="projection_integrity_error",
            not_found_message=(
                f"World graph head references a revision that does not exist: "
                f"{head.head_revision_id!r}"
            ),
            not_found_as_integrity_error=True,
        )

        if request.revision_pin:
            selected = self.get_or_load_resident(
                root,
                world_id,
                request.revision_pin,
                not_found_code="revision_not_found",
                not_found_message=f"Revision pin not found: {request.revision_pin!r}",
            )
            selected_revision_id = request.revision_pin
        else:
            selected = head_resident
            selected_revision_id = head.head_revision_id

        return ProjectionReadContext(
            selected=selected,
            head=head_resident,
            selected_revision_id=selected_revision_id,
            head_revision_id=head.head_revision_id,
        )

    def _next_generation(self) -> int:
        with self._lock:
            self._generation += 1
            return self._generation

    def _cold_load(
        self,
        root: Path,
        world_id: str,
        revision_id: str,
        *,
        key: ResidentKey,
        not_found_code: str,
        not_found_message: str,
        not_found_as_integrity_error: bool,
    ) -> ResidentRevision:
        try:
            world_paths.assert_safe_revision_id(revision_id)
        except ValueError as exc:
            raise WorldGraphProjectionError(
                f"Revision id is invalid: {revision_id!r}",
                code="invalid_request",
                status_code=422,
                diagnostics=[_diagnostic("invalid_revision_id", str(exc))],
            ) from exc

        _increment_io("revision_manifest_reads")
        _increment_io("graph_payload_reads")
        _revision_id, store = _load_revision_store_with_integrity(
            root,
            world_id,
            revision_id,
            not_found_code=not_found_code,
            not_found_message=not_found_message,
            not_found_as_integrity_error=not_found_as_integrity_error,
        )
        del _revision_id

        contributions: dict[str, GraphContribution] = {}
        for contribution_id in sorted(_active_contribution_ids(store)):
            _increment_io("contribution_reads")
            contributions[contribution_id] = _load_validated_contribution_from_disk(
                root,
                world_id,
                contribution_id,
            )

        supports_by_graph_object = _build_supports_by_graph_object(store)
        identity_context = build_union_projection_identity_context(store)
        source_span_paragraph_text = _load_source_span_paragraph_text_indexed(root, store)
        generation = self._next_generation()

        return ResidentRevision(
            key=key,
            generation=generation,
            store=store,
            contributions=MappingProxyType(dict(contributions)),
            supports_by_graph_object=MappingProxyType(supports_by_graph_object),
            identity_context=identity_context,
            source_span_paragraph_text=MappingProxyType(source_span_paragraph_text),
            backing_health="healthy",
        )

    def _verify_backing_integrity(
        self,
        root: Path,
        world_id: str,
        revision_id: str,
        resident: ResidentRevision,
    ) -> None:
        _load_revision_store_with_integrity(
            root,
            world_id,
            revision_id,
            not_found_code="projection_integrity_error",
            not_found_message=f"Revision backing verification failed: {revision_id!r}",
            not_found_as_integrity_error=True,
        )
        for contribution_id in sorted(resident.contributions):
            _load_validated_contribution_from_disk(root, world_id, contribution_id)


_RUNTIME: WorldReadRuntime | None = None
_RUNTIME_LOCK = threading.Lock()

_ACTIVE_RESIDENT: contextvars.ContextVar[ResidentRevision | None] = contextvars.ContextVar(
    "dmb_world_read_active_resident",
    default=None,
)


def get_world_read_runtime() -> WorldReadRuntime:
    global _RUNTIME
    with _RUNTIME_LOCK:
        if _RUNTIME is None:
            _RUNTIME = WorldReadRuntime()
        return _RUNTIME


def clear_world_read_runtime() -> None:
    """Clear resident registry only; projection cache is caller-coupled."""
    global _RUNTIME
    with _RUNTIME_LOCK:
        if _RUNTIME is not None:
            _RUNTIME.clear()


def set_active_resident(resident: ResidentRevision | None) -> contextvars.Token:
    """Bind the selected resident for warm contribution/index lookups."""
    return _ACTIVE_RESIDENT.set(resident)


def reset_active_resident(token: contextvars.Token) -> None:
    _ACTIVE_RESIDENT.reset(token)


def get_active_resident() -> ResidentRevision | None:
    return _ACTIVE_RESIDENT.get()


def resolve_projection_read_context(
    root: Path,
    request: WorldGraphProjectionRequest,
) -> ProjectionReadContext:
    return get_world_read_runtime().resolve_projection_read_context(root, request)


@dataclass
class ProjectionRequestObservation:
    """Structured optimization observation for one service/kernel projection."""

    world_id: str = ""
    campaign_id: str = ""
    selected_revision_id: str = ""
    head_revision_id: str = ""
    resident_status: Literal["hit", "miss", "coalesced"] = "miss"
    selected_resident_generation: int | None = None
    head_resident_generation: int | None = None
    backing_health: BackingHealth = "unknown"
    head_resolution_ms: float = 0.0
    resident_wait_ms: float = 0.0
    cold_load_ms: float | None = None
    projection_cache_status: Literal["disabled", "hit", "miss"] = "disabled"
    projection_build_ms: float = 0.0
    resident_revision_count: int = 0
    graph_payload_reads_this_request: int = 0
    revision_manifest_reads_this_request: int = 0
    contribution_reads_this_request: int = 0
    source_index_reads_this_request: int = 0
    nodes_returned: int = 0
    relationships_returned: int = 0
    attributes_returned: int = 0


_LAST_OBSERVATION: contextvars.ContextVar[ProjectionRequestObservation | None] = (
    contextvars.ContextVar("dmb_world_read_last_observation", default=None)
)


def get_last_projection_observation() -> ProjectionRequestObservation | None:
    return _LAST_OBSERVATION.get()


def set_last_projection_observation(observation: ProjectionRequestObservation) -> None:
    _LAST_OBSERVATION.set(observation)
