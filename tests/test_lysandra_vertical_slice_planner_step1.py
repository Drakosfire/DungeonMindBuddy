"""Step 1 — agent benchmark: planner tool_trace gates (Lysandra vertical slice)."""

from __future__ import annotations

import os

import pytest

from evals.lysandra_vertical_slice.step1_planner_trace import (
    format_clarification_evidence_lines,
    format_context_wiring_lines,
    load_planner_step1_scenario,
    run_planner_step1_turn,
)
from evals.planner_slice.live_eval import collect_scenario_violations
from src.agent.planner import (
    PlanningModelStepRecord,
    PlanningTurnDetail,
    merge_planning_turn_details,
)


def test_format_context_wiring_lines_load_context_marker_and_generate_statblock() -> None:
    trace = [
        {
            "tool": "load_context_markdown",
            "arguments": {"path": "Elderwyld/x/captain_statblock_cr4.md"},
            "output_chars": 1200,
            "output_excerpt": (
                "[context attached: Elderwyld/x/captain_statblock_cr4.md]\n\n"
                "# CAPTAIN LYSANDRA IRONVEIL\n> Medium humanoid"
            ),
        },
        {
            "tool": "generate_statblock",
            "arguments": {
                "creature_name": "Lysandra",
                "description": "CR 6 siege",
                "source_statblock_corpus_path": "Elderwyld/x/captain_statblock_cr4.md",
            },
            "output_chars": 5000,
            "output_excerpt": (
                "[Attached corpus statblock baseline: Elderwyld/x/captain_statblock_cr4.md "
                "(2757 chars), wire_format=markdown]\n\n## Lysandra CR 6"
            ),
        },
    ]
    text = "\n".join(format_context_wiring_lines(trace))
    assert "load_context_markdown: 1 call" in text
    assert "context_attached_prefix_present=True" in text
    assert "first_nonblank_line_preview='# CAPTAIN LYSANDRA IRONVEIL'" in text
    assert "generate_statblock: 1 call" in text
    assert "source_statblock_corpus_path='Elderwyld/x/captain_statblock_cr4.md'" in text
    assert "output_has_attached_baseline_prefix=True" in text


def test_format_context_wiring_lines_no_load_context_warns() -> None:
    trace = [
        {
            "tool": "read_corpus_file",
            "arguments": {"path": "Elderwyld/hub/README.md"},
            "output_chars": 100,
            "output_excerpt": "# README",
        }
    ]
    text = "\n".join(format_context_wiring_lines(trace))
    assert "load_context_markdown: 0 calls" in text


def test_format_clarification_evidence_lines_tool_and_turn0() -> None:
    trace = [
        {
            "tool": "propose_clarification",
            "arguments": {"question": "What CR for the siege?", "missing_slots": ["target_cr"]},
            "output_chars": 12,
        }
    ]
    text = "\n".join(
        format_clarification_evidence_lines(
            trace,
            followup_user_line="CR 6 please",
            first_turn_final_text="What target CR should she be?",
        )
    )
    assert "propose_clarification tool: 1 call" in text
    assert "What CR for the siege?" in text
    assert "What target CR should she be?" in text
    assert "heuristic_turn0_asks_target_cr_in_prose" in text


def test_format_clarification_evidence_lines_prose_only_heuristic() -> None:
    trace: list = []
    text = "\n".join(
        format_clarification_evidence_lines(
            trace,
            followup_user_line="follow",
            first_turn_final_text="Which CR do you want for Lysandra?",
        )
    )
    assert "propose_clarification tool: 0 calls" in text
    assert "heuristic_turn0_asks_target_cr_in_prose" in text
    assert "True" in text


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
    # ``upgrade_prose``: no required path substrings (model chooses reads); two-turn; no clarifier tool gate.
    if scenario_key != "upgrade_prose":
        assert len(subs) >= 1
    else:
        follow = sc.get("followup_turn") or {}
        assert str(follow.get("user_message", "")).strip()
        assert not (req.get("tool_trace_must_include_tools") or [])


