"""Step 2 — canonical statblock + intent classification (Lysandra vertical slice)."""

from __future__ import annotations

import pytest

from evals.lysandra_vertical_slice.step0_corpus_environment import resolve_corpus_dir
from evals.lysandra_vertical_slice.step1_planner_trace import load_planner_step1_scenario
from evals.lysandra_vertical_slice.step1_retrieval import load_corpus_policy
from evals.lysandra_vertical_slice.step2_canonical_intent import (
    build_step2_intent_fixture_sequence_client,
    classify_intent,
    intent_client_for_gold_expect,
    load_step2_gold,
    parse_challenge_rating_from_statblock,
    run_step2_all,
    run_step2_canonical_gates,
    run_step2_intent_fixture_gates,
    evaluate_step2_post_planner_benchmark,
    statblock_trace_reads_matching_policy,
)


def test_step2_gold_parse() -> None:
    g = load_step2_gold()
    assert g.get("required_statblock_markers")
    assert g.get("fixtures")


def test_parse_challenge_rating() -> None:
    text = "Challenge Rating : 4 (1100)\n"
    assert parse_challenge_rating_from_statblock(text) == 4


def test_upgrade_prose_voice_fixture_has_no_benchmark_intent_assertions() -> None:
    """``upgrade_prose`` is a natural-language scenario; Step 2 benchmark must not assert intent."""
    g2 = load_step2_gold()
    keys = (g2.get("planner_bridge") or {}).get("intent_expectations_by_planner_scenario_key") or {}
    assert "upgrade_prose" not in keys


def test_classify_explicit_cr_upgrade() -> None:
    got = classify_intent(
        "Bump Lysandra to CR 5 for the boss fight.",
        client=intent_client_for_gold_expect(
            {
                "intent_mode": "upgrade_request",
                "power_axis": "challenge_rating",
                "clarifier_required": False,
            }
        ),
    )
    assert got.intent_mode == "upgrade_request"
    assert got.power_axis == "challenge_rating"
    assert not got.clarifier_required


def test_classify_ambiguous_upgrade_requires_clarifier() -> None:
    got = classify_intent(
        "I want to level her up before next session.",
        client=intent_client_for_gold_expect(
            {
                "intent_mode": "upgrade_request",
                "power_axis": "unknown",
                "clarifier_required": True,
            }
        ),
    )
    assert got.intent_mode == "upgrade_request"
    assert got.power_axis == "unknown"
    assert got.clarifier_required
    assert got.clarifier_question


def test_step2_intent_fixtures_pass() -> None:
    g2 = load_step2_gold()
    ok, viol = run_step2_intent_fixture_gates(
        step2_gold=g2,
        client=build_step2_intent_fixture_sequence_client(g2),
    )
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
    g2 = load_step2_gold()
    _, ok, viol = run_step2_all(
        resolve_corpus_dir(),
        step2_gold=g2,
        intent_client=build_step2_intent_fixture_sequence_client(g2),
    )
    assert ok, viol


def test_classify_factual_ac_on_statblock() -> None:
    got = classify_intent(
        "What is Captain Lysandra's Armor Class on her current Mirathorn statblock?",
        client=intent_client_for_gold_expect(
            {
                "intent_mode": "factual_lookup",
                "power_axis": "challenge_rating",
                "clarifier_required": False,
            }
        ),
    )
    assert got.intent_mode == "factual_lookup"
    assert got.power_axis == "challenge_rating"
    assert not got.clarifier_required


def test_classify_increase_challenge_rating_is_upgrade_not_lookup() -> None:
    got = classify_intent(
        "Pull up the context on Lysandra and her latest statblock and timeline, "
        "then increase her challenge rating.",
        client=intent_client_for_gold_expect(
            {
                "intent_mode": "upgrade_request",
                "power_axis": "challenge_rating",
                "clarifier_required": False,
            }
        ),
    )
    assert got.intent_mode == "upgrade_request"
    assert got.power_axis == "challenge_rating"
    assert not got.clarifier_required


