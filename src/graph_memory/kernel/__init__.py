"""Graph Kernel public boundary (PR003+).

Runtime adapters and surfaces should import graph-memory operations from
``graph_memory.kernel`` only. Storage internals, preview loaders, and
latest-ingest selectors are not the legal production graph API.

Identity APIs (PR004) and contribution/merge APIs (PR005) are exported below.
Projection (PR007A) APIs are exported from ``graph_memory.kernel.world_projection``.
"""

from __future__ import annotations

from graph_memory.evidence.assertion_support import DurableAssertionSupport
from graph_memory.kernel.contribution_diagnostics import (
    build_contribution_integrity_report,
)
from graph_memory.kernel.contribution_merge import (
    merge_contribution_to_revision,
    retract_graph_contribution,
    supersede_graph_contribution,
)
from graph_memory.kernel.contribution_models import (
    ContributionAssertionStatus,
    ContributionIdentityMention,
    ContributionIntegrityReport,
    ContributionMergeResult,
    ContributionSourceKind,
    ContributionStatus,
    GraphContribution,
    GraphContributionAssertion,
)
from graph_memory.kernel.contribution_rebuild import rebuild_from_contributions
from graph_memory.kernel.contributions import (
    build_assertion,
    compute_assertion_id,
    compute_contribution_id,
    compute_contribution_payload_sha256,
    compute_contribution_source_payload_sha256,
    create_graph_contribution,
)
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
    IdentityAliasMapRewrite,
    IdentityMergeSideEffects,
    IdentityResolution,
    IdentityResolutionOutcome,
)
from graph_memory.kernel.identity_policy import (
    DEFAULT_IDENTITY_RESOLUTION_POLICY,
    IdentityResolutionPolicy,
)
from graph_memory.kernel.world_initialization import (
    build_empty_technical_baseline_store,
    compute_initialization_attestation_digest,
    compute_initialization_plan_digest,
    initialize_world_from_contributions,
    inspect_world_initialization_state,
    read_initialization_receipt,
)
from graph_memory.kernel.world_initialization_models import (
    WorldInitializationApprovalAttestation,
    WorldInitializationContribution,
    WorldInitializationError,
    WorldInitializationPlan,
    WorldInitializationReceipt,
    WorldInitializationResult,
)
from graph_memory.kernel.world_projection import (
    WorldGraphProjectionError,
    build_projection_payload,
    project_world_graph,
    resolve_projection_admissibility,
    search_world_graph_projection,
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
    # World initialization (PR006D1)
    "WorldInitializationApprovalAttestation",
    "WorldInitializationContribution",
    "WorldInitializationError",
    "WorldInitializationPlan",
    "WorldInitializationReceipt",
    "WorldInitializationResult",
    "build_empty_technical_baseline_store",
    "compute_contribution_payload_sha256",
    "compute_contribution_source_payload_sha256",
    "compute_initialization_attestation_digest",
    "compute_initialization_plan_digest",
    "initialize_world_from_contributions",
    "inspect_world_initialization_state",
    "read_initialization_receipt",
    # Identity (PR004)
    "IdentityCandidate",
    "IdentityCanonState",
    "IdentityDecisionKind",
    "IdentityDecisionRecord",
    "IdentityAliasMapRewrite",
    "IdentityMergeSideEffects",
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
    # Contributions (PR005)
    "ContributionAssertionStatus",
    "ContributionIdentityMention",
    "ContributionIntegrityReport",
    "ContributionMergeResult",
    "ContributionSourceKind",
    "ContributionStatus",
    "DurableAssertionSupport",
    "GraphContribution",
    "GraphContributionAssertion",
    "build_assertion",
    "build_contribution_integrity_report",
    "compute_assertion_id",
    "compute_contribution_id",
    "create_graph_contribution",
    "merge_contribution_to_revision",
    "rebuild_from_contributions",
    "retract_graph_contribution",
    "supersede_graph_contribution",
    # Projection (PR007A)
    "WorldGraphProjectionError",
    "build_projection_payload",
    "project_world_graph",
    "resolve_projection_admissibility",
    "search_world_graph_projection",
]
