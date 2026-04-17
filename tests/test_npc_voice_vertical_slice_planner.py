"""NPC voice planner slice — manifest + gold validation; opt-in live API suite."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

_SLICE = Path(__file__).resolve().parents[1] / "evals" / "npc_voice_vertical_slice"
_MANIFEST = _SLICE / "manifest.json"
_CORPUS = Path(__file__).resolve().parents[1] / "corpus" / "eldyrwild-markdown"


def _all_corpus_rel_paths(root: Path) -> set[str]:
    out: set[str] = set()
    for p in root.rglob("*.md"):
        try:
            rel = p.resolve().relative_to(root.resolve())
        except ValueError:
            continue
        out.add(str(rel).replace("\\", "/").lower())
    return out


def test_npc_voice_manifest_scenarios_exist_and_gold_shape() -> None:
    from evals.npc_voice_vertical_slice.npc_voice_planner_trace import gold_path_for_scenario_id, load_manifest

    m = load_manifest()
    ids_seen: set[str] = set()
    corpus_paths = _all_corpus_rel_paths(_CORPUS) if _CORPUS.is_dir() else set()
    for row in m["scenarios"]:
        sid = str(row["id"])
        assert sid not in ids_seen, f"duplicate scenario id: {sid}"
        ids_seen.add(sid)
        p = gold_path_for_scenario_id(sid)
        assert p.is_file(), f"missing gold for {sid}: {p}"
        data = json.loads(p.read_text(encoding="utf-8"))
        assert data.get("id"), sid
        assert "input" in data and str((data["input"] or {}).get("user_message", "")).strip(), sid
        assert "final" in data and (data["final"] or {}).get("require"), sid
        req = (data["final"] or {}).get("require") or {}
        for sub in req.get("read_corpus_paths_must_include") or []:
            s = str(sub).lower()
            if corpus_paths:
                assert any(s in rel for rel in corpus_paths), (
                    f"{sid}: read_corpus_paths_must_include substring {sub!r} not found in corpus .md paths"
                )


def test_npc_voice_suite_report_writes_md_and_json(tmp_path: Path) -> None:
    from evals.npc_voice_vertical_slice.npc_voice_planner_trace import write_npc_voice_suite_report

    rows = [
        {
            "suite_run_index": 1,
            "scenario_id": "zebra_first",
            "passed": True,
            "violations": {},
            "scenario_estimated_cost_usd": 0.01,
            "artifact_primary": str(tmp_path / "a.md"),
        },
        {
            "suite_run_index": 2,
            "scenario_id": "zebra_first",
            "passed": False,
            "violations": {"final": ["boom"]},
            "scenario_estimated_cost_usd": 0.02,
            "artifact_primary": str(tmp_path / "b.md"),
        },
    ]
    md = tmp_path / "suite.md"
    write_npc_voice_suite_report(
        rows=rows,
        out_md=md,
        model_id="gpt-test",
        corpus_fingerprint="abc",
        corpus_dir=tmp_path,
        runs_n=2,
        mode="scenario",
        scenario_filter="zebra_first",
    )
    assert md.is_file()
    js = md.with_suffix(".json")
    assert js.is_file()
    data = json.loads(js.read_text(encoding="utf-8"))
    assert data["schema"] == "npc_voice_suite_report_v1"
    assert data["summary"]["failed_cells"] == 1
    text = md.read_text(encoding="utf-8")
    assert "zebra_first" in text
    assert "boom" in text


def test_step2_noop_disables_planner_bridge() -> None:
    noop = json.loads((_SLICE / "gold" / "step2_noop.json").read_text(encoding="utf-8"))
    bridge = noop.get("planner_bridge")
    assert isinstance(bridge, dict) and len(bridge) == 0


@pytest.mark.integration
def test_npc_voice_planner_live_single_scenario() -> None:
    if os.environ.get("NPC_VOICE_PLANNER_LIVE", "").strip().lower() not in ("1", "true", "yes"):
        pytest.skip("set NPC_VOICE_PLANNER_LIVE=1 to run NPC voice planner live benchmark")
    if not os.environ.get("OPENAI_API_KEY", "").strip():
        pytest.skip("OPENAI_API_KEY required")

    from openai import OpenAI

    from evals.lysandra_vertical_slice.step0_corpus_environment import resolve_corpus_dir
    from evals.npc_voice_vertical_slice.npc_voice_planner_trace import (
        default_scenario_id,
        run_npc_voice_planner_turn,
    )
    from src.agent.planner import _resolve_planner_model

    root = resolve_corpus_dir()
    if not root.is_dir():
        pytest.skip("corpus missing")

    sid = os.environ.get("NPC_VOICE_PLANNER_SCENARIO", "").strip() or default_scenario_id()
    client = OpenAI()
    model_id = _resolve_planner_model(None)
    run = run_npc_voice_planner_turn(corpus_dir=root, client=client, model_id=model_id, scenario_id=sid)
    assert run.result.passed, (sid, run.result.violations)
    assert len(run.detail.usage_rounds) >= 1


@pytest.mark.integration
def test_npc_voice_planner_live_all_manifest() -> None:
    if os.environ.get("NPC_VOICE_PLANNER_LIVE_ALL", "").strip().lower() not in ("1", "true", "yes"):
        pytest.skip("set NPC_VOICE_PLANNER_LIVE_ALL=1 to run full NPC voice manifest (costly)")
    if not os.environ.get("OPENAI_API_KEY", "").strip():
        pytest.skip("OPENAI_API_KEY required")

    from openai import OpenAI

    from evals.lysandra_vertical_slice.step0_corpus_environment import resolve_corpus_dir
    from evals.npc_voice_vertical_slice.npc_voice_planner_trace import (
        list_scenario_ids,
        run_npc_voice_planner_turn,
    )
    from src.agent.planner import _resolve_planner_model

    root = resolve_corpus_dir()
    if not root.is_dir():
        pytest.skip("corpus missing")

    client = OpenAI()
    model_id = _resolve_planner_model(None)
    failed: list[tuple[str, dict]] = []
    for sid in list_scenario_ids():
        run = run_npc_voice_planner_turn(corpus_dir=root, client=client, model_id=model_id, scenario_id=sid)
        if not run.result.passed:
            failed.append((sid, run.result.violations))
    assert not failed, failed