def test_classify_regenerate_from_dossier_only() -> None:
    got = classify_intent(
        "Regenerate Lysandra's creature sheet using only the character dossier as input; "
        "do not copy numbers from the old mechanical markdown.",
        client=intent_client_for_gold_expect(
            {
                "intent_mode": "upgrade_request",
                "power_axis": "unknown",
                "clarifier_required": True,
            }
        ),
    )
    assert got.intent_mode == "upgrade_request"
    assert got.power_axis == "unknown"
    assert got.clarifier_required
    assert got.clarifier_question


def test_evaluate_step2_post_planner_benchmark_accepts_canonical_statblock_read() -> None:
    g2 = load_step2_gold()
    bridge = (g2.get("planner_bridge") or {}).get("intent_expectations_by_planner_scenario_key") or {}
    expect = bridge.get("stat_check") or {}
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
    detail, ok, viol = evaluate_step2_post_planner_benchmark(
        user_message=ul,
        tool_trace=trace,
        planner_scenario_key="stat_check",
        intent_client=intent_client_for_gold_expect(expect),
    )
    assert ok, viol
    assert detail.get("intent_from_planner_user_message", {}).get("intent_mode") == "factual_lookup"
    assert detail.get("mechanical_statblock_reads_in_trace")


def test_evaluate_step2_post_planner_benchmark_rejects_non_canonical_statblock_read() -> None:
    g2 = load_step2_gold()
    bridge = (g2.get("planner_bridge") or {}).get("intent_expectations_by_planner_scenario_key") or {}
    expect = bridge.get("stat_check") or {}
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
    _detail, ok, viol = evaluate_step2_post_planner_benchmark(
        user_message=ul,
        tool_trace=trace,
        planner_scenario_key="stat_check",
        intent_client=intent_client_for_gold_expect(expect),
    )
    assert not ok
    assert any("was never opened" in v for v in viol)


def test_evaluate_step2_post_planner_benchmark_allows_archive_statblock_if_canonical_also_read() -> None:
    g2 = load_step2_gold()
    bridge = (g2.get("planner_bridge") or {}).get("intent_expectations_by_planner_scenario_key") or {}
    expect = bridge.get("autonomous") or {}
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
    _detail, ok, viol = evaluate_step2_post_planner_benchmark(
        user_message=ul,
        tool_trace=trace,
        planner_scenario_key="autonomous",
        intent_client=intent_client_for_gold_expect(expect),
    )
    assert ok, viol


def test_evaluate_step2_post_planner_benchmark_no_statblock_read_still_ok() -> None:
    g2 = load_step2_gold()
    bridge = (g2.get("planner_bridge") or {}).get("intent_expectations_by_planner_scenario_key") or {}
    expect = bridge.get("autonomous") or {}
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
    detail, ok, viol = evaluate_step2_post_planner_benchmark(
        user_message=ul,
        tool_trace=trace,
        planner_scenario_key="autonomous",
        intent_client=intent_client_for_gold_expect(expect),
    )
    assert ok, viol
    assert detail.get("mechanical_statblock_reads_in_trace") == []


def test_statblock_trace_reads_matching_policy_configurable() -> None:
    """Bridge statblock trace matching is driven by corpus_policy, not a hardcoded NPC slug."""
    policy = {
        **load_corpus_policy(),
        "mechanical_statblock_trace_path_filters": {
            "all_substrings_ignore_case": ["torbin jove/", "torbin jove.md"],
            "path_suffix_ignore_case": ".md",
        },
    }
    paths = [
        "Longmont Campaign/NPCs/Torbin Jove/Torbin Jove.md",
        "Longmont Campaign/Campaign 2/Session Recaps/Session 3 - Recap.md",
    ]
    matched = statblock_trace_reads_matching_policy(paths, policy)
    assert matched == ["Longmont Campaign/NPCs/Torbin Jove/Torbin Jove.md"]
