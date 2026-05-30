from __future__ import annotations

from pathlib import Path

import pytest

from src.live_play.recap_ingestion import ingest_recap_markdown

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/live_bootstrap/session_22_fresh_recap.md"


def test_ingestion_is_deterministic_for_fixture() -> None:
    first = ingest_recap_markdown(
        recap_path=FIXTURE,
        campaign_id="longmont-c2",
        planning_session=23,
        source_session=22,
    )
    second = ingest_recap_markdown(
        recap_path=FIXTURE,
        campaign_id="longmont-c2",
        planning_session=23,
        source_session=22,
    )
    assert first.model_dump() == second.model_dump()


def test_ingestion_extracts_entities_open_loops_and_beats() -> None:
    result = ingest_recap_markdown(
        recap_path=FIXTURE,
        campaign_id="longmont-c2",
        planning_session=23,
        source_session=22,
    )
    assert result.recap_title.startswith("Session 22")
    assert any("Lysandra" in entity.name for entity in result.candidate_entities)
    assert len(result.candidate_open_loops) >= 1
    assert len(result.candidate_planning_beats) >= 2
    assert all(beat.label.strip() for beat in result.candidate_planning_beats)


def test_empty_recap_fails(tmp_path: Path) -> None:
    empty = tmp_path / "empty.md"
    empty.write_text("   \n", encoding="utf-8")
    with pytest.raises(ValueError, match="empty"):
        ingest_recap_markdown(
            recap_path=empty,
            campaign_id="longmont-c2",
            planning_session=23,
        )


def test_invalid_utf8_recap_fails(tmp_path: Path) -> None:
    bad = tmp_path / "bad.md"
    bad.write_bytes(b"\xff\xfe")
    with pytest.raises(UnicodeDecodeError):
        bad.read_text(encoding="utf-8")
    with pytest.raises(UnicodeDecodeError):
        ingest_recap_markdown(
            recap_path=bad,
            campaign_id="longmont-c2",
            planning_session=23,
        )
