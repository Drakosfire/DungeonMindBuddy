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
    publish_world_graph_revision as _publish_world_graph_revision_storage,
    rollback_world_graph_head,
)
from graph_memory.world_supergraph import paths as world_paths
from graph_memory.world_supergraph.storage import (
    list_revision_ids,
    load_world_graph_revision_manifest,
)
from graph_memory.world_supergraph.identity_decision_store import (
    sync_identity_decisions_from_store,
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
    "find_world_graph_revisions_by_operation_id",
    "load_current_world_graph",
    "load_world_graph_revision",
    "load_world_graph_revision_manifest",
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


def publish_world_graph_revision(
    root: Path,
    world_id: str,
    graph: UnionSupergraphStore,
    operation_ids: list[str],
    expected_parent_revision_id: str | None = None,
) -> WorldGraphPublishResult:
    """Publish an immutable revision, advance head, and sync identity-decision ledger."""
    result = _publish_world_graph_revision_storage(
        root,
        world_id,
        graph,
        operation_ids=operation_ids,
        expected_parent_revision_id=expected_parent_revision_id,
    )
    # Allocate commit order immediately after durable publish succeeds and
    # before post-publish work / notification. Storage created_at drops
    # microseconds; this seq is the process-local newest-committed authority.
    from graph_memory.kernel.world_revision_ready import (
        allocate_revision_ready_commit_seq,
        offer_revision_ready_from_publish,
    )

    commit_seq = allocate_revision_ready_commit_seq()
    # Durable replay source for rebuild — independent of the current head.
    sync_identity_decisions_from_store(root, world_id, graph)
    # OPT02: best-effort process-local revision-ready signal after successful
    # durable publish + Kernel post-publish work. Never changes the result.
    try:
        offer_revision_ready_from_publish(
            root,
            world_id,
            result,
            commit_seq=commit_seq,
        )
    except Exception:
        # Final containment: head is already committed; notification must not
        # convert a successful publish into an exception.
        pass
    return result


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


def find_world_graph_revisions_by_operation_id(
    root: Path,
    world_id: str,
    operation_id: str,
) -> tuple[WorldGraphRevision, ...]:
    """Return every immutable revision manifest whose ``operation_ids`` contain ``operation_id``.

    Scans the complete revision store in one enumeration snapshot (independent of
    current head). Results are ordered by ``(created_at, revision_id)``. Performs
    no durable writes.

    Manifests whose embedded ``world_id`` or ``revision_id`` disagree with the store
    path used to load them fail closed with ``WorldGraphIntegrityError``.
    """
    world_paths.assert_safe_world_id(world_id)
    if not operation_id or not operation_id.strip():
        raise ValueError("operation_id must be non-empty")

    revision_ids = list_revision_ids(root, world_id)
    if not revision_ids:
        return ()

    matches: list[WorldGraphRevision] = []
    for revision_id in revision_ids:
        manifest = load_world_graph_revision_manifest(root, world_id, revision_id)
        if manifest.world_id != world_id or manifest.revision_id != revision_id:
            raise WorldGraphIntegrityError(
                "manifest identity mismatch for "
                f"world_id={world_id!r} revision_id={revision_id!r}: "
                f"manifest claims world_id={manifest.world_id!r} "
                f"revision_id={manifest.revision_id!r}"
            )
        if operation_id in manifest.operation_ids:
            matches.append(manifest)

    matches.sort(key=lambda manifest: (manifest.created_at, manifest.revision_id))
    return tuple(matches)
