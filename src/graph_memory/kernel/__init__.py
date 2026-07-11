"""Graph Kernel public boundary (PR003).

Runtime adapters and surfaces should import graph-memory operations from
``graph_memory.kernel`` only. Storage internals, preview loaders, and
latest-ingest selectors are not the legal production graph API.

Identity (PR004), contribution/merge (PR005), and projection (PR007) APIs are
reserved — see ``graph_memory.kernel.contracts``.
"""

from __future__ import annotations

from graph_memory.kernel.world_graph import (
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
    build_world_integrity_report,
    load_current_world_graph,
    load_world_graph_revision,
    open_current_world_graph,
    open_world_graph_head,
    publish_world_graph_revision,
    publish_world_revision,
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
