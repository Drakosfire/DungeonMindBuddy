"""Tests for sentence_routing_retrieval_falsification Stage A capture."""

from __future__ import annotations

import json
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_SLICE = _REPO / "evals" / "sentence_routing_retrieval_falsification"
_SCENARIO = _SLICE / "gold" / "scenario_mini.json"


def test_capture_mini_fixture_unit_count() -> None:
    from evals.sentence_routing_retrieval_falsification.capture import capture_sentence_units_from_file
    from evals.sentence_routing_retrieval_falsification.grader import collect_stage_a_violations

    raw = json.loads(_SCENARIO.read_text(encoding="utf-8"))
    rel = str(raw["input"]["recap_relative_path"])
    units = capture_sentence_units_from_file(corpus_root=_REPO, recap_relative_path=rel)
    # Line 3: two sentences; line 5: two sentences (see fixtures/mini_recap.md).
    assert len(units) == 4
    v, _ = collect_stage_a_violations(
        units,
        dict(raw.get("gold_capture") or {}),
        corpus_root=_REPO,
        recap_relative_path=rel,
    )
    assert v == []


def test_capture_skips_headers_and_blank_lines() -> None:
    from evals.sentence_routing_retrieval_falsification.capture import capture_sentence_units

    text = "# Title line\n\nHello world. Goodbye world.\n"
    units = capture_sentence_units(recap_text=text, recap_relative_path="x.md")
    assert len(units) == 2
    assert units[0].line_start == 3
    assert "Hello world" in units[0].text
