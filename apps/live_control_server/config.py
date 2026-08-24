from __future__ import annotations

import os
from pathlib import Path

SESSION_DIR_ENV = "DUNGEONMIND_LIVE_SESSION_DIR"
WORLD_GRAPH_ROOT_ENV = "DUNGEONMIND_WORLD_GRAPH_ROOT"
# Explicit live/production world root for mutation guards. When unset, the
# configured mutation root (world_graph_root) is treated as live — never infer
# liveness solely from "<repo>/out".
LIVE_WORLD_GRAPH_ROOT_ENV = "DUNGEONMIND_LIVE_WORLD_GRAPH_ROOT"
# Dedicated root for promote source evidence fixtures / server-owned sources.
# Never treat the world graph store (world_graph_root / out/) as source authority.
EXTRACT_PROMOTE_SOURCE_ROOT_ENV = "DUNGEONMIND_EXTRACT_PROMOTE_SOURCE_ROOT"
# Whole-world authority transfer (cutover): tri-state World Graph authority
# selector (buddy_files | quiesced | dungeonmind). The canonical parser and the
# fail-closed local-mutation guard live in
# ``graph_memory.world_supergraph.storage``; re-exported here for the app layer.
WORLD_GRAPH_AUTHORITY_ENV = "DUNGEONMIND_WORLD_GRAPH_AUTHORITY"
# PostgreSQL DSN for the DungeonMind-backed World Graph authority adapter.
# Required only when WORLD_GRAPH_AUTHORITY_ENV=dungeonmind.
WORLD_GRAPH_AUTHORITY_DATABASE_URL_ENV = (
    "DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL"
)
# Cache root for the DungeonMind-hydrated read model. The cache is a pure
# derivative of DungeonMind durable state keyed by head revision; it never
# chooses authority and is never consulted when DungeonMind is unavailable.
# Production ``dungeonmind`` reads do not use this cache; remaining consumers
# are write/legacy compatibility until graph-runtime demolition.
WORLD_GRAPH_AUTHORITY_CACHE_ROOT_ENV = "DUNGEONMIND_WORLD_GRAPH_AUTHORITY_CACHE_ROOT"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def session_dir() -> Path:
    override = os.environ.get(SESSION_DIR_ENV, "").strip()
    if override:
        return Path(override)
    return repo_root() / "evals/c2_live_prep/live/session_22"


def world_graph_root() -> Path:
    override = os.environ.get(WORLD_GRAPH_ROOT_ENV, "").strip()
    if override:
        return Path(override).expanduser().resolve()
    return (repo_root() / "out").resolve()


def live_world_graph_root() -> Path:
    """Server-configured live world root that requires allowLiveWorld to mutate.

    Precedence:
    1. ``DUNGEONMIND_LIVE_WORLD_GRAPH_ROOT`` when set (explicit live designation).
    2. Otherwise ``world_graph_root()`` — the mutation target is live by default.
    """
    override = os.environ.get(LIVE_WORLD_GRAPH_ROOT_ENV, "").strip()
    if override:
        return Path(override).expanduser().resolve()
    return world_graph_root()


def extract_promote_source_root() -> Path | None:
    """Optional dedicated promote source-artifact root (outside the graph store)."""
    override = os.environ.get(EXTRACT_PROMOTE_SOURCE_ROOT_ENV, "").strip()
    if not override:
        return None
    return Path(override).expanduser().resolve()


def world_graph_authority_mode() -> str:
    """Current World Graph authority mode (see world_supergraph.storage)."""
    from graph_memory.world_supergraph.storage import (
        world_graph_authority_mode as _mode,
    )

    return _mode()


def world_graph_authority_database_url() -> str | None:
    """PostgreSQL DSN for the DungeonMind-backed authority, when configured."""
    override = os.environ.get(WORLD_GRAPH_AUTHORITY_DATABASE_URL_ENV, "").strip()
    return override or None


def world_graph_authority_cache_root() -> Path:
    """Root for the DungeonMind-hydrated read-model cache (never authority)."""
    override = os.environ.get(WORLD_GRAPH_AUTHORITY_CACHE_ROOT_ENV, "").strip()
    if override:
        return Path(override).expanduser().resolve()
    return (
        repo_root() / "out" / "cache" / "dungeonmind_world_graph_authority"
    ).resolve()


def world_graph_native_production_read(root: Path | None = None) -> bool:
    """True when a World Graph read must execute in DungeonMind native services.

    In ``dungeonmind`` authority mode a production read is ``root is None`` or
    ``resolved(root) == world_graph_root()``. An explicit different root is a
    test/tooling override and stays on the file/kernel path. Obsolete
    ``DUNGEONMIND_WORLD_GRAPH_DIRECT_READ`` values have no effect.
    """
    from graph_memory.world_supergraph import storage

    if world_graph_authority_mode() != storage.WORLD_GRAPH_AUTHORITY_DUNGEONMIND:
        return False
    if root is not None and Path(root).resolve() != world_graph_root().resolve():
        return False
    return True
