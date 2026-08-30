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
# Mounted World Graph authority selector (CUTOVER D.3A).
# Unset / dungeonmind → DungeonMind. buddy_files / quiesced / unknown fail closed.
# Legacy storage parser under graph_memory remains for HISTORICAL_TOOL until D.3B.
WORLD_GRAPH_AUTHORITY_ENV = "DUNGEONMIND_WORLD_GRAPH_AUTHORITY"
WORLD_GRAPH_AUTHORITY_BUDDY_FILES = "buddy_files"
WORLD_GRAPH_AUTHORITY_QUIESCED = "quiesced"
WORLD_GRAPH_AUTHORITY_DUNGEONMIND = "dungeonmind"
_WORLD_GRAPH_AUTHORITY_MOUNTED_MODES = frozenset({WORLD_GRAPH_AUTHORITY_DUNGEONMIND})
_WORLD_GRAPH_AUTHORITY_RETIRED_MODES = frozenset(
    {
        WORLD_GRAPH_AUTHORITY_BUDDY_FILES,
        WORLD_GRAPH_AUTHORITY_QUIESCED,
    }
)
# PostgreSQL DSN for the DungeonMind-backed World Graph authority adapter.
WORLD_GRAPH_AUTHORITY_DATABASE_URL_ENV = (
    "DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL"
)
# Cache root leftover from the retired DungeonMind-hydrated read model.
# Mounted product must not consume it; env/function remain for unmounted names.
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


class WorldGraphAuthorityConfigurationError(RuntimeError):
    """Mounted World Graph authority selection refused a retired/invalid mode."""

    code = "world_graph_authority_configuration_invalid"


def world_graph_authority_mode(environ: dict[str, str] | None = None) -> str:
    """Parse mounted authority mode; unset defaults to DungeonMind.

    ``buddy_files``, ``quiesced``, and unknown values fail closed. Historical
    tooling that still needs file-store semantics must not use this mounted
    parser.
    """
    source = os.environ if environ is None else environ
    raw = source.get(WORLD_GRAPH_AUTHORITY_ENV, "").strip().lower()
    if not raw:
        return WORLD_GRAPH_AUTHORITY_DUNGEONMIND
    if raw in _WORLD_GRAPH_AUTHORITY_RETIRED_MODES:
        raise WorldGraphAuthorityConfigurationError(
            f"retired {WORLD_GRAPH_AUTHORITY_ENV} value {raw!r}; "
            f"mounted production accepts only "
            f"{WORLD_GRAPH_AUTHORITY_DUNGEONMIND!r} (or unset)"
        )
    if raw not in _WORLD_GRAPH_AUTHORITY_MOUNTED_MODES:
        raise WorldGraphAuthorityConfigurationError(
            f"unsupported {WORLD_GRAPH_AUTHORITY_ENV} value {raw!r}; "
            f"expected {WORLD_GRAPH_AUTHORITY_DUNGEONMIND!r} or unset"
        )
    return raw


def world_graph_authority_database_url() -> str | None:
    """PostgreSQL DSN for the DungeonMind-backed authority, when configured."""
    override = os.environ.get(WORLD_GRAPH_AUTHORITY_DATABASE_URL_ENV, "").strip()
    return override or None


def world_graph_authority_cache_root() -> Path:
    """Retired hydration-cache path. Not used by mounted production reads/writes."""
    override = os.environ.get(WORLD_GRAPH_AUTHORITY_CACHE_ROOT_ENV, "").strip()
    if override:
        return Path(override).expanduser().resolve()
    return (
        repo_root() / "out" / "cache" / "dungeonmind_world_graph_authority"
    ).resolve()


def world_graph_native_production_read(root: Path | None = None) -> bool:
    """True when mounted World Graph accessors may serve DungeonMind.

    Mounted authority is DungeonMind-only. An explicit alternate ``world_root``
    fails closed rather than selecting a file adapter.
    """
    if world_graph_authority_mode() != WORLD_GRAPH_AUTHORITY_DUNGEONMIND:
        return False
    if root is not None and Path(root).resolve() != world_graph_root().resolve():
        return False
    return True


def require_mounted_dungeonmind_world_graph(*, world_root: Path | None = None) -> None:
    """Fail closed unless this process may use mounted DungeonMind World Graph."""
    mode = world_graph_authority_mode()
    if mode != WORLD_GRAPH_AUTHORITY_DUNGEONMIND:
        raise WorldGraphAuthorityConfigurationError(
            f"mounted World Graph requires authority mode "
            f"{WORLD_GRAPH_AUTHORITY_DUNGEONMIND!r}; got {mode!r}"
        )
    if world_root is not None and Path(world_root).resolve() != world_graph_root().resolve():
        raise WorldGraphAuthorityConfigurationError(
            "mounted World Graph refuses alternate world_root; "
            "Buddy file-store selection is retired"
        )
