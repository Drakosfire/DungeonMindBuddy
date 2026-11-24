import json

import pytest

from apps.live_control_server.services.build_reply_projection import BuildReplyProjection


@pytest.mark.parametrize("chunk_size", [1, 2, 7, 13])
def test_incremental_prose_is_limited_to_exact_answer_string_paths(chunk_size):
    text = 'A "bright" lantern. 雪😀\nNext line.'
    payload = json.dumps({
        "metadata": {"answer_segments": [{"text": "hidden nested text"}]},
        "answer_segments": [
            {"kind": "discussion", "text": text, "details": {"text": "hidden detail"}},
            {"kind": "discussion", "text": "The end."},
        ],
        "collaboration": {"text": "hidden collaboration"},
    }, ensure_ascii=True)
    projection = BuildReplyProjection()
    updates = [
        update for start in range(0, len(payload), chunk_size)
        if (update := projection.feed(payload[start:start + chunk_size])) is not None
    ]
    answer = text + "\n\nThe end."
    assert len(updates) >= 2
    assert "".join(updates) == answer
    assert not projection.invalid


def test_updates_are_available_inside_the_first_open_text_string():
    projection = BuildReplyProjection()
    assert projection.feed('{"answer_segments":[{"text":"A lantern') == "A lantern"
    assert projection.feed(' lit the way') == " lit the way"
    assert projection.feed('."}]}') == "."


@pytest.mark.parametrize("payload", [
    '{"answer_segments":{"0":{"text":"wrong"}}}',
    '{"answer_segments":[["wrong"],{"nested":{"text":"wrong"}}]}',
    '{"rules_segments":[{"text":"unverified ordering"}]}',
])
def test_excludes_other_output_paths(payload):
    projection = BuildReplyProjection()
    assert projection.feed(payload) is None
    assert not projection.invalid


@pytest.mark.parametrize("suffix", [
    r'\q"}]}',
    '","text":"duplicate"}]}',
    '"},]}',
    '"}]} trailing commentary',
    r'\ud800\u1234"}]}',
])
def test_malformed_output_cannot_publish_another_preview(suffix):
    projection = BuildReplyProjection()
    assert projection.feed('{"answer_segments":[{"text":"Initial preview') == "Initial preview"
    assert projection.feed(suffix) is None
    assert projection.invalid
    assert projection.feed('{"answer_segments":[{"text":"Later"}]}') is None
