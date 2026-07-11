"""Reserved Graph Kernel APIs — intentionally incomplete.

PR004 identity APIs are implemented in ``graph_memory.kernel.identity`` /
``identity_decisions`` and exported from ``graph_memory.kernel``.

PR005 contribution/merge and PR007 projection remain reserved placeholders.
Callers must not treat them as working APIs.

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

# --- Reserved for PR005 — contribution / merge ---

RESERVED_FOR_PR005_CONTRIBUTION: tuple[str, ...] = (
    "create_graph_contribution",
    "supersede_graph_contribution",
    "retract_graph_contribution",
    "merge_contribution_to_revision",
    "rebuild_from_contributions",
)

# --- Reserved for PR007 — projection ---

RESERVED_FOR_PR007_PROJECTION: tuple[str, ...] = (
    "project_world_graph",
    "build_projection_payload",
    "resolve_projection_admissibility",
)

ALL_RESERVED_KERNEL_APIS: tuple[str, ...] = (
    RESERVED_FOR_PR005_CONTRIBUTION + RESERVED_FOR_PR007_PROJECTION
)


def _reserved(name: str, pr_slice: str) -> NoReturn:
    raise NotImplementedError(
        f"{name} is reserved for {pr_slice} and is not implemented yet"
    )


def create_graph_contribution(*_args: Any, **_kwargs: Any) -> NoReturn:
    _reserved("create_graph_contribution", "PR005 — contribution / merge")


def supersede_graph_contribution(*_args: Any, **_kwargs: Any) -> NoReturn:
    _reserved("supersede_graph_contribution", "PR005 — contribution / merge")


def retract_graph_contribution(*_args: Any, **_kwargs: Any) -> NoReturn:
    _reserved("retract_graph_contribution", "PR005 — contribution / merge")


def merge_contribution_to_revision(*_args: Any, **_kwargs: Any) -> NoReturn:
    _reserved("merge_contribution_to_revision", "PR005 — contribution / merge")


def rebuild_from_contributions(*_args: Any, **_kwargs: Any) -> NoReturn:
    _reserved("rebuild_from_contributions", "PR005 — contribution / merge")


def project_world_graph(*_args: Any, **_kwargs: Any) -> NoReturn:
    _reserved("project_world_graph", "PR007 — projection")


def build_projection_payload(*_args: Any, **_kwargs: Any) -> NoReturn:
    _reserved("build_projection_payload", "PR007 — projection")


def resolve_projection_admissibility(*_args: Any, **_kwargs: Any) -> NoReturn:
    _reserved("resolve_projection_admissibility", "PR007 — projection")
