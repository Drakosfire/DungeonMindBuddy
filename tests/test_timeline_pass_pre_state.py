"""Offline tests for Stage-2 v1 (autonomous timeline-pass) pre-state corpus builder.

Covers TP6 from EXPERIMENT-Session-Recap-Timeline-Pass-Benchmark.md: the four
APPEND-target timelines have no Session-20 row after pre-state build, the two
SKIP-target timelines match HEAD bytes, and the recap is pinned from gold.
"""

from __future__ import annotations

from pathlib import Path

import json

from evals.session_recap_timeline_pass_vertical_slice.step0_pre_state import (
    apply_pre_state_manifest,
    build_pre_state_corpus,
    load_pre_state_manifest,
)


_REPO_ROOT = Path(__file__).resolve().parents[1]
_LIVE_CORPUS = _REPO_ROOT / "corpus" / "eldyrwild-markdown"

_APPEND_TARGETS = [
    "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/timeline.md",
    "Longmont Campaign/Campaign 2/NPCs/sara_mirathorn_operator/timeline.md",
    "Longmont Campaign/Campaign 2/NPCs/thrin_branchborn/timeline.md",
    "Longmont Campaign/Campaign 2/PCs/caelynn/timeline.md",
    "Longmont Campaign/Campaign 2/PCs/karsemine/timeline.md",
    "Longmont Campaign/Campaign 2/PCs/ephanna/timeline.md",
]
_SKIP_TARGETS = [
    "Longmont Campaign/Campaign 2/NPCs/dustwalker/timeline.md",
    "Longmont Campaign/Campaign 2/NPCs/torbin_jove/timeline.md",
]


def test_pre_state_recap_pinned_from_gold(tmp_path: Path) -> None:
    root = build_pre_state_corpus(tmp_dir=tmp_path)
    recap = (
        root / "Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md"
    )
    assert recap.is_file()
    text = recap.read_text(encoding="utf-8")
    assert "# Session 20 Recap" in text
    assert "Lysandra" in text and "Caelynn" in text
    assert "Karsemine" in text and "Ephanna" in text and "Stafl" in text


def test_pre_state_strips_session_20_from_all_append_targets(tmp_path: Path) -> None:
    root = build_pre_state_corpus(tmp_dir=tmp_path)
    for rel in _APPEND_TARGETS:
        path = root / rel
        assert path.is_file(), rel
        body = path.read_text(encoding="utf-8")
        assert "| **20** |" not in body, f"{rel} still has a Session-20 row"
        # Sanity: prior session rows survive
        assert "**19**" in body or "**18**" in body, f"{rel} missing earlier rows"


def test_pre_state_leaves_skip_targets_untouched(tmp_path: Path) -> None:
    root = build_pre_state_corpus(tmp_dir=tmp_path)
    for rel in _SKIP_TARGETS:
        live = (_LIVE_CORPUS / rel).read_bytes()
        snapshot = (root / rel).read_bytes()
        assert live == snapshot, f"{rel} drifted from HEAD bytes during pre-state"


def test_manifest_documents_canonical_paths_and_skip_targets() -> None:
    man = load_pre_state_manifest()
    assert man["schema"] == "session_recap_timeline_pass_pre_state_v1"
    assert "copy_into_corpus" in man
    assert "remove_table_row_session_in" in man
    assert "leave_untouched_skip_targets" in man
    assert "canonical_corpus_reference" in man
    assert "Session 20 - Recap.md" in man["canonical_corpus_reference"]
    paths_in_remove = {
        str(spec["path"]) for spec in man["remove_table_row_session_in"]
    }
    for rel in _APPEND_TARGETS:
        assert rel in paths_in_remove, f"manifest missing remove spec for {rel}"
    for rel in _SKIP_TARGETS:
        assert rel in man["leave_untouched_skip_targets"], (
            f"manifest missing skip-target documentation for {rel}"
        )


def test_remove_row_idempotent(tmp_path: Path) -> None:
    root1 = build_pre_state_corpus(tmp_dir=tmp_path / "a")
    root2 = build_pre_state_corpus(tmp_dir=tmp_path / "b")
    for rel in _APPEND_TARGETS:
        b1 = (root1 / rel).read_bytes()
        b2 = (root2 / rel).read_bytes()
        assert b1 == b2, f"{rel} pre-state is not deterministic"
        assert b"| **20** |" not in b2


def test_apply_pre_state_delete_relative_paths(tmp_path: Path) -> None:
    root = tmp_path / "eldyrwild-markdown"
    root.mkdir(parents=True)
    victim = root / "Longmont Campaign/Campaign 2/PCs/caelynn/timeline.md"
    victim.parent.mkdir(parents=True, exist_ok=True)
    victim.write_text("stub", encoding="utf-8")
    apply_pre_state_manifest(
        root,
        {"delete_relative_paths": ["Longmont Campaign/Campaign 2/PCs/caelynn/timeline.md"]},
    )
    assert not victim.is_file()


def test_pre_state_c1_session1_manifest_seeds_and_deletes_c2_pc(tmp_path: Path) -> None:
    """C1 Stage B manifest removes duplicate C2 PC timelines and copies C1 seeds."""
    man_path = (
        _REPO_ROOT
        / "evals/session_recap_timeline_pass_vertical_slice/gold/step0_pre_state_manifest_session1_c1.json"
    )
    man = json.loads(man_path.read_text(encoding="utf-8"))
    root = build_pre_state_corpus(tmp_dir=tmp_path, manifest=man)
    c1 = root / "Longmont Campaign/Campaign 1/PCs/caelynn/timeline.md"
    assert c1.is_file()
    assert "longmont-c1" in c1.read_text(encoding="utf-8")
    c2 = root / "Longmont Campaign/Campaign 2/PCs/caelynn/timeline.md"
    assert not c2.is_file()
