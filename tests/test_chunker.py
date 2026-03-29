from __future__ import annotations

from pathlib import Path

import pytest

from src.ingestion.chunker import (
    _build_heading_tree,
    _infer_session_from_section_path,
    _segment_blocks,
    chunk_document,
)


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


def test_infer_session_from_section_path() -> None:
    assert _infer_session_from_section_path(["Campaign 1", "Session 11 Recap"]) == 11
    assert _infer_session_from_section_path(["Longmont", "Session 12 - Aftermath"]) == 12
    assert _infer_session_from_section_path(["Longmont", "Recap"]) is None


def test_chunk_document_sets_inferred_session_from_headings(tmp_path: Path) -> None:
    md_path = tmp_path / "sessions.md"
    md_path.write_text(
        (
            "# Session 11 Recap\n\n"
            "The council meets and reviews long-form strategic notes for the city defenses.\n\n"
            "## Session 12 Recap\n\n"
            "The wolf is down and the party catalogs extensive post-fight aftermath details.\n"
        ),
        encoding="utf-8",
    )
    units = chunk_document(
        docx_path=md_path,
        document_id="doc_sessions",
        document_title="Sessions",
        canon_layer="campaign",
        campaign_id="longmont-c1",
        source_class="observed_session_recap",
    )

    sessions = {unit["inferred_session"] for unit in units}
    assert 11 in sessions
    assert 12 in sessions


def test_chunk_document_allows_custom_min_chars_for_aggressive_merge(tmp_path: Path) -> None:
    md_path = tmp_path / "aggressive_merge.md"
    md_path.write_text(
        (
            "# Section One\n\n"
            "This section is short.\n\n"
            "# Section Two\n\n"
            "This section is also short and should merge under aggressive settings.\n\n"
            "# Section Three\n\n"
            "This section is long enough to absorb previous chunks when min_chars is high.\n"
        ),
        encoding="utf-8",
    )

    default_units = chunk_document(
        docx_path=md_path,
        document_id="doc_default",
        document_title="Default Merge",
        canon_layer="world",
        campaign_id=None,
        source_class="seed_reference",
    )
    aggressive_units = chunk_document(
        docx_path=md_path,
        document_id="doc_aggressive",
        document_title="Aggressive Merge",
        canon_layer="world",
        campaign_id=None,
        source_class="seed_reference",
        min_chars=120,
    )

    assert len(aggressive_units) <= len(default_units)


def test_chunk_document_uses_frontmatter_metadata_when_present(tmp_path: Path) -> None:
    md_path = tmp_path / "battle.md"
    md_path.write_text(
        (
            "---\n"
            'title: "Battle with The Wolf and Aftermath"\n'
            "document_class: play\n"
            "canon_layer: campaign\n"
            "campaign_id: longmont-c1\n"
            "session: 8\n"
            "source_class: observed_session_recap\n"
            "---\n\n"
            "# Encounter\n\n"
            "The wolf receives a killing blow and falls in the council chamber.\n"
        ),
        encoding="utf-8",
    )

    units = chunk_document(docx_path=md_path)
    assert units
    assert all(unit["canon_layer"] == "campaign" for unit in units)
    assert all(unit["campaign_id"] == "longmont-c1" for unit in units)
    assert all(unit["source_class"] == "observed_session_recap" for unit in units)
    assert all(unit["inferred_session"] == 8 for unit in units)
    assert all(unit["document_session"] == 8 for unit in units)
    assert all(unit["document_type"] == "play_document" for unit in units)


def test_chunk_document_without_frontmatter_requires_metadata(tmp_path: Path) -> None:
    md_path = tmp_path / "notes.md"
    md_path.write_text("# Notes\n\nNo frontmatter present.\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Missing metadata and no frontmatter available"):
        chunk_document(docx_path=md_path)
