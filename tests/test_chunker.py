from __future__ import annotations

from pathlib import Path

import pytest

from src.ingestion.chunker import _build_heading_tree, _segment_blocks, chunk_document


def test_build_heading_tree_nests_children() -> None:
    markdown = "# Root\n\n## Child\n\nParagraph text."
    blocks = _segment_blocks(markdown.splitlines())
    root = _build_heading_tree(blocks)

    assert len(root.children) == 1
    assert root.children[0].text == "Root"
    assert root.children[0].children[0].text == "Child"


def test_chunk_document_merges_small_sections(tmp_path: Path) -> None:
    md_path = tmp_path / "sample.md"
    md_path.write_text(
        "# Intro\n\nTiny.\n\n# Details\n\nThis is a longer section that should receive the merge from Intro.\n",
        encoding="utf-8",
    )

    units = chunk_document(
        docx_path=md_path,
        document_id="doc_sample",
        document_title="Sample",
        canon_layer="world",
        campaign_id=None,
        source_class="seed_reference",
    )

    assert len(units) >= 1
    assert units[0]["source_order_index"] == 0
    assert "Tiny." in units[0]["text"]
    assert "longer section" in units[0]["text"]
    assert all(len(unit["text"].strip()) >= 50 or unit is units[-1] for unit in units)


def test_chunk_document_outputs_schema_valid_units_for_mirathorn() -> None:
    mirathorn_path = Path(
        "/media/drakosfire/Projects/DungeonOverMind/DungeonMindBuddy/Docs/"
        "Eldyrwild and Campaign Context/Elderwyld/Cities and Towns/Mirathorn/"
        "The City of Mirathorn.docx"
    )
    if not mirathorn_path.exists():
        pytest.skip("Mirathorn corpus docx is not present on this machine")

    units = chunk_document(
        docx_path=mirathorn_path,
        document_id="doc_city_of_mirathorn",
        document_title="The City of Mirathorn",
        canon_layer="world",
        campaign_id=None,
        source_class="seed_reference",
    )

    assert units
    assert any("Mirathorn Overview" in unit["section_path"] for unit in units)
    assert all(unit["schema_version"] == "0.1.0" for unit in units)
