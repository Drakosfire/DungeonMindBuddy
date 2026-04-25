"""Deterministic recap line -> sentence-ish units (Stage A scaffold).

Split policy (v0, intentionally simple):
- One-based line numbers into the recap file.
- Blank lines separate story chunks for humans but do not emit units.
- Lines whose stripped text starts with ``#`` are treated as headers; skipped for units.
- Within a nonempty content line, split on whitespace following sentence-ending ``.``, ``!``, or ``?``
  (regex: ``(?<=[.!?])\\s+``). This is not linguistically perfect (abbreviations like ``e.g.`` can
  misfire); v0 prefers stability + falsifiability over NLP completeness.

Each emitted unit carries ``line_start == line_end`` equal to the source line index for v0
(sentences are not merged across lines).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_SPLIT = re.compile(r"(?<=[.!?])\s+")


@dataclass(frozen=True)
class SentenceUnit:
    """One capture unit with recap provenance (line-addressable)."""

    unit_id: str
    path: str
    line_start: int
    line_end: int
    text: str

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "unit_id": self.unit_id,
            "path": self.path,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "text": self.text,
        }


def _split_line_into_segments(line: str) -> list[str]:
    parts = [p.strip() for p in _SPLIT.split(line.strip())]
    return [p for p in parts if p]


def capture_sentence_units(*, recap_text: str, recap_relative_path: str) -> list[SentenceUnit]:
    lines = recap_text.splitlines()
    units: list[SentenceUnit] = []
    per_line_counter: dict[int, int] = {}
    for line_no, raw in enumerate(lines, start=1):
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        segments = _split_line_into_segments(raw)
        for seg in segments:
            per_line_counter[line_no] = per_line_counter.get(line_no, 0) + 1
            idx = per_line_counter[line_no]
            uid = f"u-L{line_no:04d}-{idx:02d}"
            units.append(
                SentenceUnit(
                    unit_id=uid,
                    path=recap_relative_path,
                    line_start=line_no,
                    line_end=line_no,
                    text=seg,
                )
            )
    return units


def capture_sentence_units_from_file(*, corpus_root: Path, recap_relative_path: str) -> list[SentenceUnit]:
    full = corpus_root / recap_relative_path
    text = full.read_text(encoding="utf-8")
    return capture_sentence_units(recap_text=text, recap_relative_path=recap_relative_path)


def units_to_jsonable(units: list[SentenceUnit]) -> list[dict[str, Any]]:
    return [u.to_json_dict() for u in units]
