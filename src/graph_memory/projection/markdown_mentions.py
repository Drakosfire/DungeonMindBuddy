"""Surface-neutral Markdown mention linking (PR #413).

Given Markdown and ``(surface, node_id)`` bindings, splice ``dmb-node:`` links
into the prose without corrupting existing Markdown. No graph, recap, or
surface vocabulary appears in this module's public signature, so every surface
that renders prose beside graph nodes pays for CommonMark protection once.

Pure: no I/O, no registry enrichment, no randomness.
"""

from __future__ import annotations

import re
from collections.abc import Sequence

from pydantic import BaseModel

AMBIGUOUS_MENTION_DIAGNOSTIC = "ambiguous_mention_surface"


class MentionBinding(BaseModel):
    """A literal text form that, when found in prose, denotes a durable node."""

    surface: str
    node_id: str


class LocatedMentionBinding(BaseModel):
    """Exact source span for a mention, already resolved to a durable node."""

    surface: str
    node_id: str
    start_offset: int
    end_offset: int


class MarkdownMention(BaseModel):
    mention_id: str
    node_id: str
    label: str
    start_offset: int | None = None
    end_offset: int | None = None


class MarkdownMentionDiagnostic(BaseModel):
    code: str
    message: str
    severity: str


def splice_node_link_spans(
    markdown: str,
    spans: list[tuple[int, int, str, str]],
) -> tuple[str, list[tuple[int, int] | None]]:
    """Splice `[label](dmb-node:node_id)` at each ``(start, end, label, node_id)``
    span (offsets given in the *original* ``markdown`` coordinates) and return the
    resulting markdown plus, for each input span (by original list position), its
    ``(start, end)`` offset in the *projected* string it was actually spliced into
    (or ``None`` if the span was dropped for overlapping an earlier one).

    This is the single place that turns a located mention span into the literal
    markdown link text the frontend renders as a pill. Every consumer (live
    auto-linking, gold anchor lookup) must go through this so mention offsets are
    always computed against the text they actually describe — offsets computed
    against pre-splice text drift out of alignment with every earlier span spliced
    in ahead of them, since each replacement is longer than the span it replaces.
    """
    occupied: list[tuple[int, int]] = []
    accepted: list[tuple[int, int, str, str, int]] = []
    for index, (start, end, label, node_id) in enumerate(spans):
        if any(start < used_end and end > used_start for used_start, used_end in occupied):
            continue
        occupied.append((start, end))
        accepted.append((start, end, label, node_id, index))

    accepted.sort(key=lambda item: item[0])

    pieces: list[str] = []
    projected_offsets: list[tuple[int, int] | None] = [None] * len(spans)
    cursor = 0
    projected_length = 0
    for start, end, label, node_id, index in accepted:
        prefix = markdown[cursor:start]
        pieces.append(prefix)
        projected_length += len(prefix)

        replacement = f"[{label}](dmb-node:{node_id})"
        mention_start = projected_length
        pieces.append(replacement)
        projected_length += len(replacement)
        projected_offsets[index] = (mention_start, projected_length)
        cursor = end

    pieces.append(markdown[cursor:])
    return "".join(pieces), projected_offsets


def _is_line_start(markdown: str, index: int) -> bool:
    return index == 0 or markdown[index - 1] == "\n"


def _skip_link_label(markdown: str, index: int) -> int | None:
    """Advance past a Markdown link/image label ``[...]`` starting at ``[``.

    Nested brackets are tracked by depth so ``[The [old] Caelynn Story]`` is
    one label, not a premature close at the inner ``]``.
    """
    if index >= len(markdown) or markdown[index] != "[":
        return None
    depth = 0
    i = index
    while i < len(markdown):
        ch = markdown[i]
        if ch == "\\":
            i += 2
            continue
        if ch == "\n":
            return None
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return None


def _skip_balanced_parens(markdown: str, index: int) -> int | None:
    """Advance past a ``(...)`` destination with nested parentheses."""
    if index >= len(markdown) or markdown[index] != "(":
        return None
    depth = 0
    i = index
    while i < len(markdown):
        ch = markdown[i]
        if ch == "\\":
            i += 2
            continue
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return i + 1
        elif ch == "\n":
            return None
        i += 1
    return None


def _normalize_reference_label(label: str) -> str:
    return re.sub(r"\s+", " ", label.strip()).casefold()


