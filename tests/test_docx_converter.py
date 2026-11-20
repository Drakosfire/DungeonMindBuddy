from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.oxml import OxmlElement
import pytest

from ingestion.docx_converter import docx_to_markdown, markdown_passthrough


def test_docx_to_markdown_style_and_fallback_detection(tmp_path: Path) -> None:
    doc = Document()
    doc.add_heading("Mirathorn Overview", level=1)
    doc.add_paragraph("Founded over 200 years ago.")
    doc.add_paragraph("1. Watch Tower")
    p_bold = doc.add_paragraph()
    p_bold.add_run("Temple of the Nameless Stone").bold = True
    p_text = doc.add_paragraph()
    p_text.add_run("A ")
    p_text.add_run("prosperous").bold = True
    p_text.add_run(" city.")

    out_path = tmp_path / "sample.docx"
    doc.save(out_path)

    markdown = docx_to_markdown(out_path)

    assert "# Mirathorn Overview" in markdown
    assert "## 1. Watch Tower" in markdown
    assert "## Temple of the Nameless Stone" in markdown
    assert "A **prosperous** city." in markdown


def test_markdown_passthrough_reads_file(tmp_path: Path) -> None:
    md_path = tmp_path / "sample.md"
    md_path.write_text("# Title\n\nBody\n", encoding="utf-8")
    assert markdown_passthrough(md_path) == "# Title\n\nBody\n"


def test_table_content_stays_between_surrounding_paragraphs(tmp_path: Path) -> None:
    doc = Document()
    doc.add_paragraph("Before the table")
    table = doc.add_table(rows=2, cols=2)
    table.cell(0, 0).text = "First | second"
    table.cell(0, 1).text = "First line\nSecond line"
    table.cell(1, 0).text = "Another cell"
    table.cell(1, 1).text = "Final cell"
    doc.add_paragraph("After the table")
    path = tmp_path / "table.docx"
    doc.save(path)

    result = docx_to_markdown(path)

    assert result == (
        "Before the table\n\n"
        "|  |  |\n| --- | --- |\n"
        "| First \\| second | First line<br>Second line |\n"
        "| Another cell | Final cell |\n\nAfter the table\n"
    )


def test_table_hyperlink_text_is_not_dropped(tmp_path: Path) -> None:
    doc = Document()
    table = doc.add_table(rows=1, cols=1)
    paragraph = table.cell(0, 0).paragraphs[0]
    paragraph.add_run("See ")
    hyperlink = OxmlElement("w:hyperlink")
    run = OxmlElement("w:r")
    text = OxmlElement("w:t")
    text.text = "the clue"
    run.append(text)
    hyperlink.append(run)
    paragraph._p.append(hyperlink)
    paragraph.add_run(" nearby.")
    path = tmp_path / "link.docx"
    doc.save(path)

    assert "See the clue nearby." in docx_to_markdown(path)


def test_nonbold_hyperlink_prevents_bold_paragraph_becoming_heading(tmp_path: Path) -> None:
    doc = Document()
    paragraph = doc.add_paragraph()
    paragraph.add_run("Bold introduction ").bold = True
    hyperlink = OxmlElement("w:hyperlink")
    run = OxmlElement("w:r")
    text = OxmlElement("w:t")
    text.text = "ordinary link"
    run.append(text)
    hyperlink.append(run)
    paragraph._p.append(hyperlink)
    path = tmp_path / "paragraph.docx"
    doc.save(path)

    assert docx_to_markdown(path) == "**Bold introduction **ordinary link\n"


@pytest.mark.parametrize("shape", ["nested", "merged"])
def test_unsupported_table_structure_fails_without_silent_loss(tmp_path: Path, shape: str) -> None:
    doc = Document()
    table = doc.add_table(rows=1, cols=2)
    if shape == "nested":
        table.cell(0, 0).add_table(rows=1, cols=1)
    else:
        table.cell(0, 0).merge(table.cell(0, 1))
    path = tmp_path / "unsupported.docx"
    doc.save(path)

    with pytest.raises(ValueError, match="DOCX table"):
        docx_to_markdown(path)
