from __future__ import annotations

import re
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.hyperlink import Hyperlink
from docx.text.paragraph import Paragraph


_HEADING_STYLE_RE = re.compile(r"^Heading\s+(\d+)$", re.IGNORECASE)
_NUMBERED_SECTION_RE = re.compile(r"^\d+\.\s+\S")


def _render_paragraph_text(paragraph: Paragraph) -> str:
    """Render a paragraph preserving bold runs as markdown."""
    pieces: list[str] = []
    for item in paragraph.iter_inner_content():
        runs = item.runs if isinstance(item, Hyperlink) else [item]
        for run in runs:
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


def _table_to_markdown(table: Table) -> list[str]:
    """Render data rows without assuming the first row is a header."""
    rows: list[list[str]] = []
    for row in table.rows:
        values: list[str] = []
        for cell in row.cells:
            if cell._tc.findall(qn("w:tbl")):
                raise ValueError("Nested DOCX tables are not supported")
            tc_pr = cell._tc.tcPr
            if tc_pr is not None and (
                tc_pr.find(qn("w:gridSpan")) is not None
                or tc_pr.find(qn("w:vMerge")) is not None
            ):
                raise ValueError("Merged DOCX table cells are not supported")
            parts = [_render_paragraph_text(p) for p in cell.paragraphs]
            text = "<br>".join(part for part in parts if part)
            values.append(text.replace("\\", "\\\\").replace("|", "\\|").replace("\n", "<br>"))
        rows.append(values)
    if not rows:
        return []
    width = max(map(len, rows))
    if not width or any(len(row) != width for row in rows):
        raise ValueError("Irregular DOCX tables are not supported")
    def render_row(values: list[str]) -> str:
        return "| " + " | ".join(values) + " |"

    return [render_row([""] * width), render_row(["---"] * width), *(render_row(row) for row in rows)]


def docx_to_markdown(docx_path: Path) -> str:
    """Convert a .docx document into markdown with heading detection."""
    document = Document(str(docx_path))
    lines: list[str] = []

    for element in document.element.body:
        if element.tag == qn("w:tbl"):
            lines.extend(_table_to_markdown(Table(element, document)))
            lines.append("")
            continue
        if element.tag != qn("w:p"):
            continue
        paragraph = Paragraph(element, document)
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
