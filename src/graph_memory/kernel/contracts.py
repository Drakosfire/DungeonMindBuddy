"""Reserved Graph Kernel APIs — intentionally incomplete in PR003.

These names document the future Kernel surface. They are **not** available
implementations. Callers must not treat them as working APIs.

See also: ``Docs/Design/CONTRACT-graph-kernel-boundary.md``.
"""

from __future__ import annotations

from typing import Any, NoReturn

# --- Reserved for PR004 — identity ---

RESERVED_FOR_PR004_IDENTITY: tuple[str, ...] = (
    "resolve_identity",
    "record_identity_decision",
    "merge_identity",
    "split_identity",
    "unmerge_identity",
    "classify_identity_outcome",
)

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
    RESERVED_FOR_PR004_IDENTITY
    + RESERVED_FOR_PR005_CONTRIBUTION
    + RESERVED_FOR_PR007_PROJECTION
)


def _reserved(name: str, pr_slice: str) -> NoReturn:
    raise NotImplementedError(
        f"{name} is reserved for {pr_slice} and is not implemented in PR003"
    )


def resolve_identity(*_args: Any, **_kwargs: Any) -> NoReturn:
    _reserved("resolve_identity", "PR004 — identity")


def record_identity_decision(*_args: Any, **_kwargs: Any) -> NoReturn:
    _reserved("record_identity_decision", "PR004 — identity")


def merge_identity(*_args: Any, **_kwargs: Any) -> NoReturn:
    _reserved("merge_identity", "PR004 — identity")


def split_identity(*_args: Any, **_kwargs: Any) -> NoReturn:
    _reserved("split_identity", "PR004 — identity")


def unmerge_identity(*_args: Any, **_kwargs: Any) -> NoReturn:
    _reserved("unmerge_identity", "PR004 — identity")


def classify_identity_outcome(*_args: Any, **_kwargs: Any) -> NoReturn:
    _reserved("classify_identity_outcome", "PR004 — identity")


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
