"""Stage A harness — deterministic sentence-unit capture + sidecar + capture grader.

Writes ``sentence_routing_stage_a_capture--<scenario>--<PASS|FAIL>--<UTC>.json`` under
``artifacts/runs/<YYYY-MM-DD>/`` and mirrors ``artifacts/last_sentence_routing_stage_a_capture.json``.

Run (repo root)::

    uv run python -m evals.sentence_routing_retrieval_falsification.step1_capture_run

    uv run python -m evals.sentence_routing_retrieval_falsification.step1_capture_run \\
        --scenario-json evals/sentence_routing_retrieval_falsification/gold/scenario_mini.json
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_SLICE = Path(__file__).resolve().parent
_REPO_ROOT = _SLICE.parents[1]
_DEFAULT_SCENARIO = _SLICE / "gold" / "scenario_mini.json"
_ARTIFACTS = _SLICE / "artifacts" / "runs"


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def _date_folder() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Stage A — deterministic sentence-unit capture (sentence routing falsification harness).",
    )
    parser.add_argument(
        "--scenario-json",
        type=Path,
        default=_DEFAULT_SCENARIO,
        help="Path to scenario JSON (default: gold/scenario_mini.json).",
    )
    parser.add_argument(
        "--corpus-root",
        type=Path,
        default=_REPO_ROOT,
        help="Root directory containing recap_relative_path (default: repo root).",
    )
    parser.add_argument(
        "--no-writes",
        action="store_true",
        help="Skip writing run artifacts to disk.",
    )
    args = parser.parse_args()

    scenario_path = args.scenario_json.resolve()
    raw = json.loads(scenario_path.read_text(encoding="utf-8"))
    inp = raw.get("input") or {}
    recap_rel = str(inp.get("recap_relative_path") or "").strip()
    if not recap_rel:
        print("scenario input.recap_relative_path is required", file=sys.stderr)
        return 2

    corpus_root: Path = args.corpus_root.resolve()

    from evals.sentence_routing_retrieval_falsification.capture import (
        capture_sentence_units_from_file,
        units_to_jsonable,
    )
    from evals.sentence_routing_retrieval_falsification.grader import (
        collect_stage_a_violations,
        collect_stub_stage_bcd_telemetry,
    )

    units = capture_sentence_units_from_file(
        corpus_root=corpus_root,
        recap_relative_path=recap_rel,
    )
    grading = {k: raw.get(k) for k in ("gold_capture", "gold_routing", "gold_proposals", "gold_retrieval")}
    gold_capture = dict(raw.get("gold_capture") or {})
    violations, telem_a = collect_stage_a_violations(
        units,
        gold_capture,
        corpus_root=corpus_root,
        recap_relative_path=recap_rel,
    )
    telem_stub = collect_stub_stage_bcd_telemetry(grading)
    passed = not violations
    scenario_id = str(raw.get("scenario_id") or scenario_path.stem)

    sidecar: dict[str, object] = {
        "schema": raw.get("schema"),
        "scenario_id": scenario_id,
        "scenario_path": str(scenario_path),
        "recap_relative_path": recap_rel,
        "corpus_root": str(corpus_root),
        "pass": passed,
        "scenario_estimated_cost_usd": 0.0,
        "violations": {"stage_a": violations},
        "telemetry": {**telem_a, **telem_stub},
        "sentence_units": units_to_jsonable(units),
    }

    if not args.no_writes:
        day = _date_folder()
        out_dir = _ARTIFACTS / day
        out_dir.mkdir(parents=True, exist_ok=True)
        stamp = _utc_stamp()
        tag = "PASS" if passed else "FAIL"
        out_path = out_dir / f"sentence_routing_stage_a_capture--{scenario_id}--{tag}--{stamp}.json"
        out_path.write_text(json.dumps(sidecar, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        last_path = _SLICE / "artifacts" / "last_sentence_routing_stage_a_capture.json"
        last_path.parent.mkdir(parents=True, exist_ok=True)
        last_path.write_text(json.dumps(sidecar, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(str(out_path))

    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
