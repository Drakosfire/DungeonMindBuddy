"""Step 1 Lane A — planner tool_trace gates (Lysandra vertical slice)."""

from __future__ import annotations

import os

import pytest

from evals.lysandra_vertical_slice.step1_planner_trace import (
    load_planner_step1_scenario,
    run_planner_step1_turn,
)
from evals.planner_slice.live_eval import collect_scenario_violations
from src.agent.planner import PlanningModelStepRecord, PlanningTurnDetail


@pytest.mark.parametrize("scenario_key", ("directed", "autonomous", "stat_check", "upgrade_prose"))
def test_planner_step1_fixture_shape(scenario_key: str) -> None:
    sc = load_planner_step1_scenario(scenario_key)
    assert sc.get("version") >= 1
    assert sc.get("id")
    assert sc.get("fixture_role") == scenario_key
    inp = sc["input"]
    assert str(inp.get("user_message", "")).strip()
    req = (sc.get("final") or {}).get("require") or {}
    assert req.get("tool_trace_must_include_tool") == "read_corpus_file"
    subs = req.get("read_corpus_paths_must_include") or []
    assert len(subs) >= 1


def test_planner_step1_gates_pass_synthetic_trace_directed() -> None:
    sc = load_planner_step1_scenario("directed")
    detail = PlanningTurnDetail(
        final_text="## Summary\n" + ("x" * 200),
        last_response_id="r1",
        tool_trace=[
            {
                "tool": "read_corpus_file",
                "arguments": {
                    "path": "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/captain_lysandra_ironveil_character_dossier.md"
                },
                "output_chars": 100,
            },
            {
                "tool": "read_corpus_file",
                "arguments": {
                    "path": "Longmont Campaign/Campaign 2/Session Recaps/Session 18 - Recap.md"
                },
                "output_chars": 50,
            },
        ],
        steps=[
            PlanningModelStepRecord(
                step_index=0,
                response_id="r0",
                function_calls=[],
                assistant_text="",
            )
        ],
        hit_tool_round_limit=False,
    )
    viol = collect_scenario_violations(sc, detail)
    assert viol == {}


def test_planner_step1_gates_pass_synthetic_trace_autonomous() -> None:
    sc = load_planner_step1_scenario("autonomous")
    detail = PlanningTurnDetail(
        final_text="## Summary\n" + ("x" * 200),
        last_response_id="r1",
        tool_trace=[
            {
                "tool": "read_corpus_file",
                "arguments": {
                    "path": "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/README.md"
                },
                "output_chars": 200,
            },
            {
                "tool": "read_corpus_file",
                "arguments": {
                    "path": "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/captain_lysandra_ironveil_character_dossier.md"
                },
                "output_chars": 100,
            },
        ],
        steps=[],
        hit_tool_round_limit=False,
    )
    viol = collect_scenario_violations(sc, detail)
    assert viol == {}


def test_planner_step1_gates_fail_missing_session_read_directed() -> None:
    sc = load_planner_step1_scenario("directed")
    detail = PlanningTurnDetail(
        final_text="y" * 200,
        last_response_id="r1",
        tool_trace=[
            {
                "tool": "read_corpus_file",
                "arguments": {
                    "path": "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/captain_lysandra_ironveil_character_dossier.md"
                },
                "output_chars": 10,
            },
        ],
        steps=[],
        hit_tool_round_limit=False,
    )
    viol = collect_scenario_violations(sc, detail)
    assert viol.get("final")


def test_planner_step1_gates_fail_no_lysandra_path_autonomous() -> None:
    sc = load_planner_step1_scenario("autonomous")
    detail = PlanningTurnDetail(
        final_text="z" * 200,
        last_response_id="r1",
        tool_trace=[
            {
                "tool": "read_corpus_file",
                "arguments": {
                    "path": "Longmont Campaign/Campaign 2/Session Recaps/Session 18 - Recap.md"
                },
                "output_chars": 10,
            },
        ],
        steps=[],
        hit_tool_round_limit=False,
    )
    viol = collect_scenario_violations(sc, detail)
    assert viol.get("final")


