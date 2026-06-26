"""Tests for src/graph_memory/anchor_quotes.py."""

from __future__ import annotations

from src.graph_memory.anchor_quotes import (
    AnchorQuoteMatch,
    coerce_anchor_quotes,
    find_anchor_quote_matches,
    normalize_for_match,
    quote_found_in_paragraph,
)


def test_normalize_for_match_folds_case_and_whitespace():
    assert normalize_for_match("  Hello   World  ") == "hello world"


def test_normalize_for_match_folds_curly_quotes_and_dashes():
    raw = "Wizard\u2019s College and \u201cmeat heads\u201d"
    assert "wizard's college" in normalize_for_match(raw)
    assert "meat heads" in normalize_for_match(raw)


def test_find_exact_match_returns_raw_offsets():
    para = "Something is wrong with the reflections in the puddles."
    quote = "reflections in the puddles"
    matches = find_anchor_quote_matches(para, [quote])
    assert len(matches) == 1
    m = matches[0]
    assert m.quote == quote
    assert para[m.char_start:m.char_end] == "reflections in the puddles"
    assert m.match_text == "reflections in the puddles"


def test_find_match_case_insensitive():
    para = "Private Hester reports to Mirathorn."
    matches = find_anchor_quote_matches(para, ["private hester"])
    assert matches and para[matches[0].char_start:matches[0].char_end].casefold() == "private hester"


def test_find_repeated_quote_returns_all_matches():
    para = "Grobnok called Grobnok again."
    matches = find_anchor_quote_matches(para, ["Grobnok"])
    assert len(matches) == 2
    assert matches[0].char_start != matches[1].char_start


def test_absent_quote_returns_empty():
    assert find_anchor_quote_matches("hello world", ["missing phrase"]) == []


def test_quote_not_in_paragraph_when_only_similar_text_exists():
    para = "the reflections are somewhat delayed"
    assert not quote_found_in_paragraph(para, "Delayed puddle reflections")


def test_curly_apostrophe_in_source_matches_ascii_quote():
    para = "the Wizard\u2019s College is north."
    assert quote_found_in_paragraph(para, "Wizard's College")


def test_coerce_anchor_quotes_filters_empty():
    assert coerce_anchor_quotes(["  a  ", "", "b"]) == ["a", "b"]
    assert coerce_anchor_quotes(" lone ") == ["lone"]
    assert coerce_anchor_quotes(None) == []


def test_match_span_does_not_cross_unrelated_paragraph_boundary():
    # Paragraph-scoped: quote must appear inside the given paragraph text only.
    para_a = "first paragraph about storms."
    para_b = "second paragraph about storms."
    assert find_anchor_quote_matches(para_a, ["storms"])
    assert not find_anchor_quote_matches(para_a, ["second paragraph"])


def test_anchor_quote_match_dataclass_fields():
    m = AnchorQuoteMatch(quote="x", char_start=1, char_end=2, match_text="x")
    assert m.char_start == 1 and m.char_end == 2
