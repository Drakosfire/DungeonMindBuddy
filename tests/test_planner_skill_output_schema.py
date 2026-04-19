"""Per-skill ``text.format`` selection for planner turns."""

from __future__ import annotations

from src.agent.planner_skill_output_schema import (
    planner_turn_with_recap_write_schema,
    planner_turn_with_recap_write_text_format,
    registered_skill_ids,
    skill_text_format_for,
)
from src.agent.planner_turn_output_schema import PLANNER_USER_INTENT_ENUM
from src.agent.recap_write_output_schema import RECAP_WRITE_SCHEMA_VERSION


def test_skill_text_format_for_unknown_returns_none() -> None:
    assert skill_text_format_for(None) is None
    assert skill_text_format_for("") is None
    assert skill_text_format_for("does-not-exist") is None


def test_skill_text_format_for_recap_write() -> None:
    fmt = skill_text_format_for("recap-write")
    assert fmt is not None
    assert fmt == planner_turn_with_recap_write_text_format()
    inner = fmt["format"]
    assert inner["type"] == "json_schema"
    assert inner["name"] == "planner_turn_output_recap_write"
    assert inner["strict"] is True


def test_recap_write_envelope_requires_recap_write_field() -> None:
    schema = planner_turn_with_recap_write_schema()
    assert schema["additionalProperties"] is False
    required = set(schema["required"])
    assert required == {"user_intent", "message", "unsure_queue", "recap_write"}
    props = schema["properties"]
    assert props["recap_write"]["properties"]["schema_version"]["enum"] == [
        RECAP_WRITE_SCHEMA_VERSION
    ]
    intent_enum = props["user_intent"]["enum"]
    for label in PLANNER_USER_INTENT_ENUM:
        assert label in intent_enum
    assert None in intent_enum


def test_registered_skill_ids_includes_recap_write() -> None:
    assert "recap-write" in registered_skill_ids()
