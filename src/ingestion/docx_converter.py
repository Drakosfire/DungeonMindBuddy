from __future__ import annotations

import re
from pathlib import Path

from docx import Document
from docx.text.paragraph import Paragraph


_HEADING_STYLE_RE = re.compile(r"^Heading\s+(\d+)$", re.IGNORECASE)
_NUMBERED_SECTION_RE = re.compile(r"^\d+\.\s+\S")


def _render_paragraph_text(paragraph: Paragraph) -> str:
    """Render a paragraph preserving bold runs as markdown."""
    if not paragraph.runs:
        return paragraph.text.strip()

    pieces: list[str] = []
    for run in paragraph.runs:
        text = run.text
        if not text:
            continue
        if run.bold:
            pieces.append(f"**{text}**")
        else:
            pieces.append(text)
    return "".join(pieces).strip()


def _heading_level(style_name: str | None) -> int | None:
    if not style_name:
        return None
    match = _HEADING_STYLE_RE.match(style_name.strip())
    if not match:
        return None
    return max(1, min(6, int(match.group(1))))


def _is_bold_only_header(paragraph: Paragraph) -> bool:
    text = paragraph.text.strip()
    if not text or not paragraph.runs:
        return False
    has_text_run = False
    for run in paragraph.runs:
        if run.text.strip() == "":
            continue
        has_text_run = True
        if not run.bold:
            return False
    return has_text_run


def docx_to_markdown(docx_path: Path) -> str:
    """Convert a .docx document into markdown with heading detection."""
    document = Document(str(docx_path))
    lines: list[str] = []

    for paragraph in document.paragraphs:
        raw_text = paragraph.text.strip()
        if not raw_text:
            continue

        style_name = getattr(paragraph.style, "name", None)
        rendered_text = _render_paragraph_text(paragraph)

        level = _heading_level(style_name)
        if level is not None:
            lines.append(f"{'#' * level} {raw_text}")
            lines.append("")
            continue

        if _NUMBERED_SECTION_RE.match(raw_text):
            lines.append(f"## {raw_text}")
            lines.append("")
            continue

        if _is_bold_only_header(paragraph):
            lines.append(f"## {raw_text}")
            lines.append("")
            continue

        lines.append(rendered_text)
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def markdown_passthrough(md_path: Path) -> str:
    """Read markdown file contents as-is."""
    return md_path.read_text(encoding="utf-8")
