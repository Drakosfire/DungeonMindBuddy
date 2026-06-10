from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from src.statblocks.lifecycle_artifact import (
    StatblockBreadcrumb,
    StatblockDraftArtifact,
)
from src.statblocks.lifecycle_commands import (
    STATBLOCK_DRAFT_GENERATE,
    STATBLOCK_DRAFT_RENDER,
)
from src.statblocks.lifecycle_service import (
    StatblockLifecycleCommandRequest,
    StatblockLifecycleService,
)
from src.statblocks.v2_client import MockStatBlockGeneratorProvider
from src.statblocks.v2_contract import StatBlockDraftResponse


class StatblockWorkbenchAction(BaseModel):
    action_id: str
    label: str
    enabled: bool = False
    disabled_reason: str | None = None


class StatblockWorkbenchSampleResponse(BaseModel):
    schema_version: Literal["dmb_statblock_workbench_sample_v1"] = (
        "dmb_statblock_workbench_sample_v1"
    )
    mode: Literal["sample_mock"] = "sample_mock"
    artifact: StatblockDraftArtifact
    command_status: str
    diagnostics: list[str] = Field(default_factory=list)
    available_actions: list[StatblockWorkbenchAction] = Field(default_factory=list)


class StatblockWorkbenchCommandRequest(BaseModel):
    command_type: Literal[
        "statblock.draft.generate",
        "statblock.draft.render",
    ]
    payload: dict[str, Any] = Field(default_factory=dict)
    requested_by: Literal["human", "agent", "planning_task", "combat_task"] = "human"
    breadcrumbs: list[StatblockBreadcrumb] = Field(default_factory=list)
    as_artifact: bool = True


class StatblockWorkbenchCommandResponse(BaseModel):
    schema_version: Literal["dmb_statblock_workbench_command_v1"] = (
        "dmb_statblock_workbench_command_v1"
    )
    mode: Literal["mock_command"] = "mock_command"
    artifact: StatblockDraftArtifact | None = None
    command_status: str
    diagnostics: list[str] = Field(default_factory=list)
    available_actions: list[StatblockWorkbenchAction] = Field(default_factory=list)
    error: dict[str, Any] | None = None


def build_statblock_workbench_sample_response() -> StatblockWorkbenchSampleResponse:
    service = StatblockLifecycleService(
        MockStatBlockGeneratorProvider(
            generate_response=_statblock_workbench_sample_draft_response()
        )
    )
    result = service.execute(_statblock_workbench_sample_command())
    if result.artifact is None:
        msg = "mock statblock lifecycle command did not produce a draft artifact"
        raise RuntimeError(msg)
    return StatblockWorkbenchSampleResponse(
        artifact=result.artifact,
        command_status=result.status,
        diagnostics=[
            "sample endpoint uses MockStatBlockGeneratorProvider only",
            "artifact is read-only and not persisted",
            *result.diagnostics,
        ],
        available_actions=_statblock_workbench_future_actions(),
    )


def execute_statblock_workbench_command(
    body: StatblockWorkbenchCommandRequest,
) -> StatblockWorkbenchCommandResponse:
    service = StatblockLifecycleService(
        MockStatBlockGeneratorProvider(
            generate_response=_statblock_workbench_generate_draft_response(),
            render_response=_statblock_workbench_render_draft_response(),
        )
    )
    command_request = StatblockLifecycleCommandRequest(
        command_type=body.command_type,
        requested_by=body.requested_by,
        breadcrumbs=[
            *body.breadcrumbs,
            StatblockBreadcrumb(
                label="surface:statblock_workbench", source="live_control"
            ),
            StatblockBreadcrumb(label="source:mock_provider", source="mock_provider"),
            StatblockBreadcrumb(label=f"command:{body.command_type}", source="mock_provider"),
        ],
        payload=body.payload or _default_workbench_command_payload(body.command_type),
        as_artifact=body.as_artifact,
    )
    result = service.execute(command_request)
    diagnostics = [
        "command endpoint uses MockStatBlockGeneratorProvider only",
        "artifact is mock-backed and non-persistent",
        "no corpus write, Semantic Knowledge Layer ingestion, or combat mutation occurred",
        *result.diagnostics,
    ]
    if result.artifact is not None:
        return StatblockWorkbenchCommandResponse(
            artifact=result.artifact,
            command_status=result.status,
            diagnostics=diagnostics,
            available_actions=_statblock_workbench_future_actions(),
        )

    error = (
        result.error.model_dump(mode="json")
        if result.error is not None
        else {
            "code": "missing_artifact",
            "message": "statblock lifecycle command did not produce a draft artifact",
        }
    )
    return StatblockWorkbenchCommandResponse(
        artifact=None,
        command_status=result.status,
        diagnostics=diagnostics,
        available_actions=_statblock_workbench_future_actions(),
        error=error,
    )


