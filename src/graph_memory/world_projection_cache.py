"""Optional process-local World Graph projection cache.

NOT wired into the kernel by default. Projection integrity tests may mutate
contribution ledger bytes or revision payloads under an existing revision id;
caching only on revision id would hide those failures. Callers that opt in
must fingerprint every integrity-checked input in the cache key: the
contribution ledger, head.json, and the graph.json / revision.json payloads of
the selected revision *and* of the revision referenced by head (the kernel
validates the head's target revision even for pinned requests). Fingerprints
are content digests — aggregate metadata (file count, newest mtime) cannot
detect a contribution-file rename, which the kernel treats as an integrity
failure when the id-derived record path goes missing.

Two further fail-closed rules:

- A missing or unreadable fingerprinted input raises
  ``ProjectionSourceUnavailableError``; callers must treat that as "bypass the
  cache" rather than caching under sentinel fingerprints.
- Insertion must be gated by recomputing the key from the projection snapshot
  after the kernel read (post_key == pre_key). The key reflects source state
  observed *before* projection; a head move or payload mutation between
  fingerprinting and the kernel read must not be cached under the stale key.
"""

from __future__ import annotations

import hashlib
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
# Mirror of world_supergraph.paths._REVISION_ID_RE (the kernel boundary forbids
# importing it here). Guards digest paths against traversal from an unvalidated
# request revision_pin, which the service reads before the kernel rejects it.
_REVISION_ID_RE = re.compile(r"^rev:[a-f0-9]{16,64}$")


@dataclass(frozen=True)
class CacheKey:
    root: str
    world_id: str
    campaign_id: str
    revision_id: str
    head_revision_id: str
    source_fingerprint: str
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


def _world_dir(root: Path, world_id: str) -> Path:
    """Mirror the documented World SuperGraph layout without importing internals."""
    if not _WORLD_ID_RE.fullmatch(world_id):
        raise ValueError(f"invalid world_id: {world_id!r}")
    return root / "graph_memory" / "worlds" / world_id


class ProjectionSourceUnavailableError(RuntimeError):
    """A fingerprinted source file is missing or unreadable.

    Callers must treat this as "bypass the cache": an integrity-checked input
    that cannot be read must never produce cacheable sentinel fingerprints.
    """


def _file_digest(path: Path) -> str:
    """sha256 of file bytes.

    Raises ProjectionSourceUnavailableError when the file is missing or cannot
    be read.
    """
    if not path.is_file():
        raise ProjectionSourceUnavailableError(f"source file missing: {path}")
    try:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(65536), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except OSError as exc:
        raise ProjectionSourceUnavailableError(f"source file unreadable: {path}") from exc


def ledger_fingerprint(root: Path, world_id: str) -> str:
    """Content fingerprint of the contribution index + contributions directory.

    Sorted ``filename:sha256`` pairs so renames, rewrites, additions, and
    deletions all change the fingerprint. The kernel loads contribution records
    from id-derived paths and fails integrity when a referenced record is
    missing; a count + newest-mtime aggregate survives ``os.rename`` and would
    let a warm hit hide that failure.
    """
    world_dir = _world_dir(root, world_id)
    parts = [f"idx:{_file_digest(world_dir / 'contribution_index.json')}"]
    contrib_dir = world_dir / "contributions"
    if not contrib_dir.is_dir():
        raise ProjectionSourceUnavailableError(
            f"contributions directory missing: {contrib_dir}"
        )
    entries = ",".join(
        f"{path.name}:{_file_digest(path)}"
        for path in sorted(contrib_dir.glob("*.json"), key=lambda p: p.name)
    )
    parts.append(f"files:[{entries}]")
    return "|".join(parts)


def source_fingerprint(
    root: Path,
    world_id: str,
    revision_id: str,
    *,
    head_revision_id: str,
) -> str:
    """Digest every integrity-checked input the projection path validates.

    Warm hits must miss when head.json, the contribution ledger, or the
    selected revision's graph.json / revision.json change under a stable
    revision id — and, for pinned requests, also when the *head* revision's
    payloads change. The kernel validates the head's target revision even for
    pinned requests (response metadata such as ``headRevisionId`` / ``isHead``
    trusts it), so a pinned key that fingerprints only the pinned revision
    could serve a warm hit where the kernel would raise
    ``projection_integrity_error``.

    Raises ProjectionSourceUnavailableError if any input is missing or
    unreadable — callers must treat that as a cache bypass, not a cacheable
    state.
    """
    for candidate in (revision_id, head_revision_id):
        if not _REVISION_ID_RE.fullmatch(candidate):
            raise ValueError(f"invalid revision_id: {candidate!r}")
    world_dir = _world_dir(root, world_id)
    revision_dir = world_dir / "revisions" / revision_id
    parts = [
        f"ledger:{ledger_fingerprint(root, world_id)}",
        f"head:{_file_digest(world_dir / 'head.json')}",
        f"graph:{_file_digest(revision_dir / 'graph.json')}",
        f"rev:{_file_digest(revision_dir / 'revision.json')}",
    ]
    if head_revision_id != revision_id:
        head_revision_dir = world_dir / "revisions" / head_revision_id
        parts.append(f"headgraph:{_file_digest(head_revision_dir / 'graph.json')}")
        parts.append(f"headrev:{_file_digest(head_revision_dir / 'revision.json')}")
    return "|".join(parts)


def make_projection_cache_key(
    root: Path,
    request: WorldGraphProjectionRequest,
    *,
    revision_id: str,
    head_revision_id: str,
    source_fp: str | None = None,
    ledger_fp: str | None = None,
) -> CacheKey:
    focus = request.focus
    # ``ledger_fp`` retained as a deprecated alias for callers/tests that still
    # pass contribution-only fingerprints; prefer ``source_fp``.
    fingerprint = source_fp
    if fingerprint is None and ledger_fp is not None:
        fingerprint = ledger_fp
    if fingerprint is None:
        fingerprint = source_fingerprint(
            root,
            request.world_id,
            revision_id,
            head_revision_id=head_revision_id,
        )
    return CacheKey(
        root=str(root.resolve()),
        world_id=request.world_id,
        campaign_id=request.campaign_id,
        revision_id=revision_id,
        head_revision_id=head_revision_id,
        source_fingerprint=fingerprint,
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
    "ProjectionSourceUnavailableError",
    "clear_projection_cache",
    "get_cached_projection",
    "ledger_fingerprint",
    "make_projection_cache_key",
    "projection_cache_stats",
    "put_cached_projection",
    "source_fingerprint",
]
