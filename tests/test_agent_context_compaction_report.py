import hashlib
import json

import pytest
from pydantic import ValidationError

from apps.live_control_server.services.agent_context_compaction_report import compaction_report
from apps.live_control_server.services.agent_conversation_context import compact_conversation_context
from apps.live_control_server.services.agent_turn_service import _PLAN_GRAPH_ANSWER_INSTRUCTIONS, _plan_message


def history():
    text = "Frank and Sara use the Rocky Talkie. " * 1000
    return text, [
        {"role": "system", "content": "PRIVATE_SYSTEM_INSTRUCTIONS"},
        {"role": "user", "content": _plan_message("Tell me about Mirathorn.", "PRIVATE_PLAN_BODY") + "\n\n" + _PLAN_GRAPH_ANSWER_INSTRUCTIONS},
        {"role": "assistant", "tool_calls": [{"id": "call"}], "content": "PRIVATE_TOOL_REASONING", "reasoning": "PRIVATE_REASONING"},
        {"role": "tool", "content": json.dumps({"schema": "dmb_world_graph_source_anchor_read_v1",
            "outcome": "partial", "anchorId": "anchor", "evidenceRefId": "evidence", "sourceArtifactId": "artifact",
            "snapshot": {"worldId": "world", "revisionId": "graph-revision"},
            "sourceRevisionId": "source-revision", "content": text})},
        {"role": "assistant", "content": "Frank and Sara are communications operators.", "reasoning": "PRIVATE_REASONING"},
    ]


def test_report_matches_actual_compaction_and_excludes_prompts_reasoning_and_source_prose():
    text, messages = history()
    compacted = compact_conversation_context(messages)
    report = compaction_report(messages, compacted)
    assert report.before_chars == compacted.before_chars
    assert report.after_chars == compacted.after_chars
    assert report.routes == compacted.routes
    assert report.before_visible[0].text == "Tell me about Mirathorn."
    assert report.after_visible[-1].text == "Frank and Sara are communications operators."
    assert report.prior_sources[0].content_sha256 == hashlib.sha256(text.encode()).hexdigest()
    assert report.prior_sources[0].returned_chars == len(text)
    encoded = report.model_dump_json()
    for private in ("PRIVATE_SYSTEM_INSTRUCTIONS", "PRIVATE_PLAN_BODY", "PRIVATE_TOOL_REASONING", "PRIVATE_REASONING", text):
        assert private not in encoded
    assert {item.action for item in report.decisions} == {"pruned", "compacted", "retained"}
    assert report.prior_sources[0].item_id in {item.item_id for item in report.decisions}


def test_report_keeps_batch_source_candidates_separate_and_never_invents_capture_provenance():
    messages = [{"role": "tool", "content": json.dumps({"schema": "dmb_read_graph_source_batch_v1", "retrievalSessionId": "original-session", "reads": [
        {"schema": "dmb_world_graph_source_anchor_read_v1", "outcome": "enough", "anchorId": "a", "content": "A"},
        {"schema": "dmb_world_graph_source_anchor_read_v1", "outcome": "enough", "anchorId": "b", "content": "B"},
    ]})}]
    report = compaction_report(messages, compact_conversation_context(messages))
    assert [item.anchor_id for item in report.prior_sources] == ["a", "b"]
    assert len({item.item_id for item in report.prior_sources}) == 2
    assert all(item.retrieval_session_id == "original-session" for item in report.prior_sources)
    assert all("trace_id" not in item.model_dump() for item in report.prior_sources)


def test_oversized_context_report_fails_explicitly_without_changing_compaction_result():
    messages = [{"role": "assistant", "content": "a" * 1_048_577}]
    compacted = compact_conversation_context(messages)
    with pytest.raises(ValueError, match="explicit 1 MiB transport limit"):
        compaction_report(messages, compacted)
    assert compacted.messages == messages


def test_too_many_observed_messages_are_rejected_instead_of_silently_truncated():
    messages = [{"role": "user", "content": f"Question {index}"} for index in range(513)]
    with pytest.raises(ValidationError):
        compaction_report(messages, compact_conversation_context(messages))


def test_removed_recap_page_without_a_retained_route_is_not_reported_as_route_preserved():
    messages = [{"role": "tool", "content": json.dumps({"schema": "dmb_related_recap_context_read_v2",
        "outcome": "enough", "contextAnchorId": "recap-context", "content": "Surrounding recap prose."})}]
    compacted = compact_conversation_context(messages)
    report = compaction_report(messages, compacted)
    assert report.decisions[0].action == "pruned"
    assert report.decisions[0].reason_code == "unavailable"
    assert report.prior_sources == []
    assert "Surrounding recap prose." not in report.model_dump_json()
    assert compacted.messages == []
