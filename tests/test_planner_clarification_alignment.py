"""Tests for ``apply_clarification_alignment_to_final_text`` (passthrough after clarify-tool removal)."""

from __future__ import annotations

import json

from src.agent.planner import ClarificationAlignmentReport, apply_clarification_alignment_to_final_text


def test_apply_clarification_alignment_is_noop() -> None:
    trace = [{"tool": "read_corpus_file", "arguments": {"path": "foo.md"}}]
    body = '{"user_intent":"needs_clarification","message":"Which NPC?"}'
    aligned, report = apply_clarification_alignment_to_final_text(trace, body)
    assert aligned == body
    assert report.mode == "no_clarification"
    assert report.changed is False


def test_apply_clarification_alignment_ignores_legacy_tool_rows_in_trace() -> None:
    """Old transcripts may still list ``propose_clarification``; alignment must not rewrite."""
    trace = [
        {
            "tool": "propose_clarification",
            "arguments": {"question": "Legacy?", "kind": "missing_param"},
            "output_chars": 10,
        }
    ]
    body = json.dumps(
        {"user_intent": "needs_clarification", "message": "Model-authored question?"},
        ensure_ascii=False,
    )
    aligned, report = apply_clarification_alignment_to_final_text(trace, body)
    assert aligned == body
    assert report == ClarificationAlignmentReport(mode="no_clarification")
