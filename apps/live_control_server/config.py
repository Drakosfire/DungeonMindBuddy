from __future__ import annotations

import os
from pathlib import Path

SESSION_DIR_ENV = "DUNGEONMIND_LIVE_SESSION_DIR"
WORLD_GRAPH_ROOT_ENV = "DUNGEONMIND_WORLD_GRAPH_ROOT"


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
