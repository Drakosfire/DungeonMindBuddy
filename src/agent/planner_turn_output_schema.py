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
)

_PLANNER_TURN_OUTPUT_NAME = "planner_turn_output"


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
