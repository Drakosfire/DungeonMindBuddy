"""Per-skill strict ``text.format`` selection for planner turns.

The universal envelope (``planner_turn_output``) keeps the model's reply skill-agnostic
for one-shot Q&A turns. When a skill needs a structured side-channel (e.g. ``recap-write``
emits a ``recap_write_v1`` payload), the planner can swap the universal envelope for a
**combined** schema that adds a required top-level field carrying that payload.

This module owns the registry. Skills register a builder that returns the OpenAI
``text=`` argument; ``skill_text_format_for(skill_id)`` returns the appropriate format
or ``None`` when the universal envelope should be used.

When a per-skill schema is in effect with ``strict: true``, the model is **forced**
into the shape — graders can read ``response.recap_write`` directly without having to
extract a fenced block from prose, and validation becomes a paranoia check rather than
a recovery mechanism.
"""

from __future__ import annotations

from typing import Any, Callable

from src.agent.planner_turn_output_schema import (
    PLANNER_USER_INTENT_ENUM,
    _UNSURE_QUEUE_ITEM_SCHEMA,
)
from src.agent.recap_write_output_schema import recap_write_output_json_schema

_RECAP_WRITE_TURN_NAME = "planner_turn_output_recap_write"


def planner_turn_with_recap_write_schema() -> dict[str, Any]:
    """Universal envelope + required ``recap_write`` field carrying ``recap_write_v1``.

    Mirrors :func:`planner_turn_output_json_schema` for ``user_intent`` / ``message`` /
    ``unsure_queue`` so existing downstream consumers keep working when the recap-write
    schema is active. ``message`` is GM-facing prose only — never JSON — because the
    structured payload now lives in its own field.
    """
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
                "description": (
                    "GM-facing prose summary. Do **not** embed the recap_write payload "
                    "here — the schema provides a dedicated `recap_write` field for it."
                ),
            },
            "unsure_queue": {
                "type": ["array", "null"],
                "description": (
                    "Sparse structured questions for operator judgment at end of a "
                    "recap-ingest run. Omit or null when there is nothing material to confirm."
                ),
                "items": _UNSURE_QUEUE_ITEM_SCHEMA,
            },
            "recap_write": recap_write_output_json_schema(),
        },
        "required": ["user_intent", "message", "unsure_queue", "recap_write"],
    }


def planner_turn_with_recap_write_text_format(*, strict: bool = True) -> dict[str, Any]:
    """``text=`` argument for ``client.responses.create`` when recap-write is active."""
    return {
        "format": {
            "type": "json_schema",
            "name": _RECAP_WRITE_TURN_NAME,
            "strict": strict,
            "schema": planner_turn_with_recap_write_schema(),
        }
    }


_SkillTextFormatBuilder = Callable[[], dict[str, Any]]

_SKILL_TEXT_FORMAT_REGISTRY: dict[str, _SkillTextFormatBuilder] = {
    "recap-write": planner_turn_with_recap_write_text_format,
}


def skill_text_format_for(skill_id: str | None) -> dict[str, Any] | None:
    """Return the per-skill ``text=`` argument or ``None`` for the universal envelope.

    Unknown skill ids return ``None``; this is intentional so callers can always pass
    a skill hint without guarding it.
    """
    if not skill_id:
        return None
    builder = _SKILL_TEXT_FORMAT_REGISTRY.get(skill_id.strip())
    return builder() if builder else None


def registered_skill_ids() -> tuple[str, ...]:
    """Sorted tuple of skill ids that have a dedicated ``text.format`` payload."""
    return tuple(sorted(_SKILL_TEXT_FORMAT_REGISTRY))