# Label + `:` + optional blanks (≤ one line ending). Destination and optional
# title are consumed by scanners so `<...>` destinations with spaces work.
_REFERENCE_DEFINITION_PREFIX_RE = re.compile(
    r"(?m)^[ \t]{0,3}\[((?:[^\]\\]|\\.)+)\]:"
    r"[ \t]*(?:\n[ \t]*)?"
)

# CommonMark absolute URI scheme: ASCII letter + 1–31 of [A-Za-z0-9+.-], then `:`.
_URI_AUTOLINK_SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]{1,31}:")


class _ReferenceDefinitionMatch:
    __slots__ = ("label", "start", "end")

    def __init__(self, *, label: str, start: int, end: int) -> None:
        self.label = label
        self.start = start
        self.end = end


def _skip_link_destination(markdown: str, index: int) -> int | None:
    """Advance past a CommonMark link destination starting at ``index``.

    Angle-bracket form ``<...>`` may contain spaces and is consumed through the
    matching unescaped ``>``. Bare destinations remain a non-whitespace run.
    """
    if index >= len(markdown):
        return None
    if markdown[index] == "<":
        i = index + 1
        n = len(markdown)
        while i < n:
            ch = markdown[i]
            if ch == "\\":
                i += 2
                continue
            if ch in "\n<":
                return None
            if ch == ">":
                return i + 1
            i += 1
        return None
    if markdown[index].isspace() or ord(markdown[index]) < 32:
        return None
    i = index
    n = len(markdown)
    while i < n and not markdown[i].isspace() and ord(markdown[i]) >= 32:
        i += 1
    return i if i > index else None


def _skip_link_title(markdown: str, index: int) -> int | None:
    """Advance past a CommonMark link title starting at a delimiter.

    Supports ``"..."``, ``'...'``, and ``(...)``. Titles may span lines, but a
    blank line before the matching unescaped closer rejects the title.
    """
    if index >= len(markdown):
        return None
    opener = markdown[index]
    if opener == '"':
        closer = '"'
    elif opener == "'":
        closer = "'"
    elif opener == "(":
        closer = ")"
    else:
        return None
    i = index + 1
    n = len(markdown)
    while i < n:
        ch = markdown[i]
        if ch == "\\":
            i += 2
            continue
        if ch == "\n":
            j = i + 1
            while j < n and markdown[j] in " \t":
                j += 1
            if j >= n or markdown[j] == "\n":
                return None
            i += 1
            continue
        if ch == closer:
            end = i + 1
            while end < n and markdown[end] in " \t":
                end += 1
            return end
        i += 1
    return None


def _match_reference_definition_at(
    markdown: str, index: int
) -> _ReferenceDefinitionMatch | None:
    """Parse one CommonMark link reference definition at a line start.

    Shared by label discovery and protected-range consumption so the two
    cannot drift. Optional titles may begin after zero or more spaces/tabs
    following one line ending (no indent required) and may be multiline.
    """
    if not _is_line_start(markdown, index):
        return None
    prefix = _REFERENCE_DEFINITION_PREFIX_RE.match(markdown, index)
    if prefix is None:
        return None
    label = prefix.group(1)
    dest_end = _skip_link_destination(markdown, prefix.end())
    if dest_end is None:
        return None
    pos = dest_end
    while pos < len(markdown) and markdown[pos] in " \t":
        pos += 1

    title_at: int | None = None
    if pos < len(markdown) and markdown[pos] in "\"'(":
        title_at = pos
    elif pos < len(markdown) and markdown[pos] == "\n":
        after_nl = pos + 1
        while after_nl < len(markdown) and markdown[after_nl] in " \t":
            after_nl += 1
        if after_nl < len(markdown) and markdown[after_nl] in "\"'(":
            title_at = after_nl

    if title_at is not None:
        title_end = _skip_link_title(markdown, title_at)
        if title_end is None:
            # Invalid title (e.g. blank line inside): definition ends at dest.
            return _ReferenceDefinitionMatch(
                label=label, start=index, end=dest_end
            )
        # No further non-whitespace may follow the title on its closing line.
        if title_end < len(markdown) and markdown[title_end] not in "\n":
            return None
        return _ReferenceDefinitionMatch(label=label, start=index, end=title_end)

    # No title: destination line may end here (EOL/EOF only).
    if pos < len(markdown) and markdown[pos] not in "\n":
        return None
    return _ReferenceDefinitionMatch(label=label, start=index, end=dest_end)