def test_planner_step1_gates_pass_synthetic_trace_stat_check() -> None:
    sc = load_planner_step1_scenario("stat_check")
    detail = PlanningTurnDetail(
        final_text="AC 16, HP 52, STR save +6, WIS save +5\n" + ("x" * 100),
        last_response_id="r1",
        tool_trace=[
            {
                "tool": "read_corpus_file",
                "arguments": {
                    "path": "Elderwyld/Cities and Towns/Mirathorn/NPCs/captain_lysandra_ironveil/captain_lysandra_ironveil_statblock_cr4.md"
                },
                "output_chars": 2000,
            },
        ],
        steps=[],
        hit_tool_round_limit=False,
    )
    viol = collect_scenario_violations(sc, detail)
    assert viol == {}


def test_planner_step1_gates_pass_synthetic_trace_upgrade_prose() -> None:
    sc = load_planner_step1_scenario("upgrade_prose")
    body = (
        "Captain Lysandra Ironveil at CR 5 should feel sharper on the table: the same "
        "iron discipline the party knows, but the Mirathorn posting has left her unit stretched "
        "thin—she barks orders a beat faster, trusts flanks less, and rides the edge of "
        "Challenge Rating 5 presence without turning cartoonish. "
        "No file paths or citations belong in this packaged prose."
    )
    detail = PlanningTurnDetail(
        final_text=body,
        last_response_id="r1",
        tool_trace=[
            {
                "tool": "read_corpus_file",
                "arguments": {
                    "path": "Elderwyld/Cities and Towns/Mirathorn/NPCs/captain_lysandra_ironveil/captain_lysandra_ironveil_statblock_cr4.md"
                },
                "output_chars": 200,
            },
        ],
        steps=[],
        hit_tool_round_limit=False,
    )
    viol = collect_scenario_violations(sc, detail)
    assert viol == {}


def test_planner_step1_upgrade_prose_fails_when_final_lists_citations() -> None:
    sc = load_planner_step1_scenario("upgrade_prose")
    bad_body = (
        "Grounded in `Elderwyld/foo.md`: at CR 5, Lysandra should feel sharper. "
        + "x" * 300
    )
    detail = PlanningTurnDetail(
        final_text=bad_body,
        last_response_id="r1",
        tool_trace=[
            {
                "tool": "read_corpus_file",
                "arguments": {
                    "path": "Elderwyld/Cities and Towns/Mirathorn/NPCs/captain_lysandra_ironveil/captain_lysandra_ironveil_statblock_cr4.md"
                },
                "output_chars": 200,
            },
        ],
        steps=[],
        hit_tool_round_limit=False,
    )
    viol = collect_scenario_violations(sc, detail)
    assert viol.get("final")


def test_planner_step1_gates_fail_no_statblock_read_stat_check() -> None:
    sc = load_planner_step1_scenario("stat_check")
    detail = PlanningTurnDetail(
        final_text="AC 16, HP 52\n" + ("x" * 100),
        last_response_id="r1",
        tool_trace=[
            {
                "tool": "read_corpus_file",
                "arguments": {
                    "path": "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/README.md"
                },
                "output_chars": 200,
            },
        ],
        steps=[],
        hit_tool_round_limit=False,
    )
    viol = collect_scenario_violations(sc, detail)
    assert viol.get("final")


@pytest.mark.integration
def test_planner_step1_live_passes_with_model() -> None:
    """
    Real OpenAI + corpus. Opt-in: LYSANDRA_PLANNER_STEP1_LIVE=1 and OPENAI_API_KEY.

    Scenario: ``LYSANDRA_PLANNER_STEP1_SCENARIO`` (default **autonomous** — human-style ask).
    """
    if os.environ.get("LYSANDRA_PLANNER_STEP1_LIVE", "").strip().lower() not in ("1", "true", "yes"):
        pytest.skip("set LYSANDRA_PLANNER_STEP1_LIVE=1 to run planner Step 1 live")
    if not os.environ.get("OPENAI_API_KEY", "").strip():
        pytest.skip("OPENAI_API_KEY required")

    from openai import OpenAI

    from evals.lysandra_vertical_slice.step0_corpus_environment import resolve_corpus_dir
    from src.agent.planner import _resolve_planner_model

    root = resolve_corpus_dir()
    if not root.is_dir():
        pytest.skip("corpus missing")

    client = OpenAI()
    model_id = _resolve_planner_model(None)
    run = run_planner_step1_turn(corpus_dir=root, client=client, model_id=model_id)
    assert run.result.passed, run.result.violations
    assert len(run.detail.usage_rounds) >= 1
