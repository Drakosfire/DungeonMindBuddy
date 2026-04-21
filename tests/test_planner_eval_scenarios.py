"""End-to-end planner evals: scripted Responses API + corpus dispatch (fail loud)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from evals.planner_slice.scripted_client import ScriptedOpenAI
from src.agent.planner import (
    PlanningTurnResult,
    STATBLOCK_TOOL_DESCRIPTION,
    _build_system_prompt,
    _planner_tools_responses,
    build_corpus_manifest,
    make_tool_dispatcher,
    run_planning_turn,
)

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "evals" / "planner_slice" / "fixtures"
CORPUS = Path(__file__).resolve().parents[1] / "corpus" / "eldyrwild-markdown"


def _fail(scenario_id: str, message: str) -> None:
    raise AssertionError(f"[planner_eval:{scenario_id}] {message}")


def _validate_expectations(
    scenario_id: str,
    data: dict[str, Any],
    turn: PlanningTurnResult,
    client: ScriptedOpenAI,
) -> None:
    ex = data.get("expect") or {}
    if ex.get("all_scripted_responses_consumed"):
        n = client.remaining_script_steps()
        if n != 0:
            _fail(scenario_id, f"expected all scripted responses consumed, {n} step(s) left unused")

    names = [t["tool"] for t in turn.tool_trace]
    want_names = ex.get("tool_names_in_order")
    if want_names is not None and names != want_names:
        _fail(scenario_id, f"tool order want={want_names!r} got={names!r}")

    subs = ex.get("read_paths_must_include_substrings")
    if subs:
        read_paths = [
            str(t["arguments"].get("path", ""))
            for t in turn.tool_trace
            if t.get("tool") == "read_corpus_file"
        ]
        for needle in subs:
            if not any(needle in p for p in read_paths):
                _fail(
                    scenario_id,
                    f"read_corpus_file path missing substring {needle!r}; paths={read_paths!r}",
                )

    sb = ex.get("statblock_args")
    if sb:
        gen = [t for t in turn.tool_trace if t.get("tool") == "generate_statblock"]
        if not gen:
            _fail(scenario_id, "expected generate_statblock in tool_trace")
        args = gen[-1]["arguments"]
        cn = str(args.get("creature_name", "")).lower()
        need = str(sb.get("creature_name_contains", "")).lower()
        if need and need not in cn:
            _fail(scenario_id, f"creature_name {cn!r} missing {need!r}")
        desc = str(args.get("description", "")).lower()
        anys = [str(x).lower() for x in (sb.get("description_contains_any") or [])]
        if anys and not any(x in desc for x in anys):
            _fail(scenario_id, f"description missing any of {anys!r}: {desc!r}")

    for needle in ex.get("final_text_must_include") or []:
        if needle not in turn.final_text:
            _fail(scenario_id, f"final_text missing {needle!r}: {turn.final_text[:500]!r}")

    outs = ex.get("tool_outputs_must_include_substrings") or []
    for rule in outs:
        idx = int(rule["tool_index"])
        sub = str(rule["substring"])
        excerpt = str(turn.tool_trace[idx].get("output_excerpt", ""))
        if sub not in excerpt:
            _fail(scenario_id, f"tool_trace[{idx}] output excerpt missing {sub!r}: {excerpt[:200]!r}")

    if ex.get("previous_response_id_chained_after_first_call"):
        for i, call in enumerate(client.calls):
            prev = call.get("previous_response_id")
            if i == 0:
                if prev not in (None, "", False):
                    _fail(scenario_id, f"first responses.create should omit previous_response_id, got {prev!r}")
            else:
                if not prev:
                    _fail(scenario_id, f"call {i} expected previous_response_id, got {prev!r}")

    if turn.hit_tool_round_limit:
        _fail(scenario_id, "hit_tool_round_limit unexpectedly")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    "fixture_name",
    [
        "scenario_branchbound_mount.json",
        "scenario_bad_corpus_path.json",
    ],
)
def test_planner_eval_scripted_scenario(fixture_name: str) -> None:
    if not CORPUS.is_dir():
        pytest.skip("Corpus not present")
    path = FIXTURES_DIR / fixture_name
    if not path.exists():
        pytest.skip(f"missing fixture {path}")
    data = _load_json(path)
    sid = str(data["id"])

    required = ("user_message", "mock_responses", "expect")
    for k in required:
        if k not in data:
            _fail(sid, f"fixture missing required key {k!r}")

    manifest = build_corpus_manifest(CORPUS)
    instructions = _build_system_prompt(manifest)
    tools = _planner_tools_responses()
    stub = data.get("statblock_stub")
    client = ScriptedOpenAI(list(data["mock_responses"]))
    dispatch = make_tool_dispatcher(CORPUS, client, "gpt-mock-eval", statblock_stub=stub)

    turn = run_planning_turn(
        client=client,
        model_id="gpt-mock-eval",
        instructions=instructions,
        tools=tools,
        corpus_path=CORPUS,
        user_line=str(data["user_message"]),
        previous_response_id=None,
        dispatch_tool=dispatch,
    )

    _validate_expectations(sid, data, turn, client)


def test_statblock_tool_uses_exported_description() -> None:
    gen = next(t for t in _planner_tools_responses() if t["name"] == "generate_statblock")
    assert gen["description"] == STATBLOCK_TOOL_DESCRIPTION


def test_planner_tools_corpus_and_statblock_only() -> None:
    names = {t["name"] for t in _planner_tools_responses()}
    assert "propose_clarification" not in names
    assert names >= {
        "read_corpus_file",
        "load_context_markdown",
        "generate_statblock",
        "list_npc_hubs",
        "list_pc_hubs",
    }
