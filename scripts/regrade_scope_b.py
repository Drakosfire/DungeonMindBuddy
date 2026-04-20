#!/usr/bin/env python3
"""Re-run Scope-B recap-ingest grader on JSON that embeds ``tool_trace`` + ``scenario``.

Sidecar artifacts from ``step1_recap_ingest_run`` often omit ``tool_trace``; this
script exits with status 2 in that case. For full traces, pass a JSON object
with keys ``scenario`` (gold scenario dict), ``tool_trace`` (list), and either
``final_text`` or ``detail`` (``PlanningTurnDetail``-shaped dict).

Example::

    uv run python scripts/regrade_scope_b.py trace_bundle.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from evals.session_recap_ingest_vertical_slice.scope_b_grader import (
    collect_scope_b_recap_ingest_violations,
)
from src.agent.planner import PlanningTurnDetail


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: regrade_scope_b.py <bundle.json>", file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    data = json.loads(path.read_text(encoding="utf-8"))
    tt = data.get("tool_trace")
    if not isinstance(tt, list):
        print(
            "regrade_scope_b: no tool_trace array in JSON; sidecar summaries cannot be re-graded.",
            file=sys.stderr,
        )
        return 2
    scenario = data.get("scenario")
    if not isinstance(scenario, dict):
        print("regrade_scope_b: missing scenario object", file=sys.stderr)
        return 2
    final_text = data.get("final_text", "")
    if isinstance(data.get("detail"), dict):
        d = data["detail"]
        final_text = str(d.get("final_text") or final_text)
    detail = PlanningTurnDetail(
        final_text=final_text,
        last_response_id=str(data.get("last_response_id") or "regrade"),
        tool_trace=tt,
    )
    corpus = data.get("corpus_path") or data.get("corpus_dir")
    corpus_path = Path(str(corpus)) if corpus else Path(".")
    v = collect_scope_b_recap_ingest_violations(scenario, detail, corpus_path)
    print(json.dumps(v, indent=2, ensure_ascii=False))
    return 0 if not v else 1


if __name__ == "__main__":
    raise SystemExit(main())
