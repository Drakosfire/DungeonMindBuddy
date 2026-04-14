"""Step 4 — level-up context bundle (Lysandra vertical slice)."""

from __future__ import annotations

import copy

import pytest

from evals.lysandra_vertical_slice.step0_corpus_environment import resolve_corpus_dir
from evals.lysandra_vertical_slice.step1_retrieval import load_corpus_policy
from evals.lysandra_vertical_slice.step4_levelup_context import (
    build_levelup_context_bundle,
    g4_1_power_target_violations,
    g4_recap_violations,
    g4_timeline_violations,
    load_step4_gold,
    run_step2_through_step4,
    run_step4_levelup_context_gates,
    step4_all_gate_violations,
)


def test_step4_gold_parse() -> None:
    g = load_step4_gold()
    assert int(g["target_challenge_rating"]) >= 2
    assert g.get("recap_scan_relative_dirs")


def test_g4_1_passes_when_target_exceeds_baseline() -> None:
    """G4.1 (first Step 4 gate): synthetic Step 3 detail, no corpus."""
    detail = {"power_baseline": {"challenge_rating_current": 4}}
    assert g4_1_power_target_violations(detail, target_challenge_rating=5) == []


def test_g4_1_fails_when_baseline_cr_null() -> None:
    detail = {"power_baseline": {"challenge_rating_current": None}}
    v = g4_1_power_target_violations(detail, target_challenge_rating=5)
    assert len(v) == 1 and "null" in v[0]


def test_g4_1_fails_when_baseline_cr_non_numeric() -> None:
    detail = {"power_baseline": {"challenge_rating_current": "four"}}
    v = g4_1_power_target_violations(detail, target_challenge_rating=5)
    assert len(v) == 1 and "non-numeric" in v[0]


def test_g4_1_fails_when_target_not_strictly_greater() -> None:
    detail = {"power_baseline": {"challenge_rating_current": 5}}
    v = g4_1_power_target_violations(detail, target_challenge_rating=5)
    assert len(v) == 1 and "must exceed" in v[0]
    v2 = g4_1_power_target_violations(detail, target_challenge_rating=4)
    assert len(v2) == 1


def test_g4_recap_passes_with_synthetic_bundle() -> None:
    bundle = {
        "session_recap_snippets": [
            {"verbatim": "Captain Lysandra felt uneasy about the cliffs."},
        ],
    }
    gold = {
        "min_recap_snippets": 1,
        "assert_snippets_union_contains_substrings": ["Lysandra"],
        "assert_snippets_union_contains_one_of": ["uneasy", "difficult to navigate"],
    }
    assert g4_recap_violations(bundle, step4_gold=gold) == []


def test_g4_recap_fails_too_few_snippets() -> None:
    assert any(
        "expected at least 2" in v
        for v in g4_recap_violations(
            {"session_recap_snippets": [{"verbatim": "x"}]},
            step4_gold={"min_recap_snippets": 2},
        )
    )


def test_g4_recap_fails_missing_substring() -> None:
    v = g4_recap_violations(
        {"session_recap_snippets": [{"verbatim": "no magic word here"}]},
        step4_gold={
            "min_recap_snippets": 0,
            "assert_snippets_union_contains_substrings": ["required_token"],
        },
    )
    assert len(v) == 1 and "required_token" in v[0]


def test_g4_recap_fails_one_of_union() -> None:
    v = g4_recap_violations(
        {"session_recap_snippets": [{"verbatim": "alpha beta"}]},
        step4_gold={
            "min_recap_snippets": 0,
            "assert_snippets_union_contains_one_of": ["gamma", "delta"],
        },
    )
    assert len(v) == 1 and "missing all" in v[0]


def test_g4_timeline_skipped_when_gold_false() -> None:
    assert (
        g4_timeline_violations(
            {"timeline_excerpt": {"text": ""}},
            {"timeline_relpath": ""},
            step4_gold={"require_timeline_excerpt": False},
        )
        == []
    )


