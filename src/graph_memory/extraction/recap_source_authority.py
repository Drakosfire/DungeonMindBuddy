"""Defer explicitly marked planning material without rewriting source spans."""
from __future__ import annotations

import hashlib
import json
import re
from bisect import bisect_left
from collections.abc import Callable, Mapping, Sequence
from itertools import accumulate
from typing import Any

from markdown_it import MarkdownIt

_PLANNING_TITLES = {"looking ahead", "next beats", "planning notes", "prep notes"}
_HEADING = re.compile(r"^ {0,3}(#{1,6})\s+(.+?)\s*#*\s*$")
_INLINE = re.compile(r"^\s*(?:\*\*|__)?\s*(?:looking\s+ahead|next\s+beats|planning\s+notes|prep\s+notes)\s*:\s*(?:\*\*|__)?", re.I)
_LABEL_TITLE = r"looking\s+ahead|next\s+beats|planning\s+notes|prep\s+notes|recap"
_SECTION_LABEL = re.compile(
    rf"^ {{0,3}}(?:(?P<em>\*\*|__)\s*(?P<marked>{_LABEL_TITLE})\s*:?\s*(?P=em)\s*:?"
    rf"|(?P<plain>{_LABEL_TITLE})\s*:)\s*$", re.I,
)
# Same-line prose is structural only when the colon is inside balanced emphasis.
_MARKED_RECAP_PREFIX = re.compile(r"^ {0,3}(?P<em>\*\*|__)\s*recap\s*:\s*(?P=em)", re.I)
_FENCE_OPEN = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
_FENCE_CLOSE = re.compile(r"^ {0,3}(`{3,}|~{3,})[ \t]*$")


def partition_recap_source_rows(
    rows: Sequence[dict[str, Any]], text: str | None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """Mixed spans are deferred whole; offsets and original text remain frozen.

    This recognizes structural labels only. It does not classify prophecy,
    quotations, arbitrary future tense or unmarked preparation prose.
    """
    if text is None:
        return list(rows), [], {"checked": False, "reason": "full_source_text_unavailable"}
    lines = text.splitlines()
    # CommonMark counts CR/LF lines; source rows use Python splitlines, which
    # also counts Unicode separators. Translate through original character
    # boundaries rather than changing the source row/offset contract.
    source_boundaries = list(accumulate(map(len, text.splitlines(keepends=True)), initial=0))
    markdown_boundaries = [0, *(match.end() for match in re.finditer(r"\r\n|\r|\n", text))]
    if markdown_boundaries[-1] != len(text):
        markdown_boundaries.append(len(text))
    source_line_for_boundary = [bisect_left(source_boundaries, offset) + 1 for offset in markdown_boundaries]
    # Blockquote maps include lazy continuations without a leading `>`.
    quoted_lines = {
        number
        for token in MarkdownIt("commonmark").parse(text)
        if token.type == "blockquote_open" and token.map is not None
        for number in range(source_line_for_boundary[token.map[0]], source_line_for_boundary[token.map[1]])
    }
    planned: set[int] = set()
    section_level: int | None = None
    label_section = False
    inline = False
    fence: str | None = None
    for number, line in enumerate(lines, 1):
        if number in quoted_lines:
            if section_level is not None or label_section or inline:
                planned.add(number)
            continue
        if fence is not None:
            closing = _FENCE_CLOSE.match(line)
            if closing:
                token = closing.group(1)
                if token[0] == fence[0] and len(token) >= len(fence):
                    fence = None
            if section_level is not None or label_section or inline:
                planned.add(number)
            continue

        opening = _FENCE_OPEN.match(line)
        if opening and not (opening.group(1).startswith("`") and "`" in opening.group(2)):
            fence = opening.group(1)
            if section_level is not None or label_section or inline:
                planned.add(number)
            continue
        split_recap = (
            line.strip().casefold() in {"**recap:", "__recap:"}
            and number < len(lines)
            and lines[number].lstrip().startswith(line.strip()[:2])
        )
        label_match = _SECTION_LABEL.match(line)
        label = None
        if label_match:
            title = label_match.group("marked") or label_match.group("plain")
            label = " ".join(title.casefold().split())
        if label == "recap" or split_recap or _MARKED_RECAP_PREFIX.match(line):
            section_level = None
            label_section = False
            inline = False
            continue
        if label in _PLANNING_TITLES:
            # A label-only paragraph introduces a section, unlike an inline
            # note whose planning authority ends at the next blank line.
            label_section = True
            inline = False
            planned.add(number)
            continue
        heading = _HEADING.match(line)
        if heading:
            inline = False
            level = len(heading.group(1))
            title = heading.group(2).strip(" *_:").casefold()
            # Inspect the heading label, never the meaning of its inline payload.
            planning_title = " ".join(title.partition(":")[0].strip(" *_").split())
            if label_section and title == "recap":
                label_section = False
                section_level = None
            if section_level is not None and level <= section_level:
                section_level = None
            if planning_title in _PLANNING_TITLES and section_level is None:
                section_level = level
        elif not line.strip():
            inline = False
        elif _INLINE.match(line):
            inline = True
        if section_level is not None or label_section or inline:
            planned.add(number)
    kept, withheld, mixed = [], [], []
    for row in rows:
        substantive = {n for n in range(row["line_start"], row["line_end"] + 1)
                       if 1 <= n <= len(lines) and lines[n - 1].strip()}
        if substantive & planned:
            withheld.append(row)
            if substantive - planned:
                mixed.append(row["source_span_ref_id"])
        else:
            kept.append(row)
    return kept, withheld, {"checked": True, "withheld_span_ids": [r["source_span_ref_id"] for r in withheld], "mixed_span_ids": mixed}


def deferred_source_rows(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [{"item_id": "deferred:planning:" + hashlib.sha256(r["source_span_ref_id"].encode()).hexdigest()[:16],
             "label": "Planning source material", "reason": "Explicit planning section or mixed source span; not played-event evidence.",
             "suggested_next_step": "Review the original passage as preparation material.",
             "evidence_refs": [{"source_span_ref_id": r["source_span_ref_id"], "anchor_quotes": [r["text"]]}]}
            for r in rows]


def filter_planning_pass_output(
    parsed: Mapping[str, Any], blocked: set[str],
    canonicalize: Callable[[str, set[str]], str | None],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Do not salvage mixed claims by stripping only their planning citation."""
    out, deferred = dict(parsed), []
    if not blocked:
        return out, deferred
    for key, records in parsed.items():
        if key in {"ignored_items", "deferred_items"} or not isinstance(records, list):
            continue
        kept = []
        for record in records:
            refs = record.get("evidence_refs", []) if isinstance(record, Mapping) else []
            cites_planning = any(isinstance(ref, Mapping) and
                                 canonicalize(str(ref.get("source_span_ref_id", "")), blocked)
                                 for ref in refs)
            if not cites_planning:
                kept.append(record)
                continue
            identity = str(record.get("node_id") or record.get("edge_id") or record.get("beat_id") or record.get("label") or key)
            deferred.append({"item_id": "deferred:planning-claim:" + hashlib.sha256(json.dumps({"key": key, "record": record}, sort_keys=True).encode()).hexdigest()[:16],
                             "label": str(record.get("label") or record.get("title") or identity),
                             "reason": "Positive claim cites withheld planning material; entire claim deferred for review.",
                             "evidence_refs": list(refs)})
        out[key] = kept
    return out, deferred