def _iter_reference_definitions(markdown: str):
    i = 0
    n = len(markdown)
    while i < n:
        if _is_line_start(markdown, i):
            match = _match_reference_definition_at(markdown, i)
            if match is not None:
                yield match
                i = match.end
                continue
        i += 1


def _reference_definition_labels(markdown: str) -> set[str]:
    """Labels defined by CommonMark ``[label]: destination`` definitions."""
    return {
        _normalize_reference_label(match.label)
        for match in _iter_reference_definitions(markdown)
    }


def _skip_autolink(markdown: str, index: int) -> int | None:
    """Advance past a CommonMark URI or email autolink ``<...>``."""
    if index >= len(markdown) or markdown[index] != "<":
        return None
    close = markdown.find(">", index + 1)
    if close < 0:
        return None
    inner = markdown[index + 1 : close]
    if not inner:
        return None
    for ch in inner:
        # Spaces, ASCII controls, and nested angle brackets are not allowed.
        if ch.isspace() or ch == "<" or ord(ch) < 32:
            return None
    if _URI_AUTOLINK_SCHEME_RE.match(inner):
        return close + 1
    if "@" in inner and "/" not in inner:
        return close + 1
    return None


def _skip_reference_definition_line(markdown: str, index: int) -> int | None:
    """Advance past a full CommonMark link reference definition."""
    match = _match_reference_definition_at(markdown, index)
    if match is None:
        return None
    return match.end


def _protected_ranges(markdown: str) -> list[tuple[int, int]]:
    """Ranges that must not receive mention rewrites: fences, code, links."""
    ranges: list[tuple[int, int]] = []
    ref_labels = _reference_definition_labels(markdown)
    i = 0
    n = len(markdown)
    while i < n:
        if _is_line_start(markdown, i):
            fence_match = re.match(r"[ \t]{0,3}(```+|~~~+)", markdown[i:])
            if fence_match:
                marker = fence_match.group(1)[0]
                fence_len = len(fence_match.group(1))
                start = i
                after_opener = i + fence_match.end()
                nl = markdown.find("\n", after_opener)
                scan_from = n if nl < 0 else nl + 1
                close_re = re.compile(
                    rf"(?m)^[ \t]{{0,3}}{re.escape(marker * fence_len)}+?[ \t]*$",
                )
                close = close_re.search(markdown, scan_from)
                end = n if close is None else close.end()
                ranges.append((start, end))
                i = end
                continue

            after_def = _skip_reference_definition_line(markdown, i)
            if after_def is not None:
                ranges.append((i, after_def))
                i = after_def
                continue

        # Matching-backtick code spans may contain line breaks (conservative).
        if markdown[i] == "`":
            run = 1
            while i + run < n and markdown[i + run] == "`":
                run += 1
            closer = markdown.find("`" * run, i + run)
            if closer != -1:
                end = closer + run
                ranges.append((i, end))
                i = end
                continue

        after_auto = _skip_autolink(markdown, i)
        if after_auto is not None:
            ranges.append((i, after_auto))
            i = after_auto
            continue

        if markdown[i] == "[" or (
            markdown[i] == "!" and i + 1 < n and markdown[i + 1] == "["
        ):
            start = i
            label_at = i + 1 if markdown[i] == "!" else i
            after_label = _skip_link_label(markdown, label_at)
            if after_label is not None:
                if after_label < n and markdown[after_label] == "(":
                    after_dest = _skip_balanced_parens(markdown, after_label)
                    if after_dest is not None:
                        ranges.append((start, after_dest))
                        i = after_dest
                        continue
                if after_label < n and markdown[after_label] == "[":
                    after_ref = _skip_link_label(markdown, after_label)
                    if after_ref is not None:
                        ranges.append((start, after_ref))
                        i = after_ref
                        continue
                # Shortcut reference link: [label] with a later [label]: def.
                label_text = markdown[label_at + 1 : after_label - 1]
                if _normalize_reference_label(label_text) in ref_labels:
                    # Do not consume a following non-link character.
                    ranges.append((start, after_label))
                    i = after_label
                    continue

        i += 1

    ranges.sort()
    return ranges


