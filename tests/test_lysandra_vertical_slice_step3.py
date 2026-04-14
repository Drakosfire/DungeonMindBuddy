"""Step 3 — power baseline + evidence spans (Lysandra vertical slice)."""

from __future__ import annotations

from pathlib import Path

import pytest

from evals.lysandra_vertical_slice.step0_corpus_environment import resolve_corpus_dir
from evals.lysandra_vertical_slice.step3_power_baseline import (
    extract_evidence_spans_for_fields,
    load_step3_gold,
    run_step2_and_step3,
    run_step3_power_baseline_gates,
)


def test_step3_gold_parse() -> None:
    g = load_step3_gold()
    assert g.get("expected_power_baseline")
    assert g.get("evidence_span_fields")


def test_extract_evidence_spans_sample_body() -> None:
    body = "Intro\nArmor Class : 16\nHit Points: 52 x\nChallenge Rating : 4 (1100)\n"
    spans, viol = extract_evidence_spans_for_fields(body, "Elderwyld/x.md", ["armor_class", "hit_points", "challenge_rating"])
    assert not viol
    by = {s["field"]: s for s in spans}
    assert by["armor_class"]["verbatim"] == "Armor Class : 16"
    assert by["hit_points"]["verbatim"] == "Hit Points: 52 x"
    assert "4" in by["challenge_rating"]["verbatim"]
    assert body[by["armor_class"]["start_char"] : by["armor_class"]["end_char"]] == by["armor_class"]["verbatim"]


def test_step3_on_real_corpus() -> None:
    if not resolve_corpus_dir().is_dir():
        pytest.skip("corpus/eldyrwild-markdown not present")
    root = resolve_corpus_dir()
    detail, ok, viol = run_step3_power_baseline_gates(root)
    assert ok, viol
    pb = detail.get("power_baseline") or {}
    assert pb.get("challenge_rating_current") == 4
    assert pb.get("class_level_current") is None
    spans = detail.get("evidence_spans") or []
    assert len(spans) == 3
    canon = detail["canonical_path"]
    raw = (root / canon).read_text(encoding="utf-8")
    for sp in spans:
        s, e = sp["start_char"], sp["end_char"]
        assert raw[s:e] == sp["verbatim"]


def test_step2_and_step3_aggregate() -> None:
    if not resolve_corpus_dir().is_dir():
        pytest.skip("corpus/eldyrwild-markdown not present")
    out, ok, viol = run_step2_and_step3(resolve_corpus_dir())
    assert ok, viol
    assert out.get("intent_fixtures_ok")
    assert out.get("power_baseline_detail", {}).get("power_baseline", {}).get("challenge_rating_current") == 4


def test_step3_g3_4_fallback_when_cr_missing(tmp_path: Path) -> None:
    """No CR line → gold fallback; no span extraction for mechanical lines."""
    g3 = load_step3_gold()
    step2_like = {
        "canonical_path": "Synthetic/no_cr.md",
        "selection_reason": {"outcome": "selected"},
        "extracted_markdown": "Armor Class : 10\nHit Points: 1\n",
    }
    corpus = tmp_path / "corpus"
    (corpus / "Synthetic").mkdir(parents=True)
    (corpus / "Synthetic" / "no_cr.md").write_text(step2_like["extracted_markdown"], encoding="utf-8")
    detail, ok, viol = run_step3_power_baseline_gates(
        corpus, step2_canonical_detail=step2_like, step3_gold=g3
    )
    assert ok, viol
    fb = g3.get("fallback_when_cr_absent") or {}
    exp_pb = fb.get("power_baseline") or {}
    assert detail.get("power_baseline", {}).get("challenge_rating_current") == exp_pb.get(
        "challenge_rating_current"
    )
    assert detail.get("evidence_spans") == []
