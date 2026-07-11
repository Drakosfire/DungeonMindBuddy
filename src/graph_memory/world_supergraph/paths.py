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
            contributions/
              <contribution_id>.json
            contribution_index.json
            contribution_rebuild/
              latest.json
            identity_decisions/
              <decision_id>.json
            identity_decision_index.json

``root`` is caller-provided (repo runtime root or a test temp dir). Opening a
world graph requires only ``root`` + ``world_id`` — never a preview source,
ingest run id, session id, manifest path, or explicit store path selector.

Contribution ledger and identity-decision ledger paths (PR005) are internal to
world_supergraph; apps must use ``graph_memory.kernel`` APIs, not these helpers.
"""

from __future__ import annotations

import re
from pathlib import Path

_WORLD_ID_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]{0,127}$")
_REVISION_ID_RE = re.compile(r"^rev:[a-f0-9]{16,64}$")
_IDENTITY_DECISION_ID_RE = re.compile(r"^identity-decision:[a-f0-9]{8,64}$")


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


_CONTRIBUTION_ID_RE = re.compile(r"^contribution:[a-f0-9]{8,64}$")


def assert_safe_contribution_id(contribution_id: str) -> str:
    if not _CONTRIBUTION_ID_RE.fullmatch(contribution_id):
        raise ValueError(f"invalid contribution_id: {contribution_id!r}")
    return contribution_id


def contributions_dir(root: Path, world_id: str) -> Path:
    return world_dir(root, world_id) / "contributions"


def contribution_path(root: Path, world_id: str, contribution_id: str) -> Path:
    safe_id = assert_safe_contribution_id(contribution_id)
    # Filesystem-safe filename: replace ':' with '__'.
    return contributions_dir(root, world_id) / f"{safe_id.replace(':', '__')}.json"


def contribution_index_path(root: Path, world_id: str) -> Path:
    return world_dir(root, world_id) / "contribution_index.json"


def contribution_rebuild_dir(root: Path, world_id: str) -> Path:
    return world_dir(root, world_id) / "contribution_rebuild"


def contribution_rebuild_latest_path(root: Path, world_id: str) -> Path:
    return contribution_rebuild_dir(root, world_id) / "latest.json"


def assert_safe_identity_decision_id(decision_id: str) -> str:
    if not _IDENTITY_DECISION_ID_RE.fullmatch(decision_id):
        raise ValueError(f"invalid identity decision_id: {decision_id!r}")
    return decision_id


def identity_decisions_dir(root: Path, world_id: str) -> Path:
    return world_dir(root, world_id) / "identity_decisions"


def identity_decision_path(root: Path, world_id: str, decision_id: str) -> Path:
    safe_id = assert_safe_identity_decision_id(decision_id)
    return identity_decisions_dir(root, world_id) / f"{safe_id.replace(':', '__')}.json"


def identity_decision_index_path(root: Path, world_id: str) -> Path:
    return world_dir(root, world_id) / "identity_decision_index.json"
