"""Reserved Graph Kernel APIs — intentionally incomplete.

PR004 identity APIs are implemented in ``graph_memory.kernel.identity`` /
``identity_decisions`` and exported from ``graph_memory.kernel``.

PR005 contribution/merge APIs are implemented in ``graph_memory.kernel``
contribution modules and exported from ``graph_memory.kernel``.

PR007 projection remains reserved. Callers must not treat reserved APIs as
working.

See also: ``Docs/Design/CONTRACT-graph-kernel-boundary.md``.
"""

from __future__ import annotations

from typing import Any, NoReturn

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

# --- Reserved for PR007 — projection ---

RESERVED_FOR_PR007_PROJECTION: tuple[str, ...] = (
    "project_world_graph",
    "build_projection_payload",
    "resolve_projection_admissibility",
)

ALL_RESERVED_KERNEL_APIS: tuple[str, ...] = RESERVED_FOR_PR007_PROJECTION


def _reserved(name: str, pr_slice: str) -> NoReturn:
    raise NotImplementedError(
        f"{name} is reserved for {pr_slice} and is not implemented yet"
    )


def project_world_graph(*_args: Any, **_kwargs: Any) -> NoReturn:
    _reserved("project_world_graph", "PR007 — projection")


def build_projection_payload(*_args: Any, **_kwargs: Any) -> NoReturn:
    _reserved("build_projection_payload", "PR007 — projection")


def resolve_projection_admissibility(*_args: Any, **_kwargs: Any) -> NoReturn:
    _reserved("resolve_projection_admissibility", "PR007 — projection")