def _statblock_workbench_future_actions() -> list[StatblockWorkbenchAction]:
    future_pr_reason = (
        "Disabled in PR3: future lifecycle PR will make this action durable."
    )
    return [
        StatblockWorkbenchAction(
            action_id="store_draft",
            label="Store draft",
            disabled_reason=future_pr_reason,
        ),
        StatblockWorkbenchAction(
            action_id="preview_corpus_promotion",
            label="Preview corpus promotion",
            disabled_reason=future_pr_reason,
        ),
        StatblockWorkbenchAction(
            action_id="promote_to_corpus",
            label="Promote to corpus",
            disabled_reason=future_pr_reason,
        ),
        StatblockWorkbenchAction(
            action_id="ingest_to_semantic_layer",
            label="Ingest to Semantic Knowledge Layer",
            disabled_reason=future_pr_reason,
        ),
        StatblockWorkbenchAction(
            action_id="add_to_combat",
            label="Add to combat",
            disabled_reason=future_pr_reason,
        ),
    ]


def _statblock_workbench_sample_draft_response() -> StatBlockDraftResponse:
    return StatBlockDraftResponse.model_validate(
        {
            "success": True,
            "draft": {
                "draft_id": "mock-generated-draft",
                "lifecycle_state": "live_draft",
                "review_status": "needs_dm_review",
                "markdown": (
                    "## Geomantic Drake Juvenile\n"
                    "*Medium dragon, unaligned*\n\n"
                    "**Armor Class** 15 (natural armor)\n"
                    "**Hit Points** 68 (8d8 + 32)\n"
                    "**Speed** 30 ft., burrow 10 ft.\n\n"
                    "### Actions\n"
                    "**Bite.** Melee Weapon Attack: +5 to hit, one target.\n\n"
                    "**Stone Skitter.** The drake shifts loose earth around one creature."
                ),
                "statblock": {
                    "name": "Geomantic Drake Juvenile",
                    "size": "Medium",
                    "type": "dragon",
                    "challenge_rating": "3",
                },
                "combat_defaults": {
                    "name": "Geomantic Drake Juvenile",
                    "armor_class": 15,
                    "hit_points": 68,
                    "initiative_bonus": 2,
                    "passive_perception": 13,
                    "speed_summary": "30 ft., burrow 10 ft.",
                    "senses_summary": "darkvision 60 ft., passive Perception 13",
                    "primary_actions": ["Bite", "Stone Skitter"],
                    "suggested_tactics": [
                        "Open from partial cover in broken stone.",
                        "Use burrow movement to pressure isolated backline targets.",
                    ],
                },
                "warnings": [
                    {
                        "code": "sample_needs_dm_review",
                        "message": "Review damage math and terrain effect wording before table use.",
                        "severity": "warning",
                        "path": "actions",
                    }
                ],
                "provenance": {
                    "request_id": "live-control-statblock-workbench-sample",
                    "mode": "generate_from_prompt",
                    "generator": "mock-statblock-generator",
                    "generated_at": "2026-06-09T00:00:00Z",
                    "source_refs": [
                        {
                            "id": "sample-source-geomantic-drake",
                            "kind": "corpus_note",
                            "label": "Geomantic drake juvenile statblock seed",
                            "path": "corpus/eldyrwild-markdown/Elderwyld/Wilderness/geomantic_drake_juvenile_statblock.md",
                            "reason": "Sample provenance only; not read or written by endpoint.",
                        }
                    ],
                    "generation_info": {
                        "sample": True,
                        "provider": "MockStatBlockGeneratorProvider",
                    },
                },
            },
            "timestamp": "2026-06-09T00:00:00Z",
        }
    )


