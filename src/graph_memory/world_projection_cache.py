"""Optional process-local World Graph projection cache.

NOT wired into the kernel by default. Projection integrity tests may mutate
contribution ledger bytes under an existing revision id; caching only on
revision id would hide those failures. Callers that opt in must include a
ledger fingerprint (contribution index mtime/size) in the cache key.

# PR003_INTERNAL_GRAPH_KERNEL_EXEMPTION: ledger fingerprint needs contribution
# index/dir paths; fold behind a kernel facade when projection cache graduates
# from optional live-server helper (delete with projection-cache kernelization).
"""

from __future__ import annotations

import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path

from graph_memory.projection.world_projection import (
    WorldGraphProjection,
    WorldGraphProjectionRequest,
)
from graph_memory.world_supergraph import paths as world_paths

_DEFAULT_MAX_ENTRIES = 16
_DEFAULT_TTL_S = 120.0


@dataclass(frozen=True)
class CacheKey:
    root: str
    world_id: str
    campaign_id: str
    revision_id: str
    head_revision_id: str
    ledger_fingerprint: str
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
    """Tiny LRU+TTL cache for projection payloads."""

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


def ledger_fingerprint(root: Path, world_id: str) -> str:
    """Fingerprint contribution index + contributions directory for cache keys."""
    index_path = world_paths.contribution_index_path(root, world_id)
    contrib_dir = world_paths.world_dir(root, world_id) / "contributions"
    parts: list[str] = []
    if index_path.is_file():
        st = index_path.stat()
        parts.append(f"idx:{st.st_mtime_ns}:{st.st_size}")
    else:
        parts.append("idx:missing")
    if contrib_dir.is_dir():
        # Cheap directory fingerprint: count + newest mtime.
        newest = 0
        count = 0
        for path in contrib_dir.glob("*.json"):
            count += 1
            mtime = path.stat().st_mtime_ns
            if mtime > newest:
                newest = mtime
        parts.append(f"files:{count}:{newest}")
    else:
        parts.append("files:missing")
    return "|".join(parts)


def make_projection_cache_key(
    root: Path,
    request: WorldGraphProjectionRequest,
    *,
    revision_id: str,
    head_revision_id: str,
    ledger_fp: str | None = None,
) -> CacheKey:
    focus = request.focus
    return CacheKey(
        root=str(root.resolve()),
        world_id=request.world_id,
        campaign_id=request.campaign_id,
        revision_id=revision_id,
        head_revision_id=head_revision_id,
        ledger_fingerprint=ledger_fp or ledger_fingerprint(root, request.world_id),
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
    "ledger_fingerprint",
    "make_projection_cache_key",
    "projection_cache_stats",
    "put_cached_projection",
]
