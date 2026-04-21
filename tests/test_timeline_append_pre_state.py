"""Offline tests for Stage-2 pre-state corpus builder."""

from __future__ import annotations

from pathlib import Path

from evals.session_recap_timeline_append_vertical_slice.step0_pre_state import (
    build_pre_state_corpus,
    load_pre_state_manifest,
)


def test_pre_state_has_recap_and_no_session_20_timeline_row(tmp_path: Path) -> None:
    root = build_pre_state_corpus(tmp_dir=tmp_path)
    recap = (
        root
        / "Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md"
    )
    assert recap.is_file()
    text = recap.read_text(encoding="utf-8")
    assert "# Session 20 Recap" in text
    assert "Lysandra" in text

    tl = (
        root
        / "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/timeline.md"
    )
    assert tl.is_file()
    tl_text = tl.read_text(encoding="utf-8")
    assert "**19**" in tl_text and "Session 19 - Recap.md" in tl_text
    assert "| **20** |" not in tl_text


def test_manifest_documents_canonical_paths() -> None:
    man = load_pre_state_manifest()
    assert "copy_into_corpus" in man
    assert "canonical_corpus_reference" in man
    assert "Session 20 - Recap.md" in man["canonical_corpus_reference"]


def test_remove_row_idempotent(tmp_path: Path) -> None:
    root = build_pre_state_corpus(tmp_dir=tmp_path)
    tl = (
        root
        / "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/timeline.md"
    )
    first = tl.read_text(encoding="utf-8")
    # Second build should still not inject a stray row
    root2 = build_pre_state_corpus(tmp_dir=tmp_path / "other")
    tl2 = (
        root2
        / "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/timeline.md"
    )
    assert "| **20** |" not in tl2.read_text(encoding="utf-8")
    assert first == tl2.read_text(encoding="utf-8")
