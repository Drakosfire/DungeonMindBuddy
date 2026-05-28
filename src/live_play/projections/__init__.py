from __future__ import annotations

from typing import Any

from .capabilities import ProjectionCapability, ProjectionRiskLevel
from .commands import (
    ProjectionCommand,
    ProjectionCommandRequester,
    ProjectionCommandType,
    ProjectionEvidenceRef,
    ProjectionWriteLane,
)
from .invalidation import ProjectionInvalidation
from .targets import ProjectionSourceStatus, ProjectionTarget, ProjectionTargetType
from .write_results import (
    ProjectionConflict,
    ProjectionWriteResult,
    ProjectionWriteStatus,
)

__all__ = [
    "ProjectionCapability",
    "ProjectionCommand",
    "ProjectionCommandRequester",
    "ProjectionCommandType",
    "ProjectionConflict",
    "ProjectionEvidenceRef",
    "ProjectionInvalidation",
    "ProjectionRiskLevel",
    "ProjectionSourceStatus",
    "ProjectionTarget",
    "ProjectionTargetType",
    "ProjectionWriteLane",
    "ProjectionWriteResult",
    "ProjectionWriteStatus",
    "make_invalidation",
    "make_target",
]


def make_target(
    target_type: ProjectionTargetType,
    target_id: str,
    label: str,
    **metadata: Any,
) -> ProjectionTarget:
    return ProjectionTarget(
        target_type=target_type,
        target_id=target_id,
        label=label,
        metadata=metadata,
    )


def make_invalidation(
    projection_key: str,
    reason: str,
    target: ProjectionTarget | None = None,
) -> ProjectionInvalidation:
    return ProjectionInvalidation(
        projection_key=projection_key,
        target=target,
        reason=reason,
    )