def _overlaps_protected(start: int, end: int, protected: list[tuple[int, int]]) -> bool:
    return any(start < used_end and end > used_start for used_start, used_end in protected)


def _surface_owners(
    bindings: Sequence[MentionBinding],
) -> dict[str, set[str]]:
    owners: dict[str, set[str]] = {}
    for binding in bindings:
        surface = (binding.surface or "").strip()
        if not surface:
            continue
        key = surface.casefold()
        owners.setdefault(key, set()).add(binding.node_id)
    return owners


def _project_markdown_mentions_free_only(
    markdown: str,
    bindings: Sequence[MentionBinding],
) -> tuple[str, list[MarkdownMention], list[MarkdownMentionDiagnostic]]:
    owners = _surface_owners(bindings)
    protected = _protected_ranges(markdown)
    diagnostics: list[MarkdownMentionDiagnostic] = []
    ambiguous_reported: set[str] = set()

    unique_surfaces: list[tuple[str, str]] = []
    for binding in bindings:
        surface = (binding.surface or "").strip()
        if not surface:
            continue
        key = surface.casefold()
        node_ids = owners.get(key, set())
        if len(node_ids) != 1:
            continue
        if node_ids != {binding.node_id}:
            continue
        unique_surfaces.append((surface, binding.node_id))

    # Length-descending only; equal lengths keep binding-list order (stable sort).
    unique_surfaces.sort(key=lambda item: -len(item[0]))
    seen_keys: set[str] = set()
    ordered: list[tuple[str, str]] = []
    for surface, node_id in unique_surfaces:
        key = surface.casefold()
        if key in seen_keys:
            continue
        seen_keys.add(key)
        ordered.append((surface, node_id))

    occupied: list[tuple[int, int]] = []
    matches: list[tuple[int, int, str, str]] = []
    for surface, node_id in ordered:
        pattern = re.compile(
            rf"(?<![\w\\[]){re.escape(surface)}(?![\w\\]])",
            re.IGNORECASE,
        )
        for match in pattern.finditer(markdown):
            start, end = match.span()
            if _overlaps_protected(start, end, protected):
                continue
            if any(start < used_end and end > used_start for used_start, used_end in occupied):
                continue
            occupied.append((start, end))
            matches.append((start, end, match.group(0), node_id))

    for key, node_ids in owners.items():
        if len(node_ids) < 2 or key in ambiguous_reported:
            continue
        sample = next(
            (
                (binding.surface or "").strip()
                for binding in bindings
                if (binding.surface or "").strip().casefold() == key
            ),
            key,
        )
        pattern = re.compile(
            rf"(?<![\w\\[]){re.escape(sample)}(?![\w\\]])",
            re.IGNORECASE,
        )
        for match in pattern.finditer(markdown):
            start, end = match.span()
            if _overlaps_protected(start, end, protected):
                continue
            ambiguous_reported.add(key)
            diagnostics.append(
                MarkdownMentionDiagnostic(
                    code=AMBIGUOUS_MENTION_DIAGNOSTIC,
                    message=(
                        f"Mention surface {sample!r} matches multiple projected "
                        f"nodes ({', '.join(sorted(node_ids))}); left unlinked."
                    ),
                    severity="warning",
                )
            )
            break

    matches.sort(key=lambda item: item[0])
    projected, offsets = splice_node_link_spans(markdown, matches)
    mentions: list[MarkdownMention] = []
    for (start, _end, label, node_id), offset in zip(matches, offsets, strict=True):
        if offset is None:
            continue
        mentions.append(
            MarkdownMention(
                mention_id=f"mention:{node_id}:{start}",
                node_id=node_id,
                label=label,
                start_offset=offset[0],
                end_offset=offset[1],
            )
        )
    return projected, mentions, diagnostics


