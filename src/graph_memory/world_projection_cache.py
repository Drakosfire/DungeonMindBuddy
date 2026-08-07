"""Optional process-local World Graph completed-projection cache (OPT01).

Consulted only after a projection read context has been resolved. Cache keys
are exact resident-generation context keys and perform zero durable file reads
and zero content hashing. Correctness must hold with this cache disabled via
``DMB_WORLD_GRAPH_PROJECTION_CACHE=0``.

Resident revision verification is owned by ``world_read_runtime`` and is not
disabled by the payload-cache env switch.
"""

from __future__ import annotations

import os
import re
import threading
import time
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from graph_memory.projection.world_projection import (
    WorldGraphProjection,
    WorldGraphProjectionRequest,
)

_DEFAULT_MAX_ENTRIES = 16
_DEFAULT_TTL_S = 120.0
_WORLD_ID_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]{0,127}$")
_REVISION_ID_RE = re.compile(r"^rev:[a-f0-9]{16,64}$")


class ProjectionCacheSingleFlightResetError(RuntimeError):
    """Raised when in-flight projection builds are cleared during test reset."""


@dataclass(frozen=True)
class CacheKey:
    root: str
    world_id: str
    campaign_id: str
    revision_id: str
    selected_resident_generation: int
    head_revision_id: str
    head_resident_generation: int
    focus_kind: str
    focus_session_id: str
    focus_campaign_id: str
    admissibility: str
    scope_mode: str
    query_text: str


@dataclass
class _CacheEntry:
    projection: WorldGraphProjection
    expires_at: float


@dataclass
class _InFlightBuild:
    condition: threading.Condition
    generation: int
    result: WorldGraphProjection | None = None
    error: BaseException | None = None
    done: bool = False


class WorldGraphProjectionCache:
    """Tiny LRU+TTL cache for completed projection payloads."""

    def __init__(
        self,
        *,
        max_entries: int = _DEFAULT_MAX_ENTRIES,
        ttl_s: float = _DEFAULT_TTL_S,
    ) -> None:
        self._max_entries = max(1, int(max_entries))
        self._ttl_s = max(0.0, float(ttl_s))
        self._entries: OrderedDict[CacheKey, _CacheEntry] = OrderedDict()
        self._lock = threading.Lock()
        self.hits = 0
        self.misses = 0

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()
            self.hits = 0
            self.misses = 0

    def stats(self) -> dict[str, int]:
        with self._lock:
            return {
                "hits": self.hits,
                "misses": self.misses,
                "size": len(self._entries),
            }

    def get(self, key: CacheKey) -> WorldGraphProjection | None:
        now = time.monotonic()
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                self.misses += 1
                return None
            if entry.expires_at <= now:
                self._entries.pop(key, None)
                self.misses += 1
                return None
            self._entries.move_to_end(key)
            self.hits += 1
            return entry.projection

    def put(self, key: CacheKey, projection: WorldGraphProjection) -> None:
        expires_at = time.monotonic() + self._ttl_s
        with self._lock:
            self._entries[key] = _CacheEntry(projection=projection, expires_at=expires_at)
            self._entries.move_to_end(key)
            while len(self._entries) > self._max_entries:
                self._entries.popitem(last=False)


_PROJECTION_CACHE = WorldGraphProjectionCache()
_IN_FLIGHT: dict[CacheKey, _InFlightBuild] = {}
_IN_FLIGHT_LOCK = threading.Lock()
# Bumped on clear/reset so a builder that finishes after invalidation cannot
# republish into the completed cache. Must move under the same lock that
# gates publish, and before emptying the completed cache.
_CACHE_GENERATION = 0
# Test-only: runs after builder() returns and before the publish generation check.
_after_builder_before_publish_hook: Callable[[], None] | None = None


