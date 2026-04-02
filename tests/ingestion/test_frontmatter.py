from __future__ import annotations

from pathlib import Path

import pytest

from src.ingestion.frontmatter import (
    FrontmatterParseError,
    FrontmatterValidationError,
    parse_document_frontmatter,
    render_frontmatter,
    write_document_with_frontmatter,
)
from src.ingestion.frontmatter_inference import infer_frontmatter_metadata_heuristic


def test_parse_document_frontmatter_valid_block() -> None:
    markdown = (
        "---\n"
        'title: "Battle with The Wolf and Aftermath"\n'
        "document_class: play\n"
        "canon_layer: campaign\n"
        "campaign_id: longmont-c1\n"
        "temporal_scope: session_specific\n"
        "session: 8\n"
        "origin_session: 8\n"
        "last_updated_session: 8\n"
        "source_class: observed_session_recap\n"
        "---\n"
        "# Body\n\nDetails.\n"
    )
    metadata, body = parse_document_frontmatter(markdown)
    assert metadata is not None
    assert metadata.document_class == "play"
    assert metadata.campaign_id == "longmont-c1"
    assert metadata.temporal_scope == "session_specific"
    assert metadata.session == 8
    assert metadata.origin_session == 8
    assert metadata.last_updated_session == 8
    assert body.startswith("# Body")


def test_parse_document_frontmatter_missing_returns_none() -> None:
    markdown = "# Heading\n\nParagraph\n---\nNot frontmatter"
    metadata, body = parse_document_frontmatter(markdown)
    assert metadata is None
    assert body == markdown


def test_parse_document_frontmatter_malformed_block_raises() -> None:
    markdown = (
        "---\n"
        "title Battle without colon\n"
        "document_class: play\n"
        "---\n"
        "# Body\n"
    )
    with pytest.raises(FrontmatterParseError):
        parse_document_frontmatter(markdown)


def test_parse_document_frontmatter_invalid_schema_raises() -> None:
    markdown = (
        "---\n"
        'title: "Play Doc"\n'
        "document_class: play\n"
        "canon_layer: campaign\n"
        "campaign_id: longmont-c1\n"
        "source_class: observed_session_recap\n"
        "---\n"
        "# Body\n"
    )
    with pytest.raises(FrontmatterValidationError):
        parse_document_frontmatter(markdown)


def test_render_and_write_frontmatter_round_trip(tmp_path: Path) -> None:
    body = "# Session Notes\n\nThe council argues."
    metadata = infer_frontmatter_metadata_heuristic(
        tmp_path / "Longmont Campaign/Campaign 1/Session 8 Recap.md",
        "Session recap follows.",
    )
    target = tmp_path / "session_8.md"
    write_document_with_frontmatter(target, metadata=metadata, body=body)

    written = target.read_text(encoding="utf-8")
    assert written.startswith("---\n")
    assert "document_class: play" in written
    assert render_frontmatter(metadata) in written


def test_infer_frontmatter_heuristic_world_default() -> None:
    metadata = infer_frontmatter_metadata_heuristic(
        Path("/tmp/Elderwyld/Cities/Mirathorn/The City of Mirathorn.md"),
        "Mirathorn overview and city notes.",
    )
    assert metadata.document_class == "world"
    assert metadata.canon_layer == "world"
    assert metadata.campaign_id is None
    assert metadata.session is None
    assert metadata.temporal_scope == "evergreen"
    assert metadata.origin_session is None
    assert metadata.last_updated_session is None
    assert metadata.source_class == "seed_reference"


def test_infer_frontmatter_heuristic_campaign_play() -> None:
    metadata = infer_frontmatter_metadata_heuristic(
        Path("/tmp/Longmont Campaign/Campaign 1/Battle with The Wolf and Aftermath.md"),
        "Session 8 recap. The wolf falls.",
    )
    assert metadata.document_class == "play"
    assert metadata.canon_layer == "campaign"
    assert metadata.campaign_id == "longmont-c1"
    assert metadata.session == 8
    assert metadata.temporal_scope == "session_specific"
    assert metadata.origin_session == 8
    assert metadata.last_updated_session == 8
    assert metadata.source_class == "observed_session_recap"

