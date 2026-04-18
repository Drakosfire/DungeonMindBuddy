"""Planner turn JSON schema (Responses ``text.format`` wiring)."""

from __future__ import annotations

import json

from src.agent.planner_turn_output_schema import (
    PLANNER_USER_INTENT_ENUM,
    planner_turn_output_json_schema,
    planner_turn_text_format,
)


def test_planner_turn_output_json_schema_is_object_with_enum_and_message() -> None:
    schema = planner_turn_output_json_schema()
    assert schema["type"] == "object"
    assert schema.get("additionalProperties") is False
    props = schema["properties"]
    assert props["user_intent"]["type"] == ["string", "null"]
    assert set(props["user_intent"]["enum"]) == {None, *PLANNER_USER_INTENT_ENUM}
    assert props["message"]["type"] == "string"
    assert props["unsure_queue"]["type"] == ["array", "null"]
    item = props["unsure_queue"]["items"]
    assert item["required"] == [
        "id",
        "question",
        "default_summary",
        "alternative_summaries",
    ]
    assert schema["required"] == ["user_intent", "message"]


def test_planner_turn_text_format_is_json_schema_block() -> None:
    tf = planner_turn_text_format()
    assert tf["format"]["type"] == "json_schema"
    assert tf["format"]["name"]
    json.dumps(tf["format"]["schema"])

