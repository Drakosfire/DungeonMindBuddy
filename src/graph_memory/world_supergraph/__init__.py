"""World SuperGraph durable storage (PR002).

Public API for per-``worldId`` immutable revisions and an atomic graph head.

Preview union loaders and latest-ingest selectors are **not** production graph
identity. They remain temporary for Graph Review / live ingest until PR006–PR008.
"""

from __future__ import annotations

from graph_memory.world_supergraph.errors import (
    WorldGraphError,
    WorldGraphIntegrityError,
    WorldGraphNotFoundError,
    WorldGraphRevisionExistsError,
    WorldGraphStaleParentError,
    WorldGraphValidationError,
)
from graph_memory.world_supergraph.integrity import build_world_graph_integrity_report
from graph_memory.world_supergraph.model import (
    WorldGraphHead,
    WorldGraphIntegrityReport,
    WorldGraphPublishResult,
    WorldGraphRevision,
)
from graph_memory.world_supergraph.storage import (
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
    "load_current_world_graph",
    "load_world_graph_revision",
    "open_world_graph_head",
    "publish_world_graph_revision",
    "rollback_world_graph_head",
]
