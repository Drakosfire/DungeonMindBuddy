"""Scope-A: Session 20 mechanical recap matches on-disk gold (A8)."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.agent.recap_ingest_helpers import assemble_recap

REPO_ROOT = Path(__file__).resolve().parents[1]
RAW_NOTES = REPO_ROOT / "Session 20 Recap.txt"
GOLD = (
    REPO_ROOT
    / "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps"
    / "Session 20 - Recap.md"
)


@pytest.mark.skipif(not RAW_NOTES.is_file(), reason="Session 20 Recap.txt missing")
@pytest.mark.skipif(not GOLD.is_file(), reason="gold Session 20 - Recap.md missing")
def test_session_20_recap_byte_equal_to_gold() -> None:
    raw = RAW_NOTES.read_text(encoding="utf-8")
    assembled, _report = assemble_recap(
        raw_notes=raw, session=20, campaign_id="longmont-c2"
    )
    gold_text = GOLD.read_text(encoding="utf-8")
    assert assembled == gold_text
