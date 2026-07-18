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
