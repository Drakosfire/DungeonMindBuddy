"""Path helpers for the file-backed World SuperGraph store (v0).

Layout::

    <root>/
      graph_memory/
        worlds/
          <worldId>/
            head.json
            revisions/
              <revisionId>/
                graph.json
                revision.json
            integrity/
              latest.json

``root`` is caller-provided (repo runtime root or a test temp dir). Opening a
world graph requires only ``root`` + ``world_id`` — never a preview source,
ingest run id, session id, manifest path, or explicit store path selector.
"""

from __future__ import annotations

import re
from pathlib import Path

_WORLD_ID_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]{0,127}$")
_REVISION_ID_RE = re.compile(r"^rev:[a-f0-9]{16,64}$")


def assert_safe_world_id(world_id: str) -> str:
    if not _WORLD_ID_RE.fullmatch(world_id):
        raise ValueError(f"invalid world_id: {world_id!r}")
    return world_id


def assert_safe_revision_id(revision_id: str) -> str:
    if not _REVISION_ID_RE.fullmatch(revision_id):
        raise ValueError(f"invalid revision_id: {revision_id!r}")
    return revision_id


def worlds_root(root: Path) -> Path:
    return root / "graph_memory" / "worlds"


def world_dir(root: Path, world_id: str) -> Path:
    return worlds_root(root) / assert_safe_world_id(world_id)


def head_path(root: Path, world_id: str) -> Path:
    return world_dir(root, world_id) / "head.json"


def write_lock_path(root: Path, world_id: str) -> Path:
    """Per-world exclusive lock file for publish / rollback critical sections."""
    return world_dir(root, world_id) / ".write.lock"


def revisions_dir(root: Path, world_id: str) -> Path:
    return world_dir(root, world_id) / "revisions"


def revision_dir(root: Path, world_id: str, revision_id: str) -> Path:
    return revisions_dir(root, world_id) / assert_safe_revision_id(revision_id)


def graph_payload_path(root: Path, world_id: str, revision_id: str) -> Path:
    return revision_dir(root, world_id, revision_id) / "graph.json"


def revision_manifest_path(root: Path, world_id: str, revision_id: str) -> Path:
    return revision_dir(root, world_id, revision_id) / "revision.json"


def integrity_dir(root: Path, world_id: str) -> Path:
    return world_dir(root, world_id) / "integrity"


def integrity_latest_path(root: Path, world_id: str) -> Path:
    return integrity_dir(root, world_id) / "latest.json"


def relative_graph_payload_path(revision_id: str) -> str:
    """Path relative to the world directory for revision metadata."""
    assert_safe_revision_id(revision_id)
    return f"revisions/{revision_id}/graph.json"
