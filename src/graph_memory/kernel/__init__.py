"""Graph Kernel public boundary (PR003+).

Runtime adapters and surfaces should import graph-memory operations from
``graph_memory.kernel`` only. Storage internals, preview loaders, and
latest-ingest selectors are not the legal production graph API.

Identity APIs (PR004) are exported below. Contribution/merge (PR005) and
projection (PR007) APIs remain reserved — see ``graph_memory.kernel.contracts``.
"""

from __future__ import annotations

from graph_memory.kernel.identity import (
    classify_identity_outcome,
    resolve_identity,
)
from graph_memory.kernel.identity_decisions import (
    build_identity_decision_record,
    compute_identity_decision_id,
    merge_identity,
    record_identity_decision,
    split_identity,
    unmerge_identity,
)
from graph_memory.kernel.identity_models import (
    IdentityCandidate,
    IdentityCanonState,
    IdentityDecisionKind,
    IdentityDecisionRecord,
    IdentityResolution,
    IdentityResolutionOutcome,
)
from graph_memory.kernel.identity_policy import (
    DEFAULT_IDENTITY_RESOLUTION_POLICY,
    IdentityResolutionPolicy,
)
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
    # World graph (PR002/PR003)
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
    # Identity (PR004)
    "IdentityCandidate",
    "IdentityCanonState",
    "IdentityDecisionKind",
    "IdentityDecisionRecord",
    "IdentityResolution",
    "IdentityResolutionOutcome",
    "IdentityResolutionPolicy",
    "DEFAULT_IDENTITY_RESOLUTION_POLICY",
    "build_identity_decision_record",
    "classify_identity_outcome",
    "compute_identity_decision_id",
    "merge_identity",
    "record_identity_decision",
    "resolve_identity",
    "split_identity",
    "unmerge_identity",
]