def test_g4_timeline_fails_missing_policy_path() -> None:
    v = g4_timeline_violations(
        {"timeline_excerpt": {"text": "some timeline"}},
        {"timeline_relpath": ""},
        step4_gold={"require_timeline_excerpt": True},
    )
    assert len(v) == 1 and "timeline_relpath" in v[0]


def test_g4_timeline_fails_empty_excerpt() -> None:
    v = g4_timeline_violations(
        {"timeline_excerpt": {"text": "   "}},
        {"timeline_relpath": "Longmont Campaign/foo/timeline.md"},
        step4_gold={"require_timeline_excerpt": True},
    )
    assert len(v) == 1 and "empty" in v[0].lower()


def test_g4_timeline_passes_synthetic() -> None:
    assert (
        g4_timeline_violations(
            {"timeline_excerpt": {"text": "Session 1 \u2192 Session 2"}},
            {"timeline_relpath": "Longmont Campaign/foo/timeline.md"},
            step4_gold={"require_timeline_excerpt": True},
        )
        == []
    )


def test_step4_all_gate_violations_order_synthetic() -> None:
    """Aggregator runs G4.1 then G4_RECAP then G4_TIMELINE (two failures in order)."""
    step3 = {"power_baseline": {"challenge_rating_current": 5}}
    bundle = {"session_recap_snippets": [], "timeline_excerpt": {"text": ""}}
    policy = {"timeline_relpath": "hub/timeline.md"}
    gold = {
        "target_challenge_rating": 5,
        "min_recap_snippets": 1,
        "require_timeline_excerpt": True,
    }
    v = step4_all_gate_violations(
        step3_detail=step3,
        levelup_context_bundle=bundle,
        corpus_policy=policy,
        step4_gold=gold,
    )
    assert len(v) == 3
    assert v[0].startswith("G4.1 FAIL")
    assert v[1].startswith("G4_RECAP FAIL")
    assert v[2].startswith("G4_TIMELINE FAIL")


def test_runner_violations_match_step4_all_gate_violations_on_corpus() -> None:
    if not resolve_corpus_dir().is_dir():
        pytest.skip("corpus/eldyrwild-markdown not present")
    root = resolve_corpus_dir()
    detail, ok, viol = run_step4_levelup_context_gates(root)
    assert ok, viol
    merged = step4_all_gate_violations(
        step3_detail=detail["step3_detail"],
        levelup_context_bundle=detail["levelup_context_bundle"],
        corpus_policy=load_corpus_policy(),
        step4_gold=load_step4_gold(),
    )
    assert viol == merged == []


def test_runner_violations_match_aggregator_when_g4_1_fails() -> None:
    if not resolve_corpus_dir().is_dir():
        pytest.skip("corpus/eldyrwild-markdown not present")
    root = resolve_corpus_dir()
    from evals.lysandra_vertical_slice.step3_power_baseline import run_step3_power_baseline_gates

    d3, ok3, _ = run_step3_power_baseline_gates(root)
    assert ok3
    g4 = copy.deepcopy(load_step4_gold())
    g4["target_challenge_rating"] = 3
    detail, ok, viol = run_step4_levelup_context_gates(root, step3_detail=d3, step4_gold=g4)
    assert not ok
    merged = step4_all_gate_violations(
        step3_detail=detail["step3_detail"],
        levelup_context_bundle=detail["levelup_context_bundle"],
        corpus_policy=load_corpus_policy(),
        step4_gold=g4,
    )
    assert viol == merged
    assert len(viol) >= 1 and viol[0].startswith("G4.1 FAIL")


def test_step4_on_real_corpus() -> None:
    if not resolve_corpus_dir().is_dir():
        pytest.skip("corpus/eldyrwild-markdown not present")
    root = resolve_corpus_dir()
    detail, ok, viol = run_step4_levelup_context_gates(root)
    assert ok, viol
    bundle = detail["levelup_context_bundle"]
    policy = load_corpus_policy()
    tl = bundle.get("timeline_excerpt") or {}
    assert tl.get("corpus_relative_path") == policy.get("timeline_relpath")
    assert len(str(tl.get("text") or "").strip()) > 50
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
    assert "statblock_generator_context_plaintext" not in bundle
    assert "model_context_plaintext" not in bundle


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
