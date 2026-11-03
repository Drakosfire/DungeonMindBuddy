import pytest

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


@pytest.mark.parametrize("label", [
    "Next Beats :", "Looking Ahead:", "Planning Notes :", "Prep Notes:",
    "**Next Beats:**", "**Next Beats**:", "__Planning Notes__:",
])
@pytest.mark.parametrize("recap", ["Recap :", "**Recap:**", "## Recap"])
def test_label_only_planning_section_survives_blank_paragraphs(label, recap):
    text = f"{label}\n\nFuture reward.\n\nA planned journey.\n\n{recap}\n\nIria arrived."
    kept, withheld, _ = partition_recap_source_rows(rows(text), text)
    assert [r["text"] for r in kept] == [recap, "Iria arrived."]
    assert [r["text"] for r in withheld] == [label, "Future reward.", "A planned journey."]


def test_label_only_planning_keeps_details_until_explicit_recap_boundary():
    text = "Next Beats:\n\n### Detail\nA reward.\n\nAnother reward."
    kept, withheld, _ = partition_recap_source_rows(rows(text), text)
    assert not kept and withheld == rows(text)


def test_plain_recap_label_resumes_markdown_planning_section():
    text = "## Next Beats\nFuture reward.\n\nRecap :\n\nIria arrived."
    kept, withheld, _ = partition_recap_source_rows(rows(text), text)
    assert [r["text"] for r in kept] == ["Recap :", "Iria arrived."]
    assert [r["text"] for r in withheld] == ["## Next Beats", "Future reward."]


def test_label_only_markers_in_quotes_code_or_prose_do_not_switch_authority():
    text = '> Next Beats :\n```text\nNext Beats :\n```\nIria says: Next Beats: a reward.'
    kept, withheld, _ = partition_recap_source_rows(rows(text), text)
    assert kept == rows(text) and not withheld


def test_plain_recap_inside_planning_code_or_prose_does_not_resume_play():
    text = "Next Beats :\n\n```text\nRecap :\n```\n\nRecap: a proposed scene.\n\nFuture reward."
    kept, withheld, _ = partition_recap_source_rows(rows(text), text)
    assert not kept and withheld == rows(text)


@pytest.mark.parametrize("label", ["Next Beats:", "**Next Beats:**", "__Planning Notes__:"])
@pytest.mark.parametrize("newline", ["\n", "\r\n", "\r"])
def test_lazy_blockquote_label_does_not_hide_later_played_paragraph(label, newline):
    text = newline.join(["> The GM wrote:", label, "A future reward.", "", "The party arrived in town."])
    kept, withheld, _ = partition_recap_source_rows(rows(text), text)
    assert kept == rows(text) and not withheld


def test_lazy_quoted_recap_does_not_end_real_planning_section():
    text = "Next Beats:\n\n> A quoted example:\nRecap:\nAn example scene.\n\nActual future reward."
    kept, withheld, _ = partition_recap_source_rows(rows(text), text)
    assert not kept and withheld == rows(text)


def test_real_label_after_blockquote_paragraph_still_starts_planning():
    text = "> A quoted example.\n\nNext Beats:\n\nA future reward.\n\nRecap:\nPlayed event."
    kept, withheld, _ = partition_recap_source_rows(rows(text), text)
    assert [r["text"] for r in kept] == ["> A quoted example.", "Recap:", "Played event."]
    assert [r["text"] for r in withheld] == ["Next Beats:", "A future reward."]


@pytest.mark.parametrize("separator", ["\u2028", "\u2029", "\x85", "\v", "\f", "\x1c", "\x1d", "\x1e"])
def test_lazy_quote_maps_to_source_rows_after_unicode_separators(separator):
    text = f"Intro{separator}detail{separator}more\n> The GM wrote:\nNext Beats:\nA future reward.\n\nThe party arrived in town."
    source_rows = rows(text)
    kept, withheld, _ = partition_recap_source_rows(source_rows, text)
    assert kept == source_rows and not withheld
    assert text.splitlines()[4] == "Next Beats:"


