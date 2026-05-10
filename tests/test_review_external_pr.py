"""Unit tests for ``scripts/review_external_pr.py`` parsing helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.review_external_pr import (
    HandoffSections,
    extract_rubric_bullets,
    parse_handoff,
    parse_passed_count_from_tail,
)


def test_parse_passed_count_from_tail_pytest_summary() -> None:
    tail = (
        "....                                                                     [100%]\n"
        "============================= 17 passed, 2 warnings in 0.42s =============================\n"
    )
    assert parse_passed_count_from_tail(tail) == 17


def test_parse_passed_count_from_tail_failed_and_passed() -> None:
    tail = "=========================== short test summary info ============================\nFAILED tests/x.py::t - assert 0\n======================== 2 failed, 15 passed in 1.0s =========================\n"
    assert parse_passed_count_from_tail(tail) == 15


def test_parse_passed_count_from_tail_none_when_missing() -> None:
    assert parse_passed_count_from_tail("no pytest summary here\n") is None


def test_parse_passed_count_from_tail_last_match_wins() -> None:
    tail = "3 passed\nlater: 9 passed\n"
    assert parse_passed_count_from_tail(tail) == 9


def test_extract_rubric_bullets_skips_blockquote() -> None:
    raw = "ignored"
    body = """Acceptance rubric

- [ ] First guarantee — verified by `pytest a`.
> **Reviewer reminder:** ignore this line style
- [x] Second item done
- Plain dash bullet
"""
    h2 = HandoffSections(path=Path("x.md"), raw=raw, sections={"§9": body})
    out = extract_rubric_bullets(h2)
    assert "First guarantee" in out[0]
    assert "Second item done" in out[1]
    assert out[2] == "Plain dash bullet"
    assert len(out) == 3


def test_parse_handoff_round_trip_sample(tmp_path: Path) -> None:
    p = tmp_path / "HANDOFF-sample.md"
    p.write_text(
        """# Title

## §9 Acceptance rubric

- [ ] **Byte-identical** when flag off — verified by `uv run pytest tests/t.py`.
- [ ] No scope creep

## §10 Notes

done
""",
        encoding="utf-8",
    )
    h = parse_handoff(p)
    bullets = extract_rubric_bullets(h)
    assert len(bullets) == 2
    assert "Byte-identical" in bullets[0]


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
