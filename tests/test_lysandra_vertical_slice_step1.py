"""Step 1 retrieval gates (Lysandra vertical slice)."""

from __future__ import annotations

import pytest

from evals.lysandra_vertical_slice.step1_retrieval import (
    keyword_scan_ranked,
    load_corpus_policy,
    load_step1_gold,
    run_step1_gates,
    run_step1_keyword_scan_and_gates,
    score_text_for_aliases,
)


def test_step1_gold_and_policy_parse() -> None:
    g = load_step1_gold()
    assert g.get("required_paths_retrieved")
    p = load_corpus_policy()
    assert p.get("aliases")


def test_score_text_counts_aliases() -> None:
    text = "Captain Lysandra Ironveil met Lysandra again."
    assert score_text_for_aliases(text, ["Lysandra", "Captain Lysandra Ironveil"]) >= 3


def test_g1_3_rejects_path_outside_allowed_roots() -> None:
    policy = load_corpus_policy()
    g1 = load_step1_gold()
    ranked = [
        ("Longmont Campaign/foo.md", 9),
        ("OtherRoot/bar.md", 1),
    ]
    ok, viol = run_step1_gates(ranked, corpus_policy=policy, step1_gold=g1)
    assert not ok
    assert any("G1.3" in v for v in viol)


def test_g1_1_fails_when_required_missing_from_top_k(tmp_path: Path) -> None:
    policy = load_corpus_policy()
    g1 = dict(load_step1_gold())
    g1["top_k"] = 1
    g1["required_paths_retrieved"] = [
        "Longmont Campaign/Campaign 2/NPC Dossier/lieutenant_lysandra_ironveil_character_dossier.md",
        "Longmont Campaign/Campaign 2/Campaign 2 Notes.md",
    ]
    ranked = [
        ("Longmont Campaign/Campaign 2/NPC Dossier/lieutenant_lysandra_ironveil_character_dossier.md", 100),
        ("Longmont Campaign/Campaign 2/Campaign 2 Notes.md", 50),
    ]
    ok, viol = run_step1_gates(ranked, corpus_policy=policy, step1_gold=g1)
    assert not ok
    assert any("G1.1" in v for v in viol)


def test_step1_real_corpus_keyword_scan_passes_gates() -> None:
    """Uses repo corpus (``corpus/eldyrwild-markdown``); skips if absent."""
    from evals.lysandra_vertical_slice.step0_corpus_environment import resolve_corpus_dir

    if not resolve_corpus_dir().is_dir():
        pytest.skip("corpus/eldyrwild-markdown not present")
    ranked, ok, viol = run_step1_keyword_scan_and_gates()
    assert len(ranked) >= 10
    assert ok, viol
    top_paths = [p for p, _ in ranked[:10]]
    assert any("lieutenant_lysandra" in p for p in top_paths)
