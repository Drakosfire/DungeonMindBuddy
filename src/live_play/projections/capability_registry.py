from __future__ import annotations

from pydantic import BaseModel, Field

from src.live_play.projections.capabilities import ProjectionCapability
from src.live_play.projections.targets import ProjectionTarget

DISABLED_REASON = "Not implemented in PR85."


class CapabilityReadResponse(BaseModel):
    schema_version: str = "0.1.0"
    target: ProjectionTarget
    capabilities: list[ProjectionCapability] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)


def capabilities_for_target(target: ProjectionTarget) -> list[ProjectionCapability]:
    if target.target_type == "event":
        return [
            ProjectionCapability(
                command_type="queue_canon_patch",
                label="Queue canon patch",
                lane="canon_patch",
                enabled=False,
                disabled_reason=DISABLED_REASON,
            ),
            ProjectionCapability(
                command_type="append_observation",
                label="Append observation",
                lane="observed_play",
                enabled=True,
                required_fields=["observation"],
                risk_level="low",
                disabled_reason=None,
                metadata={"supported_in_pr": 85},
            ),
        ]
    if target.target_type == "roll_table":
        return [
            ProjectionCapability(
                command_type="patch_artifact",
                label="Patch artifact",
                lane="prep_note",
                enabled=True,
                required_fields=["expected_file_state_token", "old_text", "new_text"],
                risk_level="medium",
                disabled_reason=None,
                metadata={
                    "supported_in_pr": 87,
                    "patch_kind": "replace_text",
                    "requires_file_state_token": True,
                    "supports_dry_run": True,
                },
            ),
            ProjectionCapability(
                command_type="append_observation",
                label="Append observation",
                lane="observed_play",
                enabled=True,
                required_fields=["observation"],
                risk_level="low",
                disabled_reason=None,
                metadata={"supported_in_pr": 85},
            ),
        ]
    return []


def build_capability_response(target: ProjectionTarget) -> CapabilityReadResponse:
    return CapabilityReadResponse(
        target=target,
        capabilities=capabilities_for_target(target),
        metadata={"read_only": True},
    )