def test_planner_step1_upgrade_prose_synthetic_two_turn_merged_passes_gates() -> None:
    sc = load_planner_step1_scenario("upgrade_prose")
    detail1 = PlanningTurnDetail(
        final_text="What target CR do you want for Lysandra?",
        last_response_id="r1",
        tool_trace=[
            {
                "tool": "read_corpus_file",
                "arguments": {
                    "path": "Elderwyld/Cities and Towns/Mirathorn/NPCs/captain_lysandra_ironveil/README.md"
                },
                "output_chars": 100,
            },
        ],
        steps=[],
    )
    detail2 = PlanningTurnDetail(
        final_text="## Siege pitch\nLysandra at **CR 6** — " + ("x" * 130),
        last_response_id="r2",
        tool_trace=[],
        steps=[],
    )
    merged = merge_planning_turn_details(detail1, detail2)
    viol = collect_scenario_violations(sc, merged)
    assert not viol.get("final"), viol


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
        "Captain Lysandra Ironveil at **CR 6** for the siege: the same "
        "iron discipline the party knows, but the Mirathorn posting has left her unit stretched "
        "thin—she barks orders a beat faster, trusts flanks less, and rides the edge of "
        "Challenge Rating 6 presence without turning cartoonish. "
        "No file paths or citations belong in this packaged prose."
    )
    detail1 = PlanningTurnDetail(
        final_text="What target CR do you want?",
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
                "tool": "load_context_markdown",
                "arguments": {
                    "path": "Elderwyld/Cities and Towns/Mirathorn/NPCs/captain_lysandra_ironveil/captain_lysandra_ironveil_statblock_cr4.md"
                },
                "output_chars": 200,
            },
        ],
        steps=[],
        hit_tool_round_limit=False,
    )
    detail2 = PlanningTurnDetail(
        final_text=body,
        last_response_id="r2",
        tool_trace=[],
        steps=[],
        hit_tool_round_limit=False,
    )
    merged = merge_planning_turn_details(detail1, detail2)
    viol = collect_scenario_violations(sc, merged)
    assert viol == {}


def test_planner_step1_upgrade_prose_passes_with_read_corpus_file_only() -> None:
    """Merged two-turn trace: read on turn 1; CR 6 pitch on turn 2 final (no clarify tool required)."""
    sc = load_planner_step1_scenario("upgrade_prose")
    body = "Lysandra at **CR 6** for the siege — sharper on the table. " + "x" * 200
    detail1 = PlanningTurnDetail(
        final_text="One quick question about target CR?",
        last_response_id="r1",
        tool_trace=[
            {
                "tool": "read_corpus_file",
                "arguments": {"path": "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/README.md"},
                "output_chars": 50,
            },
        ],
        steps=[],
        hit_tool_round_limit=False,
    )
    detail2 = PlanningTurnDetail(
        final_text=body,
        last_response_id="r2",
        tool_trace=[],
        steps=[],
        hit_tool_round_limit=False,
    )
    merged = merge_planning_turn_details(detail1, detail2)
    viol = collect_scenario_violations(sc, merged)
    assert not viol.get("final")


def test_planner_step1_upgrade_prose_fails_when_final_lists_citations() -> None:
    sc = load_planner_step1_scenario("upgrade_prose")
    bad_body = (
        "Grounded in `Elderwyld/foo.md`: at CR 6, Lysandra should feel sharper. "
        + "x" * 300
    )
    detail1 = PlanningTurnDetail(
        final_text="?",
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
    detail2 = PlanningTurnDetail(
        final_text=bad_body,
        last_response_id="r2",
        tool_trace=[],
        steps=[],
        hit_tool_round_limit=False,
    )
    merged = merge_planning_turn_details(detail1, detail2)
    viol = collect_scenario_violations(sc, merged)
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

    Scenario: ``LYSANDRA_PLANNER_STEP1_SCENARIO`` (CLI default **upgrade_prose** when unset — power-rise benchmark).
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
