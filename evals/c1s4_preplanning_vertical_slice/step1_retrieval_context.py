from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evals.c1s4_preplanning_vertical_slice.preplanning_context_bundle import build_preplanning_context_bundle
from evals.c1s4_preplanning_vertical_slice.step0_kb_materialize import DEFAULT_POLICY_PATH, load_kb_manifest
from src.agent.session_memory_query import query_session_memory_candidate

TASK_PATH = Path(__file__).resolve().parent / "gold/preplanning_task.json"


class C1S4BoundaryError(RuntimeError):
    """Raised when Step 0 or bundle checks detect boundary violations."""


def run_step1() -> dict[str, Any]:
    policy = json.loads(DEFAULT_POLICY_PATH.read_text(encoding="utf-8"))
    task = json.loads(TASK_PATH.read_text(encoding="utf-8"))
    manifest, records = load_kb_manifest(DEFAULT_POLICY_PATH)
    if manifest["forbidden_path_hits"] or manifest["forbidden_session_hits"] or manifest.get("unexpected_session_hits"):
        raise C1S4BoundaryError("Step 0 manifest is not oracle-safe; aborting Step 1 retrieval")

    records_by_unit_id = {str(r.get("unit_id")): r for r in records if str(r.get("unit_id") or "")}
    bundles = []
    for q in task["queries"]:
        result = query_session_memory_candidate(
            records=records,
            query=q["query"],
            campaign_id=task["campaign_id"],
            session_min=min(task["allowed_sessions"]),
            session_max=max(task["allowed_sessions"]),
            max_hits=8,
        )
        bundle = build_preplanning_context_bundle(
            kb_id=task["kb_id"],
            campaign_id=task["campaign_id"],
            allowed_sessions=task["allowed_sessions"],
            heldout_sessions=task["heldout_sessions"],
            query=q["query"],
            retrieval_result=result,
            forbidden_oracle_relpaths=policy["forbidden_oracle_relpaths"],
            records_by_unit_id=records_by_unit_id,
        )
        bundles.append({"query_id": q["query_id"], "bundle": bundle})
    return {"schema": "dmb_c1s4_preplanning_step1_summary_v1", "kb_manifest": manifest, "task_id": task["task_id"], "bundles": bundles}


def main() -> int:
    try:
        summary = run_step1()
    except C1S4BoundaryError as exc:
        print(json.dumps({"schema": "dmb_c1s4_preplanning_step1_summary_v1", "error": str(exc)}, indent=2, sort_keys=True))
        return 1
    print(json.dumps(summary, indent=2, sort_keys=True))
    leaks = []
    for b in summary["bundles"]:
        check = b["bundle"]["oracle_leakage_check"]
        leaks.extend(check["forbidden_path_hits"])
        leaks.extend(check["forbidden_session_hits"])
    return 1 if leaks else 0


if __name__ == "__main__":
    raise SystemExit(main())
