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


def test_planner_step1_fixture_shape() -> None:
    sc = load_planner_step1_scenario()
    assert sc.get("version") == 1
    assert sc.get("id")
    inp = sc["input"]
    assert str(inp.get("user_message", "")).strip()
    req = (sc.get("final") or {}).get("require") or {}
    assert req.get("tool_trace_must_include_tool") == "read_corpus_file"
    subs = req.get("read_corpus_paths_must_include") or []
    assert len(subs) >= 2


def test_planner_step1_gates_pass_synthetic_trace() -> None:
    sc = load_planner_step1_scenario()
    detail = PlanningTurnDetail(
        final_text="## Summary\n" + ("x" * 200),
        last_response_id="r1",
        tool_trace=[
            {
                "tool": "read_corpus_file",
                "arguments": {
                    "path": "Longmont Campaign/Campaign 2/NPC Dossier/lieutenant_lysandra_ironveil_character_dossier.md"
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


def test_planner_step1_gates_fail_missing_session_read() -> None:
    sc = load_planner_step1_scenario()
    detail = PlanningTurnDetail(
        final_text="y" * 200,
        last_response_id="r1",
        tool_trace=[
            {
                "tool": "read_corpus_file",
                "arguments": {
                    "path": "Longmont Campaign/Campaign 2/NPC Dossier/lieutenant_lysandra_ironveil_character_dossier.md"
                },
                "output_chars": 10,
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
