"""Step 4 — level-up context bundle (Lysandra vertical slice)."""

from __future__ import annotations

import copy

import pytest

from evals.lysandra_vertical_slice.step0_corpus_environment import resolve_corpus_dir
from evals.lysandra_vertical_slice.step4_levelup_context import (
    assemble_model_context_plaintext,
    build_levelup_context_bundle,
    load_step4_gold,
    run_step2_through_step4,
    run_step4_levelup_context_gates,
)


def test_step4_gold_parse() -> None:
    g = load_step4_gold()
    assert int(g["target_challenge_rating"]) >= 2
    assert g.get("recap_scan_relative_dirs")


def test_step4_on_real_corpus() -> None:
    if not resolve_corpus_dir().is_dir():
        pytest.skip("corpus/eldyrwild-markdown not present")
    root = resolve_corpus_dir()
    detail, ok, viol = run_step4_levelup_context_gates(root)
    assert ok, viol
    bundle = detail["levelup_context_bundle"]
    assert bundle["power_target"]["target_challenge_rating"] == 5
    assert bundle["power_baseline"]["challenge_rating_current"] == 4
    snips = bundle["session_recap_snippets"]
    assert len(snips) >= 1
    union = "\n".join(s["verbatim"] for s in snips)
    assert "Lysandra" in union
    assert "uneasy" in union or "difficult to navigate" in union
    # Anchored windows must slice from the same file text
    for s in snips:
        raw = (root / s["corpus_relative_path"]).read_text(encoding="utf-8")
        lo, hi = int(s["start_char"]), int(s["end_char"])
        assert raw[lo:hi] == s["verbatim"]
    pt = assemble_model_context_plaintext(bundle)
    assert "Target challenge rating: 5" in pt
    assert "Session recap snippets" in pt


def test_step2_through_step4_aggregate() -> None:
    if not resolve_corpus_dir().is_dir():
        pytest.skip("corpus/eldyrwild-markdown not present")
    out, ok, viol = run_step2_through_step4(resolve_corpus_dir())
    assert ok, viol
    assert out.get("intent_fixtures_ok")
    b = out["levelup_context_detail"]["levelup_context_bundle"]
    assert b["power_target"]["target_challenge_rating"] == 5


def test_g4_1_monotonicity_violation() -> None:
    """Target must exceed baseline CR (gold override)."""
    if not resolve_corpus_dir().is_dir():
        pytest.skip("corpus/eldyrwild-markdown not present")
    root = resolve_corpus_dir()
    from evals.lysandra_vertical_slice.step3_power_baseline import run_step3_power_baseline_gates

    d3, ok3, _ = run_step3_power_baseline_gates(root)
    assert ok3
    g4 = copy.deepcopy(load_step4_gold())
    g4["target_challenge_rating"] = 3
    _, ok, viol = run_step4_levelup_context_gates(root, step3_detail=d3, step4_gold=g4)
    assert not ok
    assert any("G4.1 FAIL" in v for v in viol)


def test_build_bundle_preserves_step3_spans() -> None:
    if not resolve_corpus_dir().is_dir():
        pytest.skip("corpus/eldyrwild-markdown not present")
    from evals.lysandra_vertical_slice.step3_power_baseline import run_step3_power_baseline_gates

    root = resolve_corpus_dir()
    d3, ok3, _ = run_step3_power_baseline_gates(root)
    assert ok3
    b = build_levelup_context_bundle(root, step3_detail=d3)
    assert len(b.get("evidence_spans_from_step3") or []) == len(d3.get("evidence_spans") or [])
