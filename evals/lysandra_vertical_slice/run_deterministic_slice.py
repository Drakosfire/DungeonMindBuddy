"""Single entry: deterministic Lysandra vertical slice (Step 0 → Step 1 → Steps 2–4).

No planner LLM. Use ``step1_planner_trace.py`` for the agent benchmark (live model + tools).

Runnable from repo root::

    uv run python evals/lysandra_vertical_slice/run_deterministic_slice.py
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

from evals.lysandra_vertical_slice.step0_corpus_environment import (  # noqa: E402
    load_step0_gold,
    resolve_corpus_dir,
    run_step0_gates,
)
from evals.lysandra_vertical_slice.step1_retrieval import run_step1_keyword_scan_and_gates  # noqa: E402
from evals.lysandra_vertical_slice.step4_levelup_context import (  # noqa: E402
    run_step2_through_step4,
    slim_levelup_context_bundle_for_report,
)


def run_vertical_slice_deterministic(
    corpus_dir: Path | None = None,
    *,
    corpus_policy: dict[str, Any] | None = None,
    step1_gold: dict[str, Any] | None = None,
    step2_gold: dict[str, Any] | None = None,
    step3_gold: dict[str, Any] | None = None,
    step4_gold: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], bool, list[str]]:
    """
    Run Step 0 (corpus env) → Step 1 (keyword retrieval gates) → Steps 2–4 aggregate.

    Returns ``(report, ok, violations)``. ``report`` is JSON-serializable; the level-up bundle
    is slimmed (no full excerpt bodies). ``violations`` concatenates all step violation strings
    in execution order.
    """
    root = (corpus_dir or resolve_corpus_dir(load_step0_gold())).resolve()
    all_v: list[str] = []
    report: dict[str, Any] = {"corpus_dir": str(root)}

    ok0, v0 = run_step0_gates(corpus_dir=root)
    report["step0"] = {"ok": ok0, "violations": v0}
    all_v.extend(v0)
    if not ok0:
        report["ok"] = False
        return report, False, all_v

    _, ok1, v1 = run_step1_keyword_scan_and_gates(
        root, corpus_policy=corpus_policy, step1_gold=step1_gold
    )
    report["step1"] = {"ok": ok1, "violations": v1}
    all_v.extend(v1)
    if not ok1:
        report["ok"] = False
        return report, False, all_v

    out, ok24, v24 = run_step2_through_step4(
        root,
        corpus_policy=corpus_policy,
        step2_gold=step2_gold,
        step3_gold=step3_gold,
        step4_gold=step4_gold,
    )
    all_v.extend(v24)

    ld = out.get("levelup_context_detail") or {}
    bundle = ld.get("levelup_context_bundle")
    report["step2_through_4"] = {
        "ok": ok24,
        "violations": v24,
        "intent_fixtures_ok": out.get("intent_fixtures_ok"),
        "canonical_path": (out.get("canonical_detail") or {}).get("canonical_path"),
        "power_baseline": (ld.get("step3_detail") or {}).get("power_baseline"),
        "levelup_context_bundle": slim_levelup_context_bundle_for_report(bundle),
    }
    report["ok"] = ok24
    return report, ok24, all_v


def main() -> None:
    report, ok, viol = run_vertical_slice_deterministic()
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if viol:
        print("--- violations ---", file=sys.stderr)
        for line in viol:
            print(line, file=sys.stderr)
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
