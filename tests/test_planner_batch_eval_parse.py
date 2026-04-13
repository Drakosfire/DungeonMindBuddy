"""Unit tests for planner batch eval response parsing (no API)."""

from __future__ import annotations

from evals.planner_slice.batch_eval import (
    function_calls_from_response_body,
    output_text_from_response_body,
)


def test_function_calls_from_response_body_parses_arguments() -> None:
    body = {
        "id": "resp_1",
        "output": [
            {
                "type": "function_call",
                "name": "read_corpus_file",
                "arguments": '{"path": "foo/bar.md"}',
                "call_id": "call_abc",
            }
        ],
    }
    calls = function_calls_from_response_body(body)
    assert len(calls) == 1
    assert calls[0]["name"] == "read_corpus_file"
    assert calls[0]["arguments"] == {"path": "foo/bar.md"}
    assert calls[0]["_call_id"] == "call_abc"


def test_output_text_from_response_body_joins_parts() -> None:
    body = {
        "output": [
            {
                "type": "message",
                "content": [
                    {"type": "output_text", "text": "Hello "},
                    {"type": "output_text", "text": "world."},
                ],
            }
        ]
    }
    assert output_text_from_response_body(body) == "Hello world."


def test_function_calls_skips_non_function_items() -> None:
    body = {
        "output": [
            {"type": "message", "content": [{"type": "output_text", "text": "x"}]},
            {"type": "function_call", "name": "t", "arguments": "{}", "call_id": "c1"},
        ]
    }
    calls = function_calls_from_response_body(body)
    assert [c["name"] for c in calls] == ["t"]
