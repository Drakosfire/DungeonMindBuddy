"""Strict JSON schema for corpus planner assistant text (Responses API ``text.format``).

Every planner ``responses.create`` turn that can emit assistant-visible text uses the same
envelope so callers can treat ``user_intent`` as a lightweight classifier label for the
**user's** ask (aligned with Step 2 ``IntentMode``) while ``message`` carries GM-facing prose.
"""

from __future__ import annotations

import os
from typing import Any

# Keep overlapping labels in sync with ``IntentMode`` in
# ``src/npc_statblock_pipeline/canonical_intent.py``.
PLANNER_USER_INTENT_ENUM: tuple[str, ...] = (
    "factual_lookup",
    "upgrade_request",
    "comparison_request",
    "worldbuilding_request",
    "planning_request",
    "status_or_recap_request",
    "generation_request",
    # Use when the final ``message`` is only a blocking clarifying question (no substantive answer).
    # downstream consumers (``IntentMode`` in ``src/npc_statblock_pipeline/canonical_intent.py``)
    # treat this as a terminal turn that needs GM input before the pipeline advances.
    "needs_clarification",
)

_PLANNER_TURN_OUTPUT_NAME = "planner_turn_output"

_UNSURE_QUEUE_ITEM_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "id": {
            "type": "string",
            "description": "Stable machine id for this judgment item (snake_case).",
        },
        "question": {
            "type": "string",
            "description": "One short question the GM can answer in one line.",
        },
        "default_summary": {
            "type": "string",
            "description": "What you will do if the GM does not answer (explicit default).",
        },
        "alternative_summaries": {
            "type": "array",
            "description": "At least two other concrete options (not filler).",
            "items": {"type": "string"},
            "minItems": 2,
        },
    },
    "required": ["id", "question", "default_summary", "alternative_summaries"],
}


def planner_turn_output_json_schema(*, strict: bool = True) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "user_intent": {
                "type": ["string", "null"],
                "description": (
                    "Classifier label for the user's ask in this turn (not a tool name). "
                    "Use null only when the ask is ambiguous or genuinely mixed."
                ),
                "enum": [*PLANNER_USER_INTENT_ENUM, None],
            },
            "message": {
                "type": "string",
                "description": "GM-facing reply body (markdown allowed inside the string).",
            },
            "unsure_queue": {
                "type": ["array", "null"],
                "description": (
                    "Sparse structured questions for operator judgment at end of a recap-ingest "
                    "run. Omit or null when there is nothing material to confirm."
                ),
                "items": _UNSURE_QUEUE_ITEM_SCHEMA,
            },
        },
        "required": ["user_intent", "message"],
    }


def planner_turn_text_format(*, strict: bool = True) -> dict[str, Any]:
    """``text=`` argument for ``client.responses.create`` (planner turns only)."""
    return {
        "format": {
            "type": "json_schema",
            "name": _PLANNER_TURN_OUTPUT_NAME,
            "strict": strict,
            "schema": planner_turn_output_json_schema(strict=strict),
        }
    }


def planner_turn_output_schema_enabled() -> bool:
    raw = os.environ.get("PLANNER_TURN_OUTPUT_SCHEMA", "1").strip().lower()
    return raw not in ("0", "false", "no", "off")
