from src.graph_memory.extraction.recap_source_authority import (
    filter_planning_pass_output, partition_recap_source_rows,
)


def rows(text):
    return [{"source_span_ref_id": str(i), "line_start": i, "line_end": i, "text": line}
            for i, line in enumerate(text.splitlines(), 1) if line.strip()]


def test_nested_planning_heading_exits_only_at_peer_or_parent():
    text = "## Next Beats\nReward the party.\n### Detail\nGive a map.\n## Recap\nIria arrived."
    kept, withheld, diag = partition_recap_source_rows(rows(text), text)
    assert [r["text"] for r in kept] == ["## Recap", "Iria arrived."]
    assert len(withheld) == 4 and diag["checked"]


def test_inline_planning_prefix_ends_at_paragraph_boundary():
    text = "**Looking Ahead : **Give a reward.\nAnd a map.\n\nIria arrived."
    kept, withheld, _ = partition_recap_source_rows(rows(text), text)
    assert [r["text"] for r in kept] == ["Iria arrived."]
    assert len(withheld) == 2


def test_quoted_and_fenced_markers_do_not_switch_authority():
    text = '> ## Next Beats\n```text\n## Planning Notes\n```\nIria says: Looking Ahead: I will return.'
    kept, withheld, _ = partition_recap_source_rows(rows(text), text)
    assert kept == rows(text) and not withheld


def test_mixed_span_is_deferred_without_rewriting_or_losing_source():
    text = "## Next Beats\nA reward.\n## Recap\nIria arrived."
    source = [{"source_span_ref_id": "mixed", "line_start": 1, "line_end": 4, "text": text}]
    kept, withheld, diag = partition_recap_source_rows(source, text)
    assert not kept and withheld == source
    assert diag["mixed_span_ids"] == ["mixed"]
    assert source[0]["text"] == text


def test_missing_full_text_reports_unchecked():
    source = rows("Iria arrived.")
    kept, withheld, diag = partition_recap_source_rows(source, None)
    assert kept == source and not withheld and not diag["checked"]


def test_mixed_claim_is_deferred_whole_even_with_an_allowed_citation():
    record = {"node_id": "mixed", "evidence_refs": [
        {"source_span_ref_id": "played"}, {"source_span_ref_id": "planned"},
    ]}
    parsed = {"observation_nodes": [record], "deferred_items": [record]}
    out, deferred = filter_planning_pass_output(parsed, {"planned"}, lambda s, allowed: s if s in allowed else None)
    assert out["observation_nodes"] == []
    assert out["deferred_items"] == [record]
    assert deferred[0]["evidence_refs"] == record["evidence_refs"]
    assert parsed["observation_nodes"] == [record]


def test_standalone_bold_recap_marker_resumes_played_content():
    for marker in ["**Recap**:", "**Recap:**", "__Recap__:"]:
        text = "## Next Beats :\nFuture reward.\n\n" + marker + "\n\nThe party enters a room."
        kept, withheld, _ = partition_recap_source_rows(rows(text), text)
        assert [r["text"] for r in kept] == [marker, "The party enters a room."]
        assert [r["text"] for r in withheld] == ["## Next Beats :", "Future reward."]


def test_quoted_fenced_or_prose_recap_marker_does_not_end_planning():
    text = "## Next Beats\n> **Recap**:\n```text\n**Recap**:\n```\n**Recap**: proposed future scene.\nGive a reward."
    kept, withheld, _ = partition_recap_source_rows(rows(text), text)
    assert not kept and withheld == rows(text)


def test_fence_like_content_does_not_close_a_planning_fence():
    text = (
        "## Planning Notes\n```text\n```literal\n**Recap**:\n"
        "The party will discover Moon Harbor.\n```\n"
        "## Recap\nThe party arrived in Larkhaven."
    )
    kept, withheld, _ = partition_recap_source_rows(rows(text), text)
    assert [row["text"] for row in kept] == ["## Recap", "The party arrived in Larkhaven."]
    assert [row["text"] for row in withheld] == [
        "## Planning Notes", "```text", "```literal", "**Recap**:",
        "The party will discover Moon Harbor.", "```",
    ]


def test_longer_matching_fence_closes_but_mixed_delimiter_does_not():
    text = (
        "## Planning Notes\n~~~~text\n```\nStill planned.\n~~~~~\n"
        "## Recap\nPlayed event."
    )
    kept, withheld, _ = partition_recap_source_rows(rows(text), text)
    assert [row["text"] for row in kept] == ["## Recap", "Played event."]
    assert len(withheld) == 5


def test_planning_labels_inside_code_do_not_create_a_planning_section():
    text = (
        "Ordinary source.\n````markdown\n## Planning Notes\n**Recap**:\n"
        "This is literal example text.\n````\nPlayed event."
    )
    kept, withheld, _ = partition_recap_source_rows(rows(text), text)
    assert kept == rows(text)
    assert not withheld


def test_split_bold_recap_marker_resumes_played_content():
    text = "## Looking Ahead :\nA future reward.\n\n**Recap:\n**The party rests."
    kept, withheld, _ = partition_recap_source_rows(rows(text), text)
    assert [r["text"] for r in kept] == ["**Recap:", "**The party rests."]
    assert len(withheld) == 2


def test_unclosed_bold_recap_marker_does_not_resume_played_content():
    text = "## Looking Ahead :\n**Recap:\nA future scene."
    kept, withheld, _ = partition_recap_source_rows(rows(text), text)
    assert not kept and withheld == rows(text)
