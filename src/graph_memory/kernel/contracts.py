"""Reserved Graph Kernel APIs — intentionally incomplete.

PR004 identity APIs are implemented in ``graph_memory.kernel.identity`` /
``identity_decisions`` and exported from ``graph_memory.kernel``.

PR005 contribution/merge APIs are implemented in ``graph_memory.kernel``
contribution modules and exported from ``graph_memory.kernel``.

PR007 projection APIs are implemented in ``graph_memory.kernel.world_projection``
and exported from ``graph_memory.kernel``.

See also: ``Docs/Design/CONTRACT-graph-kernel-boundary.md``.
"""

from __future__ import annotations

# --- Implemented in PR004 — identity (exported from graph_memory.kernel) ---

IMPLEMENTED_IN_PR004_IDENTITY: tuple[str, ...] = (
    "resolve_identity",
    "record_identity_decision",
    "merge_identity",
    "split_identity",
    "unmerge_identity",
    "classify_identity_outcome",
)

# Kept for older references; empty — identity is no longer reserved.
RESERVED_FOR_PR004_IDENTITY: tuple[str, ...] = ()

# --- Implemented in PR005 — contribution / merge ---

IMPLEMENTED_IN_PR005_CONTRIBUTION: tuple[str, ...] = (
    "create_graph_contribution",
    "supersede_graph_contribution",
    "retract_graph_contribution",
    "merge_contribution_to_revision",
    "rebuild_from_contributions",
    "build_contribution_integrity_report",
)

# Kept for older references; empty — contribution APIs are no longer reserved.
RESERVED_FOR_PR005_CONTRIBUTION: tuple[str, ...] = ()

# --- Implemented in PR007A — projection ---

IMPLEMENTED_IN_PR007_PROJECTION: tuple[str, ...] = (
    "project_world_graph",
    "build_projection_payload",
    "resolve_projection_admissibility",
    "search_world_graph_projection",
)

# Kept for older references; empty — projection APIs are no longer reserved.
RESERVED_FOR_PR007_PROJECTION: tuple[str, ...] = ()

ALL_RESERVED_KERNEL_APIS: tuple[str, ...] = ()
