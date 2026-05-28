from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.live_play import projections
from src.live_play.projections import (
    ProjectionCapability,
    ProjectionCommand,
    ProjectionCommandRequester,
    ProjectionConflict,
    ProjectionInvalidation,
    ProjectionTarget,
    ProjectionWriteResult,
)


def _target() -> ProjectionTarget:
    return ProjectionTarget(
        target_type="roll_table",
        target_id="T-WX",
        label="Storm weather",
    )


def test_projection_target_validates_known_target_type() -> None:
    target = _target()
    assert target.target_type == "roll_table"
    assert target.metadata == {}


def test_projection_target_rejects_unknown_target_type() -> None:
    with pytest.raises(ValidationError):
        ProjectionTarget(
            target_type="mystery",  # type: ignore[arg-type]
            target_id="id",
            label="Label",
        )


def test_projection_capability_serializes_enabled_and_disabled() -> None:
    enabled = ProjectionCapability(
        command_type="patch_artifact",
        label="Patch roll table",
        lane="prep_note",
    )
    disabled = ProjectionCapability(
        command_type="patch_artifact",
        label="Patch roll table",
        lane="prep_note",
        enabled=False,
        disabled_reason="Readonly mode",
    )
    assert enabled.model_dump(mode="json")["enabled"] is True
    assert disabled.model_dump(mode="json")["disabled_reason"] == "Readonly mode"


def test_projection_command_requires_lane_target_requester_and_valid_type() -> None:
    with pytest.raises(ValidationError):
        ProjectionCommand.model_validate(
            {
                "command_type": "append_observation",
                "target": _target().model_dump(mode="json"),
                "requested_by": {"requester_type": "human_ui"},
            }
        )
    with pytest.raises(ValidationError):
        ProjectionCommand.model_validate(
            {
                "command_type": "not_a_real_command",
                "lane": "observed_play",
                "target": _target().model_dump(mode="json"),
                "requested_by": {"requester_type": "human_ui"},
            }
        )


def test_projection_command_supports_human_ui_and_agent_requesters() -> None:
    human = ProjectionCommand(
        command_type="append_observation",
        lane="observed_play",
        target=_target(),
        requested_by=ProjectionCommandRequester(requester_type="human_ui", requester_id="gm-1"),
    )
    agent = ProjectionCommand(
        command_type="request_retrieval_refresh",
        lane="retrieval_curation",
        target=_target(),
        requested_by=ProjectionCommandRequester(requester_type="agent", requester_id="planner"),
    )
    assert human.requested_by.requester_type == "human_ui"
    assert agent.requested_by.requester_type == "agent"


def test_projection_invalidation_requires_projection_key_and_reason() -> None:
    with pytest.raises(ValidationError):
        ProjectionInvalidation(projection_key="", reason="refresh")
    with pytest.raises(ValidationError):
        ProjectionInvalidation(projection_key="plan_view", reason="")


def test_projection_write_result_accepts_events_jobs_and_invalidations() -> None:
    result = ProjectionWriteResult(
        write_id="wr-1",
        status="accepted",
        events_appended=["evt-live-1"],
        jobs_queued=["job-1"],
        invalidations=[ProjectionInvalidation(projection_key="plan_view", reason="write accepted")],
    )
    assert result.status == "accepted"
    assert result.events_appended == ["evt-live-1"]
    assert result.jobs_queued == ["job-1"]
    assert result.invalidations[0].projection_key == "plan_view"


def test_projection_write_result_can_represent_conflict() -> None:
    result = ProjectionWriteResult(
        write_id="wr-2",
        status="conflict",
        conflicts=[
            ProjectionConflict(
                conflict_type="stale_token",
                message="Expected token mismatch",
                target=_target(),
            )
        ],
    )
    assert result.status == "conflict"
    assert result.conflicts[0].conflict_type == "stale_token"


def test_defaults_are_not_shared_mutable_instances() -> None:
    first = ProjectionWriteResult(write_id="wr-a", status="noop")
    second = ProjectionWriteResult(write_id="wr-b", status="noop")
    first.events_appended.append("evt-x")
    assert second.events_appended == []


def test_json_roundtrip_for_contract_models() -> None:
    command = ProjectionCommand(
        command_type="update_layout",
        lane="layout_config",
        target=_target(),
        requested_by=ProjectionCommandRequester(requester_type="human_ui", requester_id="gm-2"),
    )
    result = ProjectionWriteResult(
        write_id="wr-3",
        status="accepted",
        artifacts_changed=[command.target],
        invalidations=[
            ProjectionInvalidation(
                projection_key="surface_layout",
                reason="layout updated",
                target=command.target,
            )
        ],
    )
    payload = {
        "target": command.target.model_dump(mode="json"),
        "capability": ProjectionCapability(
            command_type="update_layout",
            label="Move module",
            lane="layout_config",
        ).model_dump(mode="json"),
        "command": command.model_dump(mode="json"),
        "invalidation": result.invalidations[0].model_dump(mode="json"),
        "result": result.model_dump(mode="json"),
    }
    ProjectionTarget.model_validate(payload["target"])
    ProjectionCapability.model_validate(payload["capability"])
    ProjectionCommand.model_validate(payload["command"])
    ProjectionInvalidation.model_validate(payload["invalidation"])
    ProjectionWriteResult.model_validate(payload["result"])


def test_public_imports_expose_primary_contract_classes() -> None:
    assert projections.ProjectionTarget is ProjectionTarget
    assert projections.ProjectionCapability is ProjectionCapability
    assert projections.ProjectionCommand is ProjectionCommand
    assert projections.ProjectionInvalidation is ProjectionInvalidation
    assert projections.ProjectionWriteResult is ProjectionWriteResult


@pytest.mark.parametrize(
    "factory",
    [
        lambda: ProjectionTarget(target_type="event", target_id="", label="x"),
        lambda: ProjectionTarget(target_type="event", target_id="evt-1", label=""),
        lambda: ProjectionInvalidation(projection_key="", reason="refresh"),
        lambda: ProjectionInvalidation(projection_key="plan_view", reason=""),
        lambda: ProjectionWriteResult(write_id="", status="noop"),
    ],
)
def test_blank_string_required_fields_are_rejected(factory) -> None:
    with pytest.raises(ValidationError):
        factory()
