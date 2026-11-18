"""Pure helpers for mechanical session-recap ingest (Scope-A; no IO, no LLM).

Used by the recap-write workflow and by Scope-A gold tests.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_SENTENCE_END_RE = re.compile(r"""[.!?…]["'\u201d]?\s*$|[.!?…]\s*$""")
_TITLE_LINE_RE_TEMPLATE = r"^\s*Session\s+{n}\s+Recap\s*:?\s*$"

# Common English abbreviations that end with `.` but do NOT terminate a sentence.
# Conservative set: only entries that frequently appear at end-of-line in GM notes.
# Compared case-sensitively against the line's last whitespace-delimited token.
_ABBREVIATIONS: frozenset[str] = frozenset(
    {
        "Dr.", "Mr.", "Mrs.", "Ms.", "Prof.", "Sr.", "Jr.",
        "St.", "Capt.", "Lt.", "Sgt.", "Col.", "Gen.", "Maj.", "Pvt.",
        "vs.", "etc.", "e.g.", "i.e.", "cf.", "al.", "No.",
        "Inc.", "Co.", "Ltd.", "approx.", "fig.", "ch.", "p.", "pp.",
    }
)

# Characters that open a paragraph wrapper around the actual capitalized first letter.
# (Straight + curly quotes, em/en dash, hyphen — used to open dialogue or scene cuts.)
_LEADING_PARAGRAPH_OPENERS_RE = re.compile(
    r'^["\u201c\u2018\u2019\u2014\u2013\-]+'
)


@dataclass(frozen=True)
class Paragraph:
    text: str
    source_line_start: int
    source_line_end: int


@dataclass(frozen=True)
class DuplicateMatch:
    a: Paragraph
    b: Paragraph


@dataclass(frozen=True)
class IngestReport:
    title_line_stripped: bool
    duplicates_detected: list[DuplicateMatch]
    duplicates_removed: list[DuplicateMatch]
    paragraph_count_in: int
    paragraph_count_out: int