def _statblock_workbench_sample_command() -> StatblockLifecycleCommandRequest:
    return StatblockLifecycleCommandRequest(
        command_type=STATBLOCK_DRAFT_GENERATE,
        requested_by="agent",
        breadcrumbs=[
            StatblockBreadcrumb(label="campaign:c2", source="sample_fixture"),
            StatblockBreadcrumb(label="session:23", source="sample_fixture"),
            StatblockBreadcrumb(
                label="surface:statblock_workbench", source="live_control"
            ),
            StatblockBreadcrumb(label="source:mock_provider", source="mock_provider"),
        ],
        payload={
            "request_id": "live-control-statblock-workbench-sample",
            "mode": "generate_from_prompt",
            "prompt": (
                "Create a combat-ready Elderwyld geomantic drake juvenile draft "
                "for read-only Workbench review."
            ),
            "intent": {
                "mode": "generate_from_prompt",
                "creature_name": "Geomantic Drake Juvenile",
                "challenge_rating": "3",
                "role": "skirmisher",
                "tone": "Elderwyld wilderness hazard",
            },
            "encounter_context": {
                "party_level": 5,
                "party_size": 4,
                "encounter_role": "mobile terrain-pressure threat",
                "environment": "conical hills night camp",
                "constraints": [
                    "show as sample only",
                    "do not persist",
                    "do not add to combat",
                ],
            },
            "source_refs": [
                {
                    "id": "sample-source-geomantic-drake",
                    "kind": "corpus_note",
                    "label": "Geomantic drake juvenile statblock seed",
                    "path": "corpus/eldyrwild-markdown/Elderwyld/Wilderness/geomantic_drake_juvenile_statblock.md",
                    "reason": "Sample provenance only; not read or written by endpoint.",
                }
            ],
            "output_options": {
                "include_markdown": True,
                "include_json": True,
                "include_combat_defaults": True,
                "include_review_warnings": True,
                "persist": False,
                "style": "live-control-workbench-sample",
            },
        },
    )


def _statblock_workbench_generate_draft_response() -> StatBlockDraftResponse:
    return StatBlockDraftResponse.model_validate(
        {
            "success": True,
            "draft": {
                "draft_id": "mock-generated-obsidian-thornling",
                "lifecycle_state": "live_draft",
                "review_status": "needs_dm_review",
                "markdown": (
                    "## Generated Obsidian Thornling\n"
                    "*Small plant, unaligned*\n\n"
                    "**Armor Class** 14 (glassy bark)\n"
                    "**Hit Points** 45 (10d6 + 10)\n"
                    "**Speed** 35 ft., climb 20 ft.\n\n"
                    "### Actions\n"
                    "**Splinter Thorn.** Ranged Weapon Attack: +6 to hit, one target.\n\n"
                    "**Root Snare.** The thornling lashes obsidian roots around a creature."
                ),
                "statblock": {
                    "name": "Generated Obsidian Thornling",
                    "size": "Small",
                    "type": "plant",
                    "challenge_rating": "2",
                },
                "combat_defaults": {
                    "name": "Generated Obsidian Thornling",
                    "armor_class": 14,
                    "hit_points": 45,
                    "initiative_bonus": 3,
                    "passive_perception": 12,
                    "speed_summary": "35 ft., climb 20 ft.",
                    "senses_summary": "tremorsense 30 ft., passive Perception 12",
                    "primary_actions": ["Splinter Thorn", "Root Snare"],
                    "suggested_tactics": [
                        "Skirmish from bramble cover and retreat up ruined stone.",
                        "Use Root Snare to hold a target inside hazardous undergrowth.",
                    ],
                },
                "warnings": [
                    {
                        "code": "generated_mock_needs_dm_review",
                        "message": "Review root restraint wording before table use.",
                        "severity": "warning",
                        "path": "actions.root_snare",
                    }
                ],
                "provenance": {
                    "request_id": "live-control-statblock-workbench-generate",
                    "mode": "generate_from_prompt",
                    "generator": "mock-statblock-generator",
                    "generated_at": "2026-06-09T00:00:00Z",
                    "source_refs": [
                        {
                            "id": "sample-source-obsidian-thornling",
                            "kind": "prompt_seed",
                            "label": "Obsidian thornling generated mock prompt",
                            "path": "workbench/mock/generate-prompt",
                            "reason": "Mock generate provenance only; not read or written by endpoint.",
                        }
                    ],
                    "generation_info": {
                        "generated": True,
                        "sample": True,
                        "provider": "MockStatBlockGeneratorProvider",
                    },
                },
            },
            "timestamp": "2026-06-09T00:00:00Z",
        }
    )


