"""Normalized literal anchor-quote matching within a single source paragraph.

Models emit verbatim ``anchor_quotes`` scoped to a ``source_span_ref_id`` paragraph.
This module validates those quotes with deterministic normalized literal search —
never model-authored regex — and returns raw ``char_start`` / ``char_end`` offsets
for presentation highlighting.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class AnchorQuoteMatch:
    quote: str
    char_start: int
    char_end: int
    match_text: str


# Unicode punctuation folds for quote/dash normalization (not full NFKC).
_QUOTE_FOLDS = {
    "\u2018": "'",
    "\u2019": "'",
    "\u201a": "'",
    "\u201b": "'",
    "\u201c": '"',
    "\u201d": '"',
    "\u201e": '"',
    "\u201f": '"',
    "\u2032": "'",
    "\u2033": '"',
}
_DASH_FOLDS = {
    "\u2010": "-",
    "\u2011": "-",
    "\u2012": "-",
    "\u2013": "-",
    "\u2014": "-",
    "\u2015": "-",
    "\u2212": "-",
}


def _fold_char(ch: str) -> str:
    if ch in _QUOTE_FOLDS:
        return _QUOTE_FOLDS[ch]
    if ch in _DASH_FOLDS:
        return _DASH_FOLDS[ch]
    return ch.casefold()


def normalize_for_match(text: str) -> str:
    """Collapse whitespace and fold case/punctuation for literal comparison."""
    norm, _ = _normalize_with_index_map(text)
    return norm


def _normalize_with_index_map(raw: str) -> tuple[str, list[int]]:
    """Build normalized text and map each norm char index -> raw string index."""
    norm_chars: list[str] = []
    index_map: list[int] = []
    pending_space = False
    for raw_idx, ch in enumerate(raw):
        folded = _fold_char(ch)
        if folded.isspace():
            if norm_chars and not pending_space:
                norm_chars.append(" ")
                index_map.append(raw_idx)
                pending_space = True
            continue
        pending_space = False
        norm_chars.append(folded)
        index_map.append(raw_idx)
    # trim trailing space
    if norm_chars and norm_chars[-1] == " ":
        norm_chars.pop()
        index_map.pop()
    return "".join(norm_chars), index_map


def _raw_span_for_norm_range(index_map: list[int], raw: str, norm_start: int, norm_end: int) -> tuple[int, int]:
    """Map a normalized [norm_start, norm_end) range to raw [char_start, char_end)."""
    if norm_start >= norm_end or not index_map:
        return 0, 0
    raw_start = index_map[norm_start]
    raw_end_idx = index_map[norm_end - 1]
    # Extend through any raw chars that fold to the last matched norm char (same codepoint).
    raw_end = raw_end_idx + 1
    while raw_end < len(raw) and raw[raw_end].casefold() == raw[raw_end_idx].casefold():
        raw_end += 1
    return raw_start, raw_end


def find_anchor_quote_matches(paragraph_text: str, quotes: list[str]) -> list[AnchorQuoteMatch]:
    """Find every normalized literal occurrence of each quote in ``paragraph_text``."""
    if not paragraph_text or not quotes:
        return []
    norm_para, index_map = _normalize_with_index_map(paragraph_text)
    if not norm_para:
        return []
    out: list[AnchorQuoteMatch] = []
    seen: set[tuple[str, int, int]] = set()
    for quote in quotes:
        q = (quote or "").strip()
        if not q:
            continue
        norm_quote = normalize_for_match(q)
        if not norm_quote:
            continue
        start = 0
        while True:
            pos = norm_para.find(norm_quote, start)
            if pos < 0:
                break
            end = pos + len(norm_quote)
            raw_start, raw_end = _raw_span_for_norm_range(index_map, paragraph_text, pos, end)
            match_text = paragraph_text[raw_start:raw_end]
            key = (q, raw_start, raw_end)
            if key not in seen:
                seen.add(key)
                out.append(
                    AnchorQuoteMatch(
                        quote=q,
                        char_start=raw_start,
                        char_end=raw_end,
                        match_text=match_text,
                    )
                )
            start = pos + 1
    return out


def quote_found_in_paragraph(paragraph_text: str, quote: str) -> bool:
    return bool(find_anchor_quote_matches(paragraph_text, [quote]))


def coerce_anchor_quotes(raw: Any) -> list[str]:
    """Normalize anchor_quotes field from pass JSON into a list of non-empty strings."""
    if raw is None:
        return []
    if isinstance(raw, str):
        s = raw.strip()
        return [s] if s else []
    if isinstance(raw, list):
        out: list[str] = []
        for item in raw:
            s = str(item).strip()
            if s:
                out.append(s)
        return out
    return []


def anchor_quote_matches_to_dicts(matches: list[AnchorQuoteMatch]) -> list[dict[str, Any]]:
    return [
        {
            "quote": m.quote,
            "char_start": m.char_start,
            "char_end": m.char_end,
            "match_text": m.match_text,
        }
        for m in matches
    ]