@pytest.mark.parametrize(("heading", "peer"), [
    ("## Next Beats : A reward.", "## Ordinary scene"),
    ("#### Looking Ahead: A journey.", "#### Ordinary scene"),
    ("# Planning Notes: A map.", "# Ordinary scene"),
    ("###### Prep Notes: A visitor.", "###### Ordinary scene"),
    ("## nExT\tBeats: A reward.", "## Ordinary scene"),
    ("## **Next Beats**: A reward.", "## Ordinary scene"),
])
def test_planning_heading_payload_uses_existing_heading_depth(heading, peer):
    text = f"{heading}\n\nMore preparation.\n\n{peer}\nIria arrived."
    kept, withheld, _ = partition_recap_source_rows(rows(text), text)
    assert [r["text"] for r in kept] == [peer, "Iria arrived."]
    assert [r["text"] for r in withheld] == [heading, "More preparation."]


@pytest.mark.parametrize("marker", ["**Recap : **", "__Recap:__", "**Recap:** "])
@pytest.mark.parametrize("newline", ["\n", "\r\n", "\r"])
def test_marked_recap_with_inside_colon_resumes_same_line_prose(marker, newline):
    recap = marker + "The team arrived."
    text = newline.join(["Next Beats:", "", "Future reward.", "", recap, "More played prose."])
    kept, withheld, _ = partition_recap_source_rows(rows(text), text)
    assert [r["text"] for r in kept] == [recap, "More played prose."]
    assert [r["text"] for r in withheld] == ["Next Beats:", "Future reward."]


@pytest.mark.parametrize("content", [
    "**Recap**: proposed future scene.", "Recap: proposed future scene.",
    "**Recap:__A scene.", "    **Recap:**An indented example.",
    "> **Recap:**A quoted scene.",
    "> A quoted example:\n**Recap:**A lazy quoted scene.",
    "```text\n**Recap:**A fenced scene.\n```",
])
def test_inline_recap_boundary_requires_structural_marker(content):
    text = f"Next Beats:\n\n{content}\n\nStill preparation."
    kept, withheld, _ = partition_recap_source_rows(rows(text), text)
    assert not kept and withheld == rows(text)


def test_marked_recap_exit_does_not_classify_its_payload_meaning():
    text = "Next Beats:\nFuture reward.\n**Recap:**A proposed future scene is discussed."
    kept, _, _ = partition_recap_source_rows(rows(text), text)
    assert [r["text"] for r in kept] == ["**Recap:**A proposed future scene is discussed."]


def test_inline_heading_payload_in_quote_or_code_does_not_start_planning():
    text = "> ## Next Beats: An example.\n\n```text\n## Next Beats: Another example.\n```\nIria arrived."
    kept, withheld, _ = partition_recap_source_rows(rows(text), text)
    assert kept == rows(text) and not withheld


def test_inline_planning_heading_does_not_capture_other_heading_titles():
    text = "## Next Beats are discussed: A report.\n## `Next Beats`: A code label.\nIria arrived."
    kept, withheld, _ = partition_recap_source_rows(rows(text), text)
    assert kept == rows(text) and not withheld


def test_inline_planning_heading_keeps_nested_details_at_parent_depth():
    text = "## Next Beats: A reward.\n### Detail\nMore preparation.\n## Ordinary scene\nIria arrived."
    kept, withheld, _ = partition_recap_source_rows(rows(text), text)
    assert [r["text"] for r in kept] == ["## Ordinary scene", "Iria arrived."]
    assert [r["text"] for r in withheld] == ["## Next Beats: A reward.", "### Detail", "More preparation."]


def test_marked_inline_recap_in_lazy_quote_after_unicode_is_not_boundary():
    text = "Intro\u2028detail\u2028more\nNext Beats:\n\n> An example:\n**Recap:**A quoted scene.\n\nStill preparation."
    kept, withheld, _ = partition_recap_source_rows(rows(text), text)
    assert [r["text"] for r in kept] == ["Intro", "detail", "more"]
    assert [r["text"] for r in withheld] == [
        "Next Beats:", "> An example:", "**Recap:**A quoted scene.", "Still preparation.",
    ]