def projection_cache_enabled() -> bool:
    """Return whether the completed projection payload cache is active."""
    raw = (os.environ.get("DMB_WORLD_GRAPH_PROJECTION_CACHE") or "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def projection_cache_stats() -> dict[str, int]:
    return _PROJECTION_CACHE.stats()


def _fail_in_flight_entries(
    entries: list[_InFlightBuild],
    *,
    reason: str,
) -> None:
    for entry in entries:
        with entry.condition:
            if entry.done:
                continue
            entry.error = ProjectionCacheSingleFlightResetError(reason)
            entry.done = True
            entry.condition.notify_all()


def _invalidate_in_flight(*, reason: str) -> None:
    global _CACHE_GENERATION
    with _IN_FLIGHT_LOCK:
        _CACHE_GENERATION += 1
        entries = list(_IN_FLIGHT.values())
        _IN_FLIGHT.clear()
    _fail_in_flight_entries(entries, reason=reason)


def reset_projection_cache_single_flight_for_tests() -> None:
    """Clear in-flight builds and fail any waiters (test helper)."""
    global _after_builder_before_publish_hook
    _after_builder_before_publish_hook = None
    _invalidate_in_flight(reason="projection cache single-flight reset for tests")


def clear_projection_cache() -> None:
    """Drop completed payloads and invalidate in-flight builders atomically.

    Generation bump, in-flight map clear, and completed-cache clear share one
    lock with the builder publish path so an old builder cannot observe a
    cleared cache while still holding a pre-clear generation.
    """
    global _CACHE_GENERATION
    with _IN_FLIGHT_LOCK:
        _CACHE_GENERATION += 1
        entries = list(_IN_FLIGHT.values())
        _IN_FLIGHT.clear()
        _PROJECTION_CACHE.clear()
    _fail_in_flight_entries(entries, reason="projection cache cleared")


def make_projection_cache_key(
    root: Path,
    request: WorldGraphProjectionRequest,
    *,
    revision_id: str,
    head_revision_id: str,
    selected_resident_generation: int,
    head_resident_generation: int,
) -> CacheKey:
    """Build a completed-payload cache key from an already-resolved context.

    Performs no durable file reads and no content hashing.
    """
    if not _WORLD_ID_RE.fullmatch(request.world_id):
        raise ValueError(f"invalid world_id: {request.world_id!r}")
    for candidate in (revision_id, head_revision_id):
        if not _REVISION_ID_RE.fullmatch(candidate):
            raise ValueError(f"invalid revision_id: {candidate!r}")
    focus = request.focus
    return CacheKey(
        root=str(root.resolve()),
        world_id=request.world_id,
        campaign_id=request.campaign_id,
        revision_id=revision_id,
        selected_resident_generation=int(selected_resident_generation),
        head_revision_id=head_revision_id,
        head_resident_generation=int(head_resident_generation),
        focus_kind=focus.kind,
        focus_session_id=str(focus.session_id or ""),
        focus_campaign_id=str(getattr(focus, "campaign_id", None) or ""),
        admissibility=str(request.admissibility),
        scope_mode=str(getattr(request, "scope_mode", "campaign") or "campaign"),
        query_text=str(request.query_text or ""),
    )


def get_cached_projection(key: CacheKey) -> WorldGraphProjection | None:
    return _PROJECTION_CACHE.get(key)


def put_cached_projection(key: CacheKey, projection: WorldGraphProjection) -> None:
    _PROJECTION_CACHE.put(key, projection)


def get_or_build_cached_projection(
    key: CacheKey,
    builder: Callable[[], WorldGraphProjection],
) -> tuple[WorldGraphProjection, Literal["hit", "miss", "coalesced"]]:
    """Return a completed projection, coalescing concurrent builds for one key."""
    cached = get_cached_projection(key)
    if cached is not None:
        return cached, "hit"

    is_builder = False
    wait_entry: _InFlightBuild | None = None
    with _IN_FLIGHT_LOCK:
        cached = get_cached_projection(key)
        if cached is not None:
            return cached, "hit"
        existing = _IN_FLIGHT.get(key)
        if existing is not None:
            wait_entry = existing
        else:
            wait_entry = _InFlightBuild(
                condition=threading.Condition(),
                generation=_CACHE_GENERATION,
            )
            _IN_FLIGHT[key] = wait_entry
            is_builder = True

    assert wait_entry is not None
    if is_builder:
        try:
            projection = builder()
            hook = _after_builder_before_publish_hook
            if hook is not None:
                hook()
            with _IN_FLIGHT_LOCK:
                publish = (
                    wait_entry.generation == _CACHE_GENERATION
                    and _IN_FLIGHT.get(key) is wait_entry
                )
                if publish:
                    put_cached_projection(key, projection)
                if _IN_FLIGHT.get(key) is wait_entry:
                    _IN_FLIGHT.pop(key, None)
            with wait_entry.condition:
                if wait_entry.done:
                    # Cleared/reset while building; waiters already finalized.
                    raise ProjectionCacheSingleFlightResetError(
                        "projection cache invalidated during build"
                    )
                if not publish:
                    wait_entry.error = ProjectionCacheSingleFlightResetError(
                        "projection cache invalidated during build"
                    )
                    wait_entry.done = True
                    wait_entry.condition.notify_all()
                    raise wait_entry.error
                wait_entry.result = projection
                wait_entry.done = True
                wait_entry.condition.notify_all()
            return projection, "miss"
        except BaseException as exc:
            with _IN_FLIGHT_LOCK:
                if _IN_FLIGHT.get(key) is wait_entry:
                    _IN_FLIGHT.pop(key, None)
            with wait_entry.condition:
                if not wait_entry.done:
                    wait_entry.error = exc
                    wait_entry.done = True
                    wait_entry.condition.notify_all()
            raise
    with wait_entry.condition:
        while not wait_entry.done:
            wait_entry.condition.wait()
        if wait_entry.error is not None:
            raise wait_entry.error
        assert wait_entry.result is not None
        return wait_entry.result, "coalesced"


__all__ = [
    "CacheKey",
    "ProjectionCacheSingleFlightResetError",
    "clear_projection_cache",
    "get_cached_projection",
    "get_or_build_cached_projection",
    "make_projection_cache_key",
    "projection_cache_enabled",
    "projection_cache_stats",
    "put_cached_projection",
    "reset_projection_cache_single_flight_for_tests",
]
