"""Strict structured output for live-turn classification (Responses API ``text.format``)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

LATENCY_MODE_LITERAL = Literal["fast_live", "context_lookup", "prep_architect", "post_session"]

EVENT_TYPE_LITERAL = Literal[
    "roll_result",
    "skill_check",
    "canon_commit",
    "canon_correction",
    "open_loop_update",
    "context_question",
    "prep_request",
    "state_note",
]

CONFIDENCE_LITERAL = Literal["high", "medium", "low"]

_SCHEMA_NAME = "live_turn_classification"


class LiveTurnSkillCheck(BaseModel):
    actor: str = Field(description="Character name performing the check.")
    skill: str = Field(description="Skill name, e.g. Nature.")
    total: int = Field(description="Reported total on the die/check.")


class LiveTurnClassificationModel(BaseModel):
    latency_mode: LATENCY_MODE_LITERAL = Field(
        description="How expensive the answer path may be.",
    )
    event_type: EVENT_TYPE_LITERAL = Field(
        description="Primary event row to append to the live event log.",
    )
    intent: str = Field(
        description="Short snake_case intent label for telemetry (e.g. resolve_roll_table).",
        max_length=120,
    )
    table_id: str | None = Field(
        default=None,
        description="Roll table id when event_type is roll_result (e.g. T-WX, R5).",
    )
    roll: int | None = Field(
        default=None,
        description="Die result for roll_result when present in the GM line.",
    )
    skill_check: LiveTurnSkillCheck | None = Field(
        default=None,
        description="Optional inline skill check mentioned with a roll line.",
    )
    confidence: CONFIDENCE_LITERAL = Field(
        default="high",
        description="Classifier confidence in this routing decision.",
    )


def live_turn_classification_json_schema(*, strict: bool = True) -> dict[str, Any]:
    return LiveTurnClassificationModel.model_json_schema()


def live_turn_classification_text_format(*, strict: bool = True) -> dict[str, Any]:
    return {
        "format": {
            "type": "json_schema",
            "name": _SCHEMA_NAME,
            "strict": strict,
            "schema": live_turn_classification_json_schema(strict=strict),
        }
    }
