"""Step 2 — canonical statblock + intent classification (Lysandra vertical slice)."""

from __future__ import annotations

import pytest

from evals.lysandra_vertical_slice.step0_corpus_environment import resolve_corpus_dir
from evals.lysandra_vertical_slice.step2_canonical_intent import (
    classify_intent,
    load_step2_gold,
    parse_challenge_rating_from_statblock,
    run_step2_all,
    run_step2_canonical_gates,
    run_step2_intent_fixture_gates,
)


def test_step2_gold_parse() -> None:
    g = load_step2_gold()
    assert g.get("required_statblock_markers")
    assert g.get("fixtures")


def test_parse_challenge_rating() -> None:
    text = "Challenge Rating : 4 (1100)\n"
    assert parse_challenge_rating_from_statblock(text) == 4


def test_classify_explicit_cr_upgrade() -> None:
    got = classify_intent("Bump Lysandra to CR 5 for the boss fight.")
    assert got.intent_mode == "upgrade_request"
    assert got.power_axis == "challenge_rating"
    assert not got.clarifier_required


def test_classify_ambiguous_upgrade_requires_clarifier() -> None:
    got = classify_intent("I want to level her up before next session.")
    assert got.intent_mode == "upgrade_request"
    assert got.power_axis == "unknown"
    assert got.clarifier_required
    assert got.clarifier_question


def test_step2_intent_fixtures_pass() -> None:
    ok, viol = run_step2_intent_fixture_gates()
    assert ok, viol


def test_step2_canonical_gates_on_real_corpus() -> None:
    if not resolve_corpus_dir().is_dir():
        pytest.skip("corpus/eldyrwild-markdown not present")
    detail, ok, viol = run_step2_canonical_gates(resolve_corpus_dir())
    assert detail.get("canonical_path")
    assert detail.get("parsed_challenge_rating") == 4
    assert ok, viol


def test_step2_full_on_real_corpus() -> None:
    if not resolve_corpus_dir().is_dir():
        pytest.skip("corpus/eldyrwild-markdown not present")
    _, ok, viol = run_step2_all(resolve_corpus_dir())
    assert ok, viol
