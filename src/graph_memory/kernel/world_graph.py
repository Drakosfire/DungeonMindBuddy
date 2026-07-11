"""Public Kernel facade for World SuperGraph head/revision operations.

Wraps PR002 ``graph_memory.world_supergraph`` storage without exposing
``storage`` / ``paths`` / ``integrity`` / ``model`` modules to application code.

Preview union loaders and latest-ingest selectors are not production graph
identity — they remain temporary until PR006–PR008.
"""

from __future__ import annotations

from pathlib import Path

from graph_memory.union_supergraph.model import UnionSupergraphStore
from graph_memory.world_supergraph import (
    WorldGraphError,
    WorldGraphHead,
    WorldGraphIntegrityError,
    WorldGraphIntegrityReport,
    WorldGraphNotFoundError,
    WorldGraphPublishResult,
    WorldGraphRevision,
    WorldGraphRevisionExistsError,
    WorldGraphStaleParentError,
    WorldGraphValidationError,
    build_world_graph_integrity_report,
    load_current_world_graph,
    load_world_graph_revision,
    open_world_graph_head,
    publish_world_graph_revision,
    rollback_world_graph_head,
)

__all__ = [
    "WorldGraphError",
    "WorldGraphHead",
    "WorldGraphIntegrityError",
    "WorldGraphIntegrityReport",
    "WorldGraphNotFoundError",
    "WorldGraphPublishResult",
    "WorldGraphRevision",
    "WorldGraphRevisionExistsError",
    "WorldGraphStaleParentError",
    "WorldGraphValidationError",
    "build_world_graph_integrity_report",
    "build_world_integrity_report",
    "load_current_world_graph",
    "load_world_graph_revision",
    "open_current_world_graph",
    "open_world_graph_head",
    "publish_world_graph_revision",
    "publish_world_revision",
    "rollback_world_graph_head",
]


def open_current_world_graph(
    root: Path, world_id: str
) -> tuple[WorldGraphHead, WorldGraphRevision, UnionSupergraphStore]:
    """Load the current world graph head + revision + payload (``root`` + ``world_id`` only)."""
    return load_current_world_graph(root, world_id)


def publish_world_revision(
    root: Path,
    world_id: str,
    graph: UnionSupergraphStore,
    operation_ids: list[str],
    expected_parent_revision_id: str | None = None,
) -> WorldGraphPublishResult:
    """Publish an immutable revision and advance the world graph head."""
    return publish_world_graph_revision(
        root,
        world_id,
        graph,
        operation_ids=operation_ids,
        expected_parent_revision_id=expected_parent_revision_id,
    )


def build_world_integrity_report(root: Path, world_id: str, *, persist: bool = True):
    """Build the machine-readable world graph integrity report."""
    return build_world_graph_integrity_report(root, world_id, persist=persist)
