"""Unified deterministic runner (Steps 0 → 1 → 2–4)."""

from __future__ import annotations

import pytest

from evals.lysandra_vertical_slice.run_deterministic_slice import run_vertical_slice_deterministic
from evals.lysandra_vertical_slice.step0_corpus_environment import resolve_corpus_dir
from evals.lysandra_vertical_slice.step1_retrieval import load_corpus_policy
from evals.lysandra_vertical_slice.step4_levelup_context import (
    load_step4_gold,
    run_step2_through_step4,
    step4_all_gate_violations,
)


def test_run_vertical_slice_deterministic_wires_step234_like_direct_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    if not resolve_corpus_dir().is_dir():
        pytest.skip("corpus/eldyrwild-markdown not present")
    monkeypatch.setenv("LYSANDRA_SLICE_SKIP_STATBLOCK_URL_GATE", "1")
    root = resolve_corpus_dir()
    report, ok, viol = run_vertical_slice_deterministic(root)
    assert report["step0"]["ok"] is True
    assert report["step1"]["ok"] is True
    assert ok is True
    assert viol == []

    out, ok_direct, viol_direct = run_step2_through_step4(root)
    assert ok_direct and viol_direct == []

    s24 = report["step2_through_4"]
    assert s24["ok"] is True
    assert s24["canonical_path"] == (out.get("canonical_detail") or {}).get("canonical_path")
    assert s24["intent_fixtures_ok"] == out.get("intent_fixtures_ok")

    ld = out["levelup_context_detail"]
    bundle = ld["levelup_context_bundle"]
    assert step4_all_gate_violations(
        step3_detail=ld["step3_detail"],
        levelup_context_bundle=bundle,
        corpus_policy=load_corpus_policy(),
        step4_gold=load_step4_gold(),
    ) == []


def test_run_vertical_slice_violations_concat_step_outputs(monkeypatch: pytest.MonkeyPatch) -> None:
    """Returned ``violations`` equals step0 + step1 + (step2–4 if reached), in order."""
    if not resolve_corpus_dir().is_dir():
        pytest.skip("corpus/eldyrwild-markdown not present")
    monkeypatch.setenv("LYSANDRA_SLICE_SKIP_STATBLOCK_URL_GATE", "1")
    root = resolve_corpus_dir()
    report, _ok, viol = run_vertical_slice_deterministic(root)
    expected: list[str] = []
    expected.extend(report["step0"]["violations"])
    expected.extend(report["step1"]["violations"])
    if "step2_through_4" in report:
        expected.extend(report["step2_through_4"]["violations"])
    assert viol == expected
