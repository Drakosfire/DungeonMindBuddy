"""Live planner evals (real OpenAI); schema + matcher unit tests (no API)."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from src.agent.planner import PlanningModelStepRecord, PlanningTurnDetail

from evals.planner_slice.live_eval import (
    cite_matches_any_read,
    collect_scenario_violations,
    dedupe_read_paths_preserve_order,
    discover_live_fixtures,
    extract_cited_markdown_paths_from_final,
    load_live_fixture,
    match_calls_satisfy,
    min_pass_rate_from_env,
    read_paths_from_tool_trace,
    resolve_planner_user_message,
    run_live_suite,
)
from evals.planner_slice.live_report import render_planner_live_report_markdown

LIVE_FIXTURES_DIR = Path(__file__).resolve().parents[1] / "evals" / "planner_slice" / "live_fixtures"
CORPUS = Path(__file__).resolve().parents[1] / "corpus" / "eldyrwild-markdown"


def test_resolve_planner_model_uses_model_policy_when_present() -> None:
    from src.agent.planner import _model_policy_paths, _resolve_planner_model

    if not any(p.is_file() for p in _model_policy_paths()):
        pytest.skip("MODEL_POLICY.json not found next to repo")
    assert _resolve_planner_model(None) == "gpt-5.4-mini"
    assert _resolve_planner_model("  custom-model  ") == "custom-model"


def test_live_fixtures_parse_and_have_required_keys() -> None:
    paths = discover_live_fixtures(LIVE_FIXTURES_DIR)
    assert paths, "expected at least one live fixture"
    for p in paths:
        data = load_live_fixture(p)
        assert data.get("version") == 1
        assert "id" in data
        assert "input" in data
        inp = data["input"]
        um = str(inp.get("user_message", "")).strip()
        pa = str(inp.get("planning_ask", "")).strip()
        pg = str(inp.get("planning_goal", "")).strip()
        assert um or pa or pg, "fixture needs input.user_message, input.planning_ask, or input.planning_goal"
        assert "steps" in data
        assert "final" in data


def test_resolve_planner_user_message_planning_ask_wins_over_goal(tmp_path: Path) -> None:
    corp = tmp_path / "corpus"
    corp.mkdir()
    sc = {
        "id": "g2",
        "input": {"planning_ask": "ASK ONLY", "planning_goal": "goal ignored"},
    }
    text, viol = resolve_planner_user_message(sc, corp)
    assert not viol
    assert "ASK ONLY" in text
    assert "goal ignored" not in text


def test_resolve_planner_user_message_planning_goal_autonomous_suffix(tmp_path: Path) -> None:
    corp = tmp_path / "corpus"
    corp.mkdir()
    sc = {
        "id": "g1",
        "input": {"planning_goal": "Prep the festival beat."},
    }
    text, viol = resolve_planner_user_message(sc, corp)
    assert not viol
    assert "--- Planning goal ---" in text
    assert "Prep the festival beat." in text
    assert "## How to respond (autonomous plan)" in text
    assert "read_corpus_file" in text


def test_resolve_planner_user_message_prior_plus_ask(tmp_path: Path) -> None:
    corp = tmp_path / "corpus"
    sess = corp / "sessions" / "s1.md"
    sess.parent.mkdir(parents=True)
    sess.write_text("# Recap\nhello", encoding="utf-8")
    sc = {
        "id": "t1",
        "input": {"planning_ask": "Plan next.", "prior_session_path": "sessions/s1.md"},
    }
    text, viol = resolve_planner_user_message(sc, corp)
    assert not viol
    assert "--- Prior session (`sessions/s1.md`) ---" in text
    assert "hello" in text
    assert "--- Planning ask ---" in text
    assert "Plan next." in text


def test_resolve_planner_user_message_rejects_path_escape(tmp_path: Path) -> None:
    corp = tmp_path / "corpus"
    corp.mkdir()
    outside = tmp_path / "secret.md"
    outside.write_text("x", encoding="utf-8")
    sc = {
        "id": "t2",
        "input": {"planning_ask": "x", "prior_session_path": "../secret.md"},
    }
    _, viol = resolve_planner_user_message(sc, corp)
    assert viol and ".." in viol[0].lower()


def test_resolve_planner_user_message_direct_user_message_wins() -> None:
    sc = {"id": "t3", "input": {"user_message": "  full only  ", "planning_ask": "ignored"}}
    text, viol = resolve_planner_user_message(sc, Path("/tmp"))
    assert text == "full only"
    assert not viol


def test_extract_cited_markdown_paths_from_final() -> None:
    text = "I read Elderwyld/Migrating Forest/foo.md and also `Elderwyld/Other/bar.md`."
    got = extract_cited_markdown_paths_from_final(text)
    assert "Elderwyld/Migrating Forest/foo.md" in got
    assert "Elderwyld/Other/bar.md" in got


def test_cite_matches_any_read_suffix_and_basename() -> None:
    reads = ["Elderwyld/Migrating Forest/the_migrating_forest_executive_dm_summary.md"]
    assert cite_matches_any_read("Elderwyld/Migrating Forest/the_migrating_forest_executive_dm_summary.md", reads)
    assert cite_matches_any_read("the_migrating_forest_executive_dm_summary.md", reads)


def test_cited_paths_must_match_reads_violation() -> None:
    detail = PlanningTurnDetail(
        final_text="I used Elderwyld/Made/up.md for everything.",
        last_response_id="x",
        tool_trace=[{"tool": "read_corpus_file", "arguments": {"path": "Elderwyld/real/file.md"}}],
        steps=[],
        hit_tool_round_limit=False,
    )
    scenario = {"id": "g2", "steps": [], "final": {"require": {"cited_paths_must_match_reads": True}}}
    v = collect_scenario_violations(scenario, detail)
    assert v.get("final")


def test_cited_paths_and_reads_mention_pass() -> None:
    detail = PlanningTurnDetail(
        final_text=(
            "Paths Elderwyld/Migrating Forest/the_migrating_forest_executive_dm_summary.md "
            "and Elderwyld/Migrating Forest/Branchbound/branchbound_culture_pack.md were read."
        ),
        last_response_id="x",
        tool_trace=[
            {"tool": "read_corpus_file", "arguments": {"path": "Elderwyld/Migrating Forest/the_migrating_forest_executive_dm_summary.md"}},
            {"tool": "read_corpus_file", "arguments": {"path": "Elderwyld/Migrating Forest/Branchbound/branchbound_culture_pack.md"}},
        ],
        steps=[],
        hit_tool_round_limit=False,
    )
    scenario = {
        "id": "g2b",
        "steps": [],
        "final": {
            "require": {
                "cited_paths_must_match_reads": True,
                "read_paths_must_appear_in_final": True,
            }
        },
    }
    assert not collect_scenario_violations(scenario, detail).get("final")


def test_read_corpus_paths_must_include_pass_and_fail() -> None:
    detail_ok = PlanningTurnDetail(
        final_text="x" * 700,
        last_response_id="x",
        tool_trace=[
            {"tool": "read_corpus_file", "arguments": {"path": "Elderwyld/Cities and Towns/Mirathorn/The City of Mirathorn.md"}},
        ],
        steps=[],
        hit_tool_round_limit=False,
    )
    scenario_ok = {
        "id": "rcpi",
        "steps": [],
        "final": {"require": {"read_corpus_paths_must_include": ["the city of mirathorn"]}},
    }
    assert not collect_scenario_violations(scenario_ok, detail_ok).get("final")

    detail_bad = PlanningTurnDetail(
        final_text="x" * 700,
        last_response_id="x",
        tool_trace=[
            {"tool": "read_corpus_file", "arguments": {"path": "Elderwyld/Migrating Forest/foo.md"}},
        ],
        steps=[],
        hit_tool_round_limit=False,
    )
    v = collect_scenario_violations(scenario_ok, detail_bad).get("final")
    assert v and any("read_corpus_paths_must_include" in msg for msg in v)


def test_render_planner_live_report_markdown_covers_steps_and_final() -> None:
    detail = PlanningTurnDetail(
        final_text="## Gate\nThe main gates are **grand**.",
        last_response_id="resp_final",
        tool_trace=[
            {
                "tool": "read_corpus_file",
                "arguments": {"path": "Elderwyld/foo.md"},
                "output_chars": 100,
                "output_excerpt": "excerpt body",
            },
        ],
        steps=[
            PlanningModelStepRecord(
                step_index=0,
                response_id="resp_0",
                function_calls=[{"name": "read_corpus_file", "arguments": {"path": "Elderwyld/foo.md"}}],
                assistant_text="",
            ),
            PlanningModelStepRecord(
                step_index=1,
                response_id="resp_1",
                function_calls=[],
                assistant_text="## Gate\nThe main gates are **grand**.",
            ),
        ],
        hit_tool_round_limit=False,
        telemetry_cost={
            "planner_usage_totals": {
                "input_tokens": 10,
                "output_tokens": 20,
                "cached_tokens": 5,
            }
        },
    )
    md = render_planner_live_report_markdown(
        scenario_id="unit_scenario",
        model_id="gpt-test",
        corpus_fingerprint="abc123",
        corpus_dir="/tmp/corpus",
        fixture_filename="unit.json",
        passed=True,
        violations={},
        estimated_cost_usd=0.01,
        user_message="Do the thing.",
        detail=detail,
    )
    assert "## Final output (assistant reply)" in md
    assert "## Corpus files retrieved (`read_corpus_file`)" in md
    assert "`Elderwyld/foo.md`" in md
    assert "The main gates are **grand**." in md
    assert "### Round 0 — model response" in md
    assert "### Round 1 — model response" in md
    assert "read_corpus_file" in md
    assert "SUITE_INDEX" not in md


def test_render_planner_live_report_markdown_includes_benchmark_section() -> None:
    detail = PlanningTurnDetail(
        final_text="## A\nAspitome and Stories in Shadow.",
        last_response_id="r",
        tool_trace=[],
        steps=[
            PlanningModelStepRecord(
                step_index=0,
                response_id="r0",
                function_calls=[],
                assistant_text="## A\nAspitome.",
            )
        ],
        hit_tool_round_limit=False,
    )
    bench = {
        "scenario_id": "live_x",
        "exemplar_relpath": "exemplars/foo.md",
        "exemplar_chars": 1000,
        "candidate_chars": 50,
        "declared_min_keyword_fraction": 0.4,
        "declared_min_weighted_concept_score": 0.55,
        "declared_saturation_cosine": 0.92,
        "declared_saturation_keyword_fraction": 0.85,
        "citation_grounding": {
            "read_count": 1,
            "citation_count": 1,
            "reads": ["Elderwyld/a.md"],
            "citations_in_final": ["Elderwyld/a.md"],
            "citations_not_grounded": [],
            "reads_not_mentioned_in_final": [],
        },
        "concept_coverage": {
            "weighted_score": 0.72,
            "phrase_count": 2,
            "total_weight": 2.0,
            "per_phrase": [
                {
                    "phrase": "p1",
                    "score": 0.5,
                    "bag_fraction": 0.5,
                    "proximity_match": False,
                    "exact_substring": False,
                    "weight": 1.0,
                },
            ],
        },
        "keyword_coverage": {
            "fraction": 0.5,
            "present": ["Aspitome"],
            "missing": ["Tindlewix", "expansion ritual"],
        },
        "embedding": {"skipped": True, "reason": "off"},
        "quality_summary": {
            "purpose": "test",
            "citation_alignment": {"telemetry_available": True, "aligned": True, "read_count": 1},
            "exemplar_concepts": {"weighted_score": 0.72, "mean_phrase_score": 0.7, "phrases_scored_below_0_5": 1, "phrase_count": 3},
            "legacy_substring_keywords": {"fraction": 0.5, "hit_count": 1, "miss_count": 1},
            "embedding_diagnostic": {"skipped": True, "reason": "off"},
            "notes": ["Synthetic rollup for render test."],
        },
    }
    md = render_planner_live_report_markdown(
        scenario_id="unit_scenario",
        model_id="gpt-test",
        corpus_fingerprint="abc",
        corpus_dir="/tmp/corpus",
        fixture_filename=None,
        passed=True,
        violations={},
        estimated_cost_usd=None,
        user_message="x",
        detail=detail,
        benchmark=bench,
    )
    assert "## Benchmark instrumentation (citations + concepts)" in md
    assert "### Quality summary (dimensions, not suite pass/fail)" in md
    assert "### Citation grounding" in md
    assert "### Concept coverage" in md
    assert "`Aspitome`" in md
    assert "`Tindlewix`" in md
    assert "### Embedding (optional diagnostic)" in md


def test_min_h2_headings_final_require() -> None:
    detail_ok = PlanningTurnDetail(
        final_text="## A\n## B\n## C\nbody",
        last_response_id="x",
        tool_trace=[],
        steps=[],
        hit_tool_round_limit=False,
    )
    scenario_ok = {"id": "h2", "steps": [], "final": {"require": {"min_h2_headings": 3}}}
    assert not collect_scenario_violations(scenario_ok, detail_ok).get("final")

    detail_bad = PlanningTurnDetail(
        final_text="## Only\nbody",
        last_response_id="x",
        tool_trace=[],
        steps=[],
        hit_tool_round_limit=False,
    )
    v = collect_scenario_violations(scenario_ok, detail_bad).get("final")
    assert v and any("min_h2_headings" in msg for msg in v)


def test_read_paths_from_tool_trace_order() -> None:
    tt = [
        {"tool": "read_corpus_file", "arguments": {"path": "a/b.md"}},
        {"tool": "generate_statblock", "arguments": {}},
        {"tool": "read_corpus_file", "arguments": {"path": "c/d.md"}},
    ]
    assert read_paths_from_tool_trace(tt) == ["a/b.md", "c/d.md"]


def test_dedupe_read_paths_preserve_order() -> None:
    r = ["Elderwyld/Foo/Same.md", "Elderwyld/Foo/Same.md", "Elderwyld/Other/x.md"]
    assert dedupe_read_paths_preserve_order(r) == ["Elderwyld/Foo/Same.md", "Elderwyld/Other/x.md"]


def test_read_paths_must_appear_in_final_tolerates_duplicate_reads() -> None:
    """Same file opened twice should not require two prose mentions."""
    detail = PlanningTurnDetail(
        final_text="Plan from `Elderwyld/Foo/Same.md` only.",
        last_response_id="r",
        tool_trace=[
            {"tool": "read_corpus_file", "arguments": {"path": "Elderwyld/Foo/Same.md"}},
            {"tool": "read_corpus_file", "arguments": {"path": "Elderwyld/Foo/Same.md"}},
        ],
        steps=[],
        hit_tool_round_limit=False,
    )
    scenario = {
        "id": "dup",
        "steps": [],
        "final": {"require": {"read_paths_must_appear_in_final": True}},
    }
    assert not collect_scenario_violations(scenario, detail).get("final")


def test_resolve_live_fixture_with_session_prior() -> None:
    paths = discover_live_fixtures(LIVE_FIXTURES_DIR)
    assert paths
    mig = next(p for p in paths if p.name == "live_migrating_forest_branchbound_plan.json")
    data = load_live_fixture(mig)
    text, viol = resolve_planner_user_message(data, CORPUS)
    assert not viol
    assert "Session 17" in text or "Thrin" in text
    assert "--- Planning ask ---" in text


def test_match_calls_satisfy_distinct_calls() -> None:
    calls = [
        {"name": "read_corpus_file", "arguments": {"path": "Elderwyld/Migrating Forest/a.md"}},
        {"name": "read_corpus_file", "arguments": {"path": "Elderwyld/Migrating Forest/Branchbound/b.md"}},
    ]
    specs = [
        {"tool": "read_corpus_file", "path_contains": "migrating forest"},
        {"tool": "read_corpus_file", "path_contains": "branchbound"},
    ]
    v = match_calls_satisfy("unit", "step0", calls, specs)
    assert v == []

    v2 = match_calls_satisfy(
        "unit",
        "step0",
        [{"name": "read_corpus_file", "arguments": {"path": "Elderwyld/wrong.md"}}],
        specs,
    )
    assert len(v2) == 2


def test_match_calls_satisfy_generate_statblock_description_min() -> None:
    calls = [
        {
            "name": "generate_statblock",
            "arguments": {"creature_name": "X", "description": "y" * 50},
        }
    ]
    specs = [{"tool": "generate_statblock", "description_min_chars": 40}]
    assert match_calls_satisfy("unit", "s", calls, specs) == []


def test_min_pass_rate_from_env_defaults() -> None:
    old = os.environ.pop("PLANNER_EVAL_MIN_PASS_RATE", None)
    try:
        assert min_pass_rate_from_env() == 1.0
    finally:
        if old is not None:
            os.environ["PLANNER_EVAL_MIN_PASS_RATE"] = old


@pytest.mark.integration
def test_planner_live_suite_meets_gate() -> None:
    """Real model + fixtures; opt-in via PLANNER_LIVE_EVAL=1 and OPENAI_API_KEY."""
    if os.environ.get("PLANNER_LIVE_EVAL", "").strip().lower() not in ("1", "true", "yes"):
        pytest.skip("set PLANNER_LIVE_EVAL=1 to run live planner evals")
    if not os.environ.get("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY required for live planner evals")
    if not CORPUS.is_dir():
        pytest.skip("corpus missing")

    from openai import OpenAI

    from src.agent.planner import _resolve_planner_model

    client = OpenAI()
    model_id = _resolve_planner_model(None)
    results, rate = run_live_suite(corpus_dir=CORPUS, client=client, model_id=model_id)
    assert results, "no live fixtures ran"
    min_rate = min_pass_rate_from_env()
    failures = [r for r in results if not r.passed]
    if rate < min_rate:
        detail = json.dumps(
            {r.scenario_id: r.violations for r in failures},
            indent=2,
            ensure_ascii=False,
        )
        pytest.fail(
            f"live planner suite pass rate {rate:.2f} < gate {min_rate:.2f}. Failures:\n{detail}"
        )
