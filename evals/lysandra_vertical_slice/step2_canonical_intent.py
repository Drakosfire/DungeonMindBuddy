"""Step 2 — Lysandra vertical slice **benchmark harness** for canonical statblock + intent.

Loads committed gold under ``gold/`` and default ``corpus_policy.json``; delegates all logic to
``src.npc_statblock_pipeline`` (policy + gold in, gates out — no hardcoded NPC paths).

See ``gold/step2_canonical_and_intent.json`` and ``Docs/Plans/DESIGN-lysandra-statblock-vertical-slice-benchmark.md`` §6.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

_SLICE_DIR = Path(__file__).resolve().parent
_REPO_ROOT = str(_SLICE_DIR.parents[1])
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from evals.lysandra_vertical_slice.step0_corpus_environment import load_step0_gold, resolve_corpus_dir  # noqa: E402
from evals.lysandra_vertical_slice.step1_retrieval import load_corpus_policy  # noqa: E402
from src.npc_statblock_pipeline.canonical_intent import (  # noqa: E402
    IntentClassification,
    IntentMode,
    PowerAxis,
    build_extracted_section_span,
    build_selection_reason,
    classify_intent,
    detail_for_cli_stdout,
    parse_challenge_rating_from_statblock,
    run_step2_all as _run_step2_all_pipeline,
    run_step2_canonical_gates as _run_step2_canonical_gates_pipeline,
    run_step2_intent_fixture_gates as _run_step2_intent_fixture_gates_pipeline,
    run_step2_planner_bridge as _run_step2_planner_bridge_pipeline,
    select_canonical_statblock_relpath,
    statblock_trace_reads_matching_policy,
)

__all__ = [
    "IntentClassification",
    "IntentMode",
    "PowerAxis",
    "build_extracted_section_span",
    "build_selection_reason",
    "classify_intent",
    "detail_for_cli_stdout",
    "load_step2_gold",
    "parse_challenge_rating_from_statblock",
    "run_step2_all",
    "run_step2_canonical_gates",
    "run_step2_intent_fixture_gates",
    "run_step2_planner_bridge",
    "select_canonical_statblock_relpath",
    "statblock_trace_reads_matching_policy",
    "step2_gold_path",
]


def step2_gold_path() -> Path:
    return _SLICE_DIR / "gold" / "step2_canonical_and_intent.json"


def load_step2_gold() -> dict[str, Any]:
    return json.loads(step2_gold_path().read_text(encoding="utf-8"))


def run_step2_canonical_gates(
    corpus_dir: Path,
    *,
    corpus_policy: dict[str, Any] | None = None,
    step2_gold: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], bool, list[str]]:
    policy = corpus_policy if corpus_policy is not None else load_corpus_policy()
    g2 = step2_gold if step2_gold is not None else load_step2_gold()
    return _run_step2_canonical_gates_pipeline(corpus_dir, corpus_policy=policy, step2_gold=g2)


def run_step2_intent_fixture_gates(
    *,
    step2_gold: dict[str, Any] | None = None,
) -> tuple[bool, list[str]]:
    g2 = step2_gold if step2_gold is not None else load_step2_gold()
    return _run_step2_intent_fixture_gates_pipeline(step2_gold=g2)


def run_step2_all(
    corpus_dir: Path | None = None,
    *,
    corpus_policy: dict[str, Any] | None = None,
    step2_gold: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], bool, list[str]]:
    root = corpus_dir or resolve_corpus_dir(load_step0_gold())
    policy = corpus_policy if corpus_policy is not None else load_corpus_policy()
    g2 = step2_gold if step2_gold is not None else load_step2_gold()
    return _run_step2_all_pipeline(root, corpus_policy=policy, step2_gold=g2)


def run_step2_planner_bridge(
    *,
    user_message: str,
    tool_trace: list[dict[str, Any]],
    planner_scenario_key: str,
    corpus_policy: dict[str, Any] | None = None,
    step2_gold: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], bool, list[str]]:
    policy = corpus_policy if corpus_policy is not None else load_corpus_policy()
    g2 = step2_gold if step2_gold is not None else load_step2_gold()
    return _run_step2_planner_bridge_pipeline(
        user_message=user_message,
        tool_trace=tool_trace,
        planner_scenario_key=planner_scenario_key,
        corpus_policy=policy,
        step2_gold=g2,
    )


def main() -> None:
    root = resolve_corpus_dir(load_step0_gold())
    out, ok, viol = run_step2_all(root)
    cd = out.get("canonical_detail")
    if isinstance(cd, dict):
        out = {**out, "canonical_detail": detail_for_cli_stdout(cd)}
    print(json.dumps({"corpus_dir": str(root), "ok": ok, "detail": out}, indent=2, ensure_ascii=False))
    if viol:
        print("--- violations ---", file=sys.stderr)
        for line in viol:
            print(line, file=sys.stderr)
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
