#!/usr/bin/env python3
"""PR98 smoke: live query path uses manifest-backed context packet."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.live_control_server.config import repo_root  # noqa: E402
from apps.live_control_server.services.live_agent_loop import process_live_query  # noqa: E402

ROOT = repo_root()
DEFAULT_SESSION_DIR = ROOT / "evals/c2_live_prep/live/session_23"
DEFAULT_OUTPUT_DIR = ROOT / "evals/c2_live_prep/artifacts/runs" / str(date.today())
DEFAULT_QUESTION = "What Session 22 outcomes matter for Session 23 prep?"
DEFAULT_REJECTION_QUESTION = (
    "After ingesting Session 22 raw notes, what Session 22 outcomes matter for Session 23 prep?"
)
DEFAULT_MANIFEST_PATH = "evals/c2_live_prep/benchmarks/c2s23_planning_corpus_manifest.json"


def _utc_now_z() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session-dir", type=Path, default=DEFAULT_SESSION_DIR)
    parser.add_argument("--question", type=str, default=DEFAULT_QUESTION)
    parser.add_argument("--rejection-question", type=str, default=DEFAULT_REJECTION_QUESTION)
    parser.add_argument("--manifest-path", type=str, default=DEFAULT_MANIFEST_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    cases = [
        {"name": "baseline", "question": args.question, "admitted_count_min": 1, "rejected_count_min": 0},
        {
            "name": "rejection_authority",
            "question": args.rejection_question,
            "admitted_count_min": 1,
            "rejected_count_min": 1,
        },
    ]

    case_results: list[dict[str, object]] = []
    all_ok = True
    for case in cases:
        response = process_live_query(
            str(case["question"]),
            base=args.session_dir.resolve(),
            root=ROOT,
            request_manifest_path=args.manifest_path,
        )
        packet = response.get("context_packet") or {}
        citations = response.get("citations") or []
        warnings = response.get("warnings") or []
        has_llm_fallback_warning = "llm_grounding_call_failed" in warnings
        smoke = {
            "name": case["name"],
            "question": case["question"],
            "has_answer": bool(str(response.get("answer") or "").strip()),
            "has_context_packet": bool(packet),
            "admitted_count": len(packet.get("admitted_evidence") or []),
            "rejected_count": len(packet.get("rejected_evidence") or []),
            "admitted_count_min": int(case["admitted_count_min"]),
            "rejected_count_min": int(case["rejected_count_min"]),
            "answer_has_evidence_citation": bool(citations),
            "mutations_count": len(response.get("mutations") or []),
            "mode": response.get("mode"),
            "status": response.get("status"),
            "warnings": warnings,
            "llm_path_available": not has_llm_fallback_warning,
        }
        smoke_ok = (
            bool(smoke["has_answer"])
            and bool(smoke["has_context_packet"])
            and int(smoke["admitted_count"]) >= int(smoke["admitted_count_min"])
            and int(smoke["rejected_count"]) >= int(smoke["rejected_count_min"])
            and bool(smoke["answer_has_evidence_citation"])
            and int(smoke["mutations_count"]) == 0
            and smoke["mode"] == "context_lookup"
            and smoke["status"] == "ok"
        )
        smoke["ok"] = smoke_ok
        all_ok = all_ok and smoke_ok
        case_results.append(smoke)

    smoke_report = {
        "schema": "dmb_c2s23_live_query_context_smoke_v2",
        "generated_at": _utc_now_z(),
        "manifest_path": args.manifest_path,
        "cases": case_results,
    }

    out_dir = args.output_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "c2s23_live_query_context_smoke.json"
    out_path.write_text(json.dumps(smoke_report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"ok": all_ok, "output": str(out_path.relative_to(ROOT)), "smoke": smoke_report}, indent=2))
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