def _statblock_workbench_render_draft_response() -> StatBlockDraftResponse:
    return StatBlockDraftResponse.model_validate(
        {
            "success": True,
            "draft": {
                "draft_id": "mock-rendered-clockwork-mire-sentinel",
                "lifecycle_state": "live_draft",
                "review_status": "needs_dm_review",
                "markdown": (
                    "## Rendered Clockwork Mire Sentinel\n"
                    "*Large construct, unaligned*\n\n"
                    "**Armor Class** 17 (plated reeds)\n"
                    "**Hit Points** 95 (10d10 + 40)\n"
                    "**Speed** 25 ft., swim 20 ft.\n\n"
                    "### Actions\n"
                    "**Gearhook Slam.** Melee Weapon Attack: +7 to hit, one target.\n\n"
                    "**Bog Vent.** The sentinel vents scalding mist in a 15-foot cone."
                ),
                "statblock": {
                    "name": "Rendered Clockwork Mire Sentinel",
                    "size": "Large",
                    "type": "construct",
                    "challenge_rating": "5",
                },
                "combat_defaults": {
                    "name": "Rendered Clockwork Mire Sentinel",
                    "armor_class": 17,
                    "hit_points": 95,
                    "initiative_bonus": 0,
                    "passive_perception": 12,
                    "speed_summary": "25 ft., swim 20 ft.",
                    "senses_summary": "blindsight 30 ft., passive Perception 12",
                    "primary_actions": ["Gearhook Slam", "Bog Vent"],
                    "suggested_tactics": [
                        "Anchor a flooded choke point and punish clustered movement.",
                        "Use Bog Vent after grappling a front-line defender.",
                    ],
                },
                "warnings": [
                    {
                        "code": "rendered_mock_needs_dm_review",
                        "message": "Validate rendered recharge cadence before durable storage.",
                        "severity": "warning",
                        "path": "actions.bog_vent",
                    }
                ],
                "provenance": {
                    "request_id": "live-control-statblock-workbench-render",
                    "mode": "render_existing",
                    "generator": "mock-statblock-generator",
                    "generated_at": "2026-06-09T00:00:00Z",
                    "source_refs": [
                        {
                            "id": "sample-source-clockwork-mire-sentinel",
                            "kind": "render_source",
                            "label": "Clockwork mire sentinel render input",
                            "path": "workbench/mock/render-input",
                            "reason": "Mock render provenance only; not read or written by endpoint.",
                        }
                    ],
                    "generation_info": {
                        "generated": False,
                        "sample": True,
                        "provider": "MockStatBlockGeneratorProvider",
                    },
                },
            },
            "timestamp": "2026-06-09T00:00:00Z",
        }
    )


def _default_workbench_command_payload(command_type: str) -> dict[str, Any]:
    if command_type == STATBLOCK_DRAFT_RENDER:
        return {
            "request_id": "live-control-statblock-workbench-render",
            "mode": "render_existing",
            "statblock": {
                "name": "Rendered Clockwork Mire Sentinel",
                "size": "Large",
                "type": "construct",
                "challenge_rating": "5",
            },
            "output_options": {
                "include_markdown": True,
                "include_json": True,
                "include_combat_defaults": True,
                "include_review_warnings": True,
                "persist": False,
                "style": "live-control-workbench-command-render",
            },
            "source_refs": [
                {
                    "id": "sample-source-clockwork-mire-sentinel",
                    "kind": "render_source",
                    "label": "Clockwork mire sentinel render input",
                    "path": "workbench/mock/render-input",
                    "reason": "Mock render provenance only; not read or written by endpoint.",
                }
            ],
        }
    return {
        "request_id": "live-control-statblock-workbench-generate",
        "mode": "generate_from_prompt",
        "prompt": (
            "Create a combat-ready obsidian thornling draft for interactive "
            "mock Workbench review."
        ),
        "intent": {
            "mode": "generate_from_prompt",
            "creature_name": "Generated Obsidian Thornling",
            "challenge_rating": "2",
            "role": "skirmisher-controller",
            "tone": "Elderwyld bramble hazard",
        },
        "encounter_context": {
            "party_level": 4,
            "party_size": 4,
            "encounter_role": "mobile bramble-control threat",
            "environment": "obsidian-choked ruin trail",
            "constraints": ["show as mock only", "do not persist", "do not add to combat"],
        },
        "output_options": {
            "include_markdown": True,
            "include_json": True,
            "include_combat_defaults": True,
            "include_review_warnings": True,
            "persist": False,
            "style": "live-control-workbench-command-generate",
        },
    }
