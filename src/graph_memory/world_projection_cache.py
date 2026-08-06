"""Optional process-local World Graph completed-projection cache (OPT01).

Consulted only after a projection read context has been resolved. Cache keys
are exact resident-generation context keys and perform zero durable file reads
and zero content hashing. Correctness must hold with this cache disabled via
``DMB_WORLD_GRAPH_PROJECTION_CACHE=0``.

Resident revision verification is owned by ``world_read_runtime`` and is not
disabled by the payload-cache env switch.
"""

from __future__ import annotations

import re
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path

from graph_memory.projection.world_projection import (
    WorldGraphProjection,
    WorldGraphProjectionRequest,
)

_DEFAULT_MAX_ENTRIES = 16
_DEFAULT_TTL_S = 120.0
_WORLD_ID_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]{0,127}$")
_REVISION_ID_RE = re.compile(r"^rev:[a-f0-9]{16,64}$")


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


def projection_cache_stats() -> dict[str, int]:
    return _PROJECTION_CACHE.stats()


def clear_projection_cache() -> None:
    _PROJECTION_CACHE.clear()


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


__all__ = [
    "CacheKey",
    "clear_projection_cache",
    "get_cached_projection",
    "make_projection_cache_key",
    "projection_cache_stats",
    "put_cached_projection",
]