def _normalize_for_dup(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _ends_with_known_abbreviation(line: str) -> bool:
    """Return True when the last whitespace-token is a known non-terminal abbreviation."""
    s = line.rstrip()
    if not s or not s.endswith("."):
        return False
    last_token = s.split()[-1]
    return last_token in _ABBREVIATIONS


def _ends_sentence(line: str) -> bool:
    """True when the line looks like the end of a sentence (and not a known abbreviation)."""
    s = line.rstrip()
    if not s:
        return False
    if not _SENTENCE_END_RE.search(s):
        return False
    if _ends_with_known_abbreviation(s):
        return False
    return True


def _starts_new_paragraph_line(line: str) -> bool:
    """True when the line begins a new paragraph.

    Accepts the obvious case (uppercase first character) and the dialogue case
    (one or more opening quote / dash characters wrapping an uppercase letter).
    """
    s = line.lstrip()
    if not s:
        return False
    if s[0].isupper():
        return True
    inner = _LEADING_PARAGRAPH_OPENERS_RE.sub("", s)
    if inner and inner[0].isupper():
        return True
    return False


def _join_para_lines(parts: list[tuple[int, str]]) -> str:
    if len(parts) == 1:
        return parts[0][1]
    return " ".join(p[1].rstrip() for p in parts)


def split_paragraphs_robust(
    numbered_lines: list[tuple[int, str]],
) -> list[Paragraph]:
    """Split on blank lines and on single newlines after sentence-complete lines.

    ``numbered_lines`` is ``(file_line_no, text)`` for every line of the transcript
    after any title strip, in order.
    """
    paragraphs: list[Paragraph] = []
    current: list[tuple[int, str]] = []

    def flush() -> None:
        nonlocal current
        if not current:
            return
        text = _join_para_lines(current)
        paragraphs.append(
            Paragraph(
                text=text,
                source_line_start=current[0][0],
                source_line_end=current[-1][0],
            )
        )
        current = []

    for _line_no, raw in numbered_lines:
        if not raw.strip():
            flush()
            continue
        if not current:
            current.append((_line_no, raw))
            continue
        prev_text = current[-1][1]
        if _ends_sentence(prev_text) and _starts_new_paragraph_line(raw):
            flush()
            current.append((_line_no, raw))
        else:
            current.append((_line_no, raw))
    flush()
    return paragraphs


def detect_duplicate_paragraphs(paragraphs: list[Paragraph]) -> list[DuplicateMatch]:
    """Pair paragraphs that match after whitespace normalization."""
    matches: list[DuplicateMatch] = []
    by_norm: dict[str, Paragraph] = {}
    for p in paragraphs:
        key = _normalize_for_dup(p.text)
        if not key:
            continue
        if key in by_norm:
            matches.append(DuplicateMatch(a=by_norm[key], b=p))
        else:
            by_norm[key] = p
    return matches


def strip_leading_title_line(body: str, session_number: int) -> tuple[str, bool]:
    """If the first non-blank line matches ``Session {N} Recap[:]?``, remove that line."""
    lines = body.splitlines(keepends=False)
    title_re = re.compile(
        _TITLE_LINE_RE_TEMPLATE.format(n=session_number), re.IGNORECASE
    )
    first_idx = next((i for i, ln in enumerate(lines) if ln.strip()), None)
    if first_idx is None:
        return body, False
    if not title_re.match(lines[first_idx].strip()):
        return body, False
    rest = lines[:first_idx] + lines[first_idx + 1 :]
    out = "\n".join(rest)
    return out, True


def numbered_lines_for_recap(
    raw_notes: str, session: int
) -> tuple[list[tuple[int, str]], bool]:
    """All lines with original 1-based line numbers, excluding a leading session title line."""
    all_lines = raw_notes.splitlines(keepends=False)
    title_re = re.compile(_TITLE_LINE_RE_TEMPLATE.format(n=session), re.IGNORECASE)
    first_idx = next((i for i, ln in enumerate(all_lines) if ln.strip()), None)
    stripped = False
    if first_idx is not None and title_re.match(all_lines[first_idx].strip()):
        numbered = [(i + 1, all_lines[i]) for i in range(len(all_lines)) if i != first_idx]
        stripped = True
    else:
        numbered = [(i + 1, all_lines[i]) for i in range(len(all_lines))]
    return numbered, stripped


def emit_recap_frontmatter(
    *, session: int, campaign_id: str, title: str | None = None
) -> str:
    """Emit the 8-field YAML frontmatter block (ends with ``---`` and one blank line)."""
    if title is None:
        title = f"Session {session} - Recap"
    lines = [
        "---",
        f'title: "{title}"',
        "document_class: play",
        "canon_layer: campaign",
        f"campaign_id: {campaign_id}",
        "temporal_scope: session_specific",
        f"session: {session}",
        f"origin_session: {session}",
        f"last_updated_session: {session}",
        "source_class: observed_session_recap",
        "---",
        "",
    ]
    return "\n".join(lines)


def assemble_recap(
    *,
    raw_notes: str,
    session: int,
    campaign_id: str,
    title: str | None = None,
    remove_duplicates: bool = True,
) -> tuple[str, IngestReport]:
    """Compose frontmatter + H1 + body; optionally drop repeated paragraphs (keep first)."""
    numbered, title_stripped = numbered_lines_for_recap(raw_notes, session)
    paragraphs_in = split_paragraphs_robust(numbered)
    dupes = detect_duplicate_paragraphs(paragraphs_in)

    removed: list[DuplicateMatch] = []
    if remove_duplicates:
        seen: dict[str, Paragraph] = {}
        paragraphs_out: list[Paragraph] = []
        for p in paragraphs_in:
            key = _normalize_for_dup(p.text)
            if key:
                if key in seen:
                    removed.append(DuplicateMatch(a=seen[key], b=p))
                    continue
                seen[key] = p
            paragraphs_out.append(p)
    else:
        paragraphs_out = list(paragraphs_in)

    body = "\n\n".join(p.text for p in paragraphs_out)
    fm = emit_recap_frontmatter(session=session, campaign_id=campaign_id, title=title)
    h1 = f"# Session {session} Recap"
    full = f"{fm}{h1}\n\n{body}\n"

    report = IngestReport(
        title_line_stripped=title_stripped,
        duplicates_detected=dupes,
        duplicates_removed=removed,
        paragraph_count_in=len(paragraphs_in),
        paragraph_count_out=len(paragraphs_out),
    )
    return full, report
