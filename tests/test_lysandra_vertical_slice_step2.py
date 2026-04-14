"""Step 2 — canonical statblock + intent classification (Lysandra vertical slice)."""

from __future__ import annotations

import pytest

from evals.lysandra_vertical_slice.step0_corpus_environment import resolve_corpus_dir
from evals.lysandra_vertical_slice.step1_planner_trace import load_planner_step1_scenario
from evals.lysandra_vertical_slice.step2_canonical_intent import (
    classify_intent,
    load_step2_gold,
    parse_challenge_rating_from_statblock,
    run_step2_all,
    run_step2_canonical_gates,
    run_step2_intent_fixture_gates,
    run_step2_planner_bridge,
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
    sr = detail.get("selection_reason") or {}
    assert sr.get("outcome") == "selected"
    assert sr.get("rule_id") == "corpus_policy.canonical_statblock_relpath"
    em = detail.get("extracted_markdown") or ""
    assert "Challenge Rating" in em
    span = detail.get("extracted_section_span") or {}
    assert span.get("corpus_relative_path") == detail.get("canonical_path")
    assert span.get("end_char") == len(em)
    assert not detail.get("extracted_markdown_truncated")


def test_step2_extract_respects_detail_max_chars() -> None:
    if not resolve_corpus_dir().is_dir():
        pytest.skip("corpus/eldyrwild-markdown not present")
    gold = {**load_step2_gold(), "detail_max_extracted_markdown_chars": 120}
    detail, ok, viol = run_step2_canonical_gates(resolve_corpus_dir(), step2_gold=gold)
    assert ok, viol
    assert detail.get("extracted_markdown_truncated") is True
    assert len(detail.get("extracted_markdown") or "") <= 120
    span = detail.get("extracted_section_span") or {}
    assert span.get("end_char") == len(detail.get("extracted_markdown") or "")


def test_step2_full_on_real_corpus() -> None:
    if not resolve_corpus_dir().is_dir():
        pytest.skip("corpus/eldyrwild-markdown not present")
    _, ok, viol = run_step2_all(resolve_corpus_dir())
    assert ok, viol


def test_classify_factual_ac_on_statblock() -> None:
    got = classify_intent(
        "What is Captain Lysandra's Armor Class on her current Mirathorn statblock?"
    )
    assert got.intent_mode == "factual_lookup"
    assert got.power_axis == "challenge_rating"
    assert not got.clarifier_required


def test_classify_regenerate_from_dossier_only() -> None:
    got = classify_intent(
        "Regenerate Lysandra's creature sheet using only the character dossier as input; "
        "do not copy numbers from the old mechanical markdown."
    )
    assert got.intent_mode == "upgrade_request"
    assert got.power_axis == "unknown"
    assert got.clarifier_required
    assert got.clarifier_question


def test_run_step2_planner_bridge_accepts_canonical_statblock_read() -> None:
    sc = load_planner_step1_scenario("stat_check")
    ul = str(sc["input"]["user_message"])
    trace = [
        {
            "tool": "read_corpus_file",
            "arguments": {
                "path": "Elderwyld/Cities and Towns/Mirathorn/NPCs/captain_lysandra_ironveil/captain_lysandra_ironveil_statblock_cr4.md",
            },
        }
    ]
    detail, ok, viol = run_step2_planner_bridge(
        user_message=ul,
        tool_trace=trace,
        planner_scenario_key="stat_check",
    )
    assert ok, viol
    assert detail.get("intent_from_planner_user_message", {}).get("intent_mode") == "factual_lookup"
    assert detail.get("lysandra_statblock_reads_in_trace")


def test_run_step2_planner_bridge_rejects_non_canonical_statblock_read() -> None:
    sc = load_planner_step1_scenario("stat_check")
    ul = str(sc["input"]["user_message"])
    trace = [
        {
            "tool": "read_corpus_file",
            "arguments": {
                "path": "Elderwyld/Cities and Towns/Mirathorn/NPCs/captain_lysandra_ironveil/captain_lysandra_ironveil_statblock_cr2.md",
            },
        }
    ]
    _detail, ok, viol = run_step2_planner_bridge(
        user_message=ul,
        tool_trace=trace,
        planner_scenario_key="stat_check",
    )
    assert not ok
    assert any("was never opened" in v for v in viol)


def test_run_step2_planner_bridge_allows_archive_statblock_if_canonical_also_read() -> None:
    sc = load_planner_step1_scenario("autonomous")
    ul = str(sc["input"]["user_message"])
    trace = [
        {
            "tool": "read_corpus_file",
            "arguments": {
                "path": "Elderwyld/Cities and Towns/Mirathorn/NPCs/captain_lysandra_ironveil/captain_lysandra_ironveil_statblock_cr4.md",
            },
        },
        {
            "tool": "read_corpus_file",
            "arguments": {
                "path": "Elderwyld/Cities and Towns/Mirathorn/NPCs/captain_lysandra_ironveil/captain_lysandra_ironveil_statblock_cr2.md",
            },
        },
    ]
    _detail, ok, viol = run_step2_planner_bridge(
        user_message=ul,
        tool_trace=trace,
        planner_scenario_key="autonomous",
    )
    assert ok, viol


def test_run_step2_planner_bridge_no_statblock_read_still_ok() -> None:
    sc = load_planner_step1_scenario("autonomous")
    ul = str(sc["input"]["user_message"])
    trace = [
        {
            "tool": "read_corpus_file",
            "arguments": {
                "path": "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/README.md",
            },
        }
    ]
    detail, ok, viol = run_step2_planner_bridge(
        user_message=ul,
        tool_trace=trace,
        planner_scenario_key="autonomous",
    )
    assert ok, viol
    assert detail.get("lysandra_statblock_reads_in_trace") == []
