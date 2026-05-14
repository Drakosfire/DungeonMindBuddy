"""Deterministic recap line -> sentence-ish units (``capture_sentence_units`` scaffold; legacy: Stage A).

Split policy (v0, intentionally simple):
- One-based line numbers into the recap file.
- Blank lines separate story chunks for humans but do not emit units.
- Lines whose stripped text starts with ``#`` are treated as headers; skipped for units.
- Within a nonempty content line, split on whitespace following sentence-ending ``.``, ``!``, or ``?``
  (regex: ``(?<=[.!?])\\s+``). Each unit's ``text`` begins at the recap byte immediately after the
  prior unit's end through the end of its clause, so newlines and indentation between lines are
  preserved (e.g. ``...with 4.`` then blank lines then ``1:``). This is not linguistically perfect
  (abbreviations like ``e.g.`` can misfire); v0 prefers stability + falsifiability over NLP
  completeness.

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


@dataclass(frozen=True)
class SentenceUnitSpan:
    """Sentence unit plus absolute ``[body_start, body_end)`` offsets into ``recap_text``."""

    unit_id: str
    path: str
    line_start: int
    line_end: int
    text: str
    body_start: int
    body_end: int

    def to_json_dict(self) -> dict[str, Any]:
        return {
            **SentenceUnit(
                unit_id=self.unit_id,
                path=self.path,
                line_start=self.line_start,
                line_end=self.line_end,
                text=self.text,
            ).to_json_dict(),
            "body_start": self.body_start,
            "body_end": self.body_end,
        }


def line_start_offsets(recap_text: str) -> list[int]:
    """Char offset of each line returned by ``splitlines()`` (supports ``\\n`` / ``\\r\\n``)."""
    lines = recap_text.splitlines()
    starts: list[int] = []
    pos = 0
    for i, ln in enumerate(lines):
        starts.append(pos)
        pos += len(ln)
        if i < len(lines) - 1:
            if pos < len(recap_text) and recap_text[pos] == "\r":
                pos += 1
            if pos < len(recap_text) and recap_text[pos] == "\n":
                pos += 1
    return starts


def _split_line_into_segments(line: str) -> list[str]:
    parts = [p.strip() for p in _SPLIT.split(line.strip())]
    return [p for p in parts if p]


def _line_segment_boundaries(raw_line: str) -> list[tuple[int, int]]:
    """Return ``(idx, end)`` for each stripped clause segment within ``raw_line`` (local indices)."""
    stripped = raw_line.strip()
    if not stripped or stripped.startswith("#"):
        return []
    segments = _split_line_into_segments(raw_line)
    if not segments:
        return []
    lead = len(raw_line) - len(raw_line.lstrip())
    cursor = lead
    out: list[tuple[int, int]] = []
    for seg in segments:
        idx = raw_line.find(seg, cursor)
        if idx < 0:
            raise ValueError(
                "sentence unit boundary: segment not found — "
                f"seg={seg!r} raw_line={raw_line!r}"
            )
        end = idx + len(seg)
        out.append((idx, end))
        cursor = end
    return out


def capture_sentence_units(*, recap_text: str, recap_relative_path: str) -> list[SentenceUnit]:
    lines = recap_text.splitlines()
    starts = line_start_offsets(recap_text)
    if len(lines) != len(starts):
        raise ValueError("internal error: splitlines vs line_start_offsets length mismatch")
    units: list[SentenceUnit] = []
    per_line_counter: dict[int, int] = {}
    last_body_end: int | None = None
    for line_no, raw in enumerate(lines, start=1):
        line_base = starts[line_no - 1]
        for idx, end in _line_segment_boundaries(raw):
            abs_start = line_base + idx
            abs_end = line_base + end
            piece_start = abs_start if last_body_end is None else last_body_end
            text = recap_text[piece_start:abs_end]
            last_body_end = abs_end
            per_line_counter[line_no] = per_line_counter.get(line_no, 0) + 1
            uidx = per_line_counter[line_no]
            uid = f"u-L{line_no:04d}-{uidx:02d}"
            units.append(
                SentenceUnit(
                    unit_id=uid,
                    path=recap_relative_path,
                    line_start=line_no,
                    line_end=line_no,
                    text=text,
                )
            )
    return units


def capture_sentence_unit_spans(*, recap_text: str, recap_relative_path: str) -> list[SentenceUnitSpan]:
    """Same segmentation as ``capture_sentence_units`` with char spans for deterministic tag injection."""
    lines = recap_text.splitlines()
    starts = line_start_offsets(recap_text)
    if len(lines) != len(starts):
        raise ValueError("internal error: splitlines vs line_start_offsets length mismatch")
    units: list[SentenceUnitSpan] = []
    per_line_counter: dict[int, int] = {}
    last_body_end: int | None = None
    for line_no, raw in enumerate(lines, start=1):
        line_base = starts[line_no - 1]
        for idx, end in _line_segment_boundaries(raw):
            abs_start = line_base + idx
            abs_end = line_base + end
            piece_start = abs_start if last_body_end is None else last_body_end
            text = recap_text[piece_start:abs_end]
            last_body_end = abs_end
            per_line_counter[line_no] = per_line_counter.get(line_no, 0) + 1
            uidx = per_line_counter[line_no]
            uid = f"u-L{line_no:04d}-{uidx:02d}"
            units.append(
                SentenceUnitSpan(
                    unit_id=uid,
                    path=recap_relative_path,
                    line_start=line_no,
                    line_end=line_no,
                    text=text,
                    body_start=piece_start,
                    body_end=abs_end,
                )
            )
    return units


def capture_sentence_units_from_file(*, corpus_root: Path, recap_relative_path: str) -> list[SentenceUnit]:
    full = corpus_root / recap_relative_path
    text = full.read_text(encoding="utf-8")
    return capture_sentence_units(recap_text=text, recap_relative_path=recap_relative_path)


def units_to_jsonable(units: list[SentenceUnit]) -> list[dict[str, Any]]:
    return [u.to_json_dict() for u in units]
