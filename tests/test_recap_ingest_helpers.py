"""Unit tests for mechanical recap ingest helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.agent.recap_ingest_helpers import (
    assemble_recap,
    detect_duplicate_paragraphs,
    emit_recap_frontmatter,
    numbered_lines_for_recap,
    split_paragraphs_robust,
    strip_leading_title_line,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SESSION_20_RAW = REPO_ROOT / "Session 20 Recap.txt"
GOLD_RECAP = (
    REPO_ROOT
    / "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps"
    / "Session 20 - Recap.md"
)


def test_strip_leading_title_line_session_20() -> None:
    raw = SESSION_20_RAW.read_text(encoding="utf-8")
    stripped, ok = strip_leading_title_line(raw, 20)
    assert ok is True
    assert not stripped.lstrip().startswith("Session 20 Recap")


def test_numbered_lines_preserve_file_numbers_after_title_strip() -> None:
    raw = SESSION_20_RAW.read_text(encoding="utf-8")
    numbered, stripped = numbered_lines_for_recap(raw, 20)
    assert stripped is True
    # First content line of transcript is still line 3 in the file
    first_nonblank = next(ln for _no, ln in numbered if ln.strip())
    assert first_nonblank.startswith("Back out near")


def test_split_paragraphs_session_20_counts() -> None:
    raw = SESSION_20_RAW.read_text(encoding="utf-8")
    numbered, _s = numbered_lines_for_recap(raw, 20)
    paras = split_paragraphs_robust(numbered)
    assert len(paras) == 12


def test_detect_duplicates_session_20_lines_6_and_10() -> None:
    raw = SESSION_20_RAW.read_text(encoding="utf-8")
    numbered, _s = numbered_lines_for_recap(raw, 20)
    paras = split_paragraphs_robust(numbered)
    dupes = detect_duplicate_paragraphs(paras)
    assert len(dupes) == 1
    assert dupes[0].a.source_line_start == 6
    assert dupes[0].b.source_line_start == 10


def test_assemble_recap_duplicate_report() -> None:
    raw = SESSION_20_RAW.read_text(encoding="utf-8")
    _text, report = assemble_recap(
        raw_notes=raw, session=20, campaign_id="longmont-c2", remove_duplicates=True
    )
    assert report.title_line_stripped is True
    assert report.paragraph_count_in == 12
    assert report.paragraph_count_out == 11
    assert len(report.duplicates_detected) == 1
    assert len(report.duplicates_removed) == 1


def test_assemble_body_not_leading_title() -> None:
    raw = SESSION_20_RAW.read_text(encoding="utf-8")
    text, _r = assemble_recap(raw_notes=raw, session=20, campaign_id="longmont-c2")
    body_start = text.split("# Session 20 Recap\n\n", 1)[1]
    first_para = body_start.split("\n\n")[0]
    assert not first_para.startswith("Session 20 Recap")


def test_emit_recap_frontmatter_shape() -> None:
    fm = emit_recap_frontmatter(session=20, campaign_id="longmont-c2")
    assert 'title: "Session 20 - Recap"' in fm
    assert "campaign_id: longmont-c2" in fm
    assert fm.count("---") == 2


@pytest.mark.skipif(not GOLD_RECAP.is_file(), reason="gold recap missing")
def test_assemble_body_matches_gold_body() -> None:
    raw = SESSION_20_RAW.read_text(encoding="utf-8")
    assembled, _r = assemble_recap(
        raw_notes=raw, session=20, campaign_id="longmont-c2"
    )
    gold = GOLD_RECAP.read_text(encoding="utf-8")
    gold_body = gold.split("# Session 20 Recap\n\n", 1)[1]
    asm_body = assembled.split("# Session 20 Recap\n\n", 1)[1]
    assert asm_body == gold_body


# ---------------------------------------------------------------------------
# Heuristic robustness — abbreviations and dialogue boundaries.
# These add diagnostic coverage on top of the Session 20 byte-equal gate.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "abbrev_line",
    [
        "Karesmine talks to Dr.",
        "Bonogo argues with Mr.",
        "Stafl says vs.",
        "Sara, etc.",
        "She uses i.e.",
    ],
)
def test_abbreviations_do_not_terminate_sentence(abbrev_line: str) -> None:
    numbered = [(1, abbrev_line), (2, "The party regroups.")]
    paras = split_paragraphs_robust(numbered)
    assert len(paras) == 1, paras


def test_real_period_after_abbreviation_token_still_splits() -> None:
    numbered = [(1, "He greeted Mr. Smith."), (2, "Then they left.")]
    paras = split_paragraphs_robust(numbered)
    assert len(paras) == 2


@pytest.mark.parametrize(
    "next_line",
    [
        '"Stop!" she yelled.',
        '\u201cStop!\u201d she yelled.',
        '\u2014Then he ran.',
        '"What?" he replied.',
    ],
)
def test_dialogue_or_dash_line_starts_new_paragraph(next_line: str) -> None:
    numbered = [(1, "She turned to face him."), (2, next_line)]
    paras = split_paragraphs_robust(numbered)
    assert len(paras) == 2, paras


def test_lowercase_continuation_line_does_not_split() -> None:
    numbered = [(1, "She walked"), (2, "to the door.")]
    paras = split_paragraphs_robust(numbered)
    assert len(paras) == 1


def test_quote_only_line_does_not_split_when_no_inner_capital() -> None:
    numbered = [(1, "She walked away."), (2, '"yes,"')]
    paras = split_paragraphs_robust(numbered)
    assert len(paras) == 1
