from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from src.statblocks.lifecycle_artifact import (
    StatblockBreadcrumb,
    StatblockDraftArtifact,
)
from src.statblocks.lifecycle_commands import STATBLOCK_DRAFT_GENERATE
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