def project_markdown_mentions(
    markdown: str,
    bindings: Sequence[MentionBinding],
    *,
    located_bindings: Sequence[LocatedMentionBinding] = (),
) -> tuple[str, list[MarkdownMention], list[MarkdownMentionDiagnostic]]:
    """Splice unique bound surfaces into ``dmb-node:`` links.

    Ambiguous surfaces (same case-insensitive text owned by multiple bound
    node ids) are left unchanged and emit ``ambiguous_mention_surface``.
    Protected Markdown/code ranges are never rewritten.

    ``bindings`` is order-significant and duplicates are meaningful: the
    ambiguity diagnostic quotes the first surface in this order with its
    original casing.

    ``located_bindings`` are processed first in caller order; invalid,
    protected, or overlapping located spans are skipped fail-closed without
    diagnostics.
    """
    if not located_bindings:
        return _project_markdown_mentions_free_only(markdown, bindings)

    protected = _protected_ranges(markdown)
    occupied: list[tuple[int, int]] = []
    located_matches: list[tuple[int, int, str, str]] = []
    for binding in located_bindings:
        start = binding.start_offset
        end = binding.end_offset
        surface = binding.surface
        if not (0 <= start < end <= len(markdown)):
            continue
        if markdown[start:end] != surface:
            continue
        if _overlaps_protected(start, end, protected):
            continue
        if any(start < used_end and end > used_start for used_start, used_end in occupied):
            continue
        occupied.append((start, end))
        located_matches.append((start, end, surface, binding.node_id))

    owners = _surface_owners(bindings)
    diagnostics: list[MarkdownMentionDiagnostic] = []
    ambiguous_reported: set[str] = set()

    unique_surfaces: list[tuple[str, str]] = []
    for binding in bindings:
        surface = (binding.surface or "").strip()
        if not surface:
            continue
        key = surface.casefold()
        node_ids = owners.get(key, set())
        if len(node_ids) != 1:
            continue
        if node_ids != {binding.node_id}:
            continue
        unique_surfaces.append((surface, binding.node_id))

    # Length-descending only; equal lengths keep binding-list order (stable sort).
    unique_surfaces.sort(key=lambda item: -len(item[0]))
    seen_keys: set[str] = set()
    ordered: list[tuple[str, str]] = []
    for surface, node_id in unique_surfaces:
        key = surface.casefold()
        if key in seen_keys:
            continue
        seen_keys.add(key)
        ordered.append((surface, node_id))

    matches: list[tuple[int, int, str, str]] = list(located_matches)
    for surface, node_id in ordered:
        pattern = re.compile(
            rf"(?<![\w\\[]){re.escape(surface)}(?![\w\\]])",
            re.IGNORECASE,
        )
        for match in pattern.finditer(markdown):
            start, end = match.span()
            if _overlaps_protected(start, end, protected):
                continue
            if any(start < used_end and end > used_start for used_start, used_end in occupied):
                continue
            occupied.append((start, end))
            matches.append((start, end, match.group(0), node_id))

    for key, node_ids in owners.items():
        if len(node_ids) < 2 or key in ambiguous_reported:
            continue
        sample = next(
            (
                (binding.surface or "").strip()
                for binding in bindings
                if (binding.surface or "").strip().casefold() == key
            ),
            key,
        )
        pattern = re.compile(
            rf"(?<![\w\\[]){re.escape(sample)}(?![\w\\]])",
            re.IGNORECASE,
        )
        for match in pattern.finditer(markdown):
            start, end = match.span()
            if _overlaps_protected(start, end, protected):
                continue
            ambiguous_reported.add(key)
            diagnostics.append(
                MarkdownMentionDiagnostic(
                    code=AMBIGUOUS_MENTION_DIAGNOSTIC,
                    message=(
                        f"Mention surface {sample!r} matches multiple projected "
                        f"nodes ({', '.join(sorted(node_ids))}); left unlinked."
                    ),
                    severity="warning",
                )
            )
            break

    matches.sort(key=lambda item: item[0])
    projected, offsets = splice_node_link_spans(markdown, matches)
    mentions: list[MarkdownMention] = []
    for (start, _end, label, node_id), offset in zip(matches, offsets, strict=True):
        if offset is None:
            continue
        mentions.append(
            MarkdownMention(
                mention_id=f"mention:{node_id}:{start}",
                node_id=node_id,
                label=label,
                start_offset=offset[0],
                end_offset=offset[1],
            )
        )
    return projected, mentions, diagnostics


__all__ = [
    "AMBIGUOUS_MENTION_DIAGNOSTIC",
    "LocatedMentionBinding",
    "MarkdownMention",
    "MarkdownMentionDiagnostic",
    "MentionBinding",
    "project_markdown_mentions",
    "splice_node_link_spans",
]
