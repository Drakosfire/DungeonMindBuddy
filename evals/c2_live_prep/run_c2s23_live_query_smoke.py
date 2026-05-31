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

from apps.live_control_server.config import repo_root
from apps.live_control_server.services.live_agent_loop import process_live_query

ROOT = repo_root()
DEFAULT_SESSION_DIR = ROOT / "evals/c2_live_prep/live/session_23"
DEFAULT_OUTPUT_DIR = ROOT / "evals/c2_live_prep/artifacts/runs" / str(date.today())
DEFAULT_QUESTION = "What Session 22 outcomes matter for Session 23 prep?"


def _utc_now_z() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session-dir", type=Path, default=DEFAULT_SESSION_DIR)
    parser.add_argument("--question", type=str, default=DEFAULT_QUESTION)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    response = process_live_query(
        args.question,
        base=args.session_dir.resolve(),
        root=ROOT,
    )
    packet = response.get("context_packet") or {}
    citations = response.get("citations") or []
    smoke = {
        "schema": "dmb_c2s23_live_query_context_smoke_v1",
        "generated_at": _utc_now_z(),
        "question": args.question,
        "has_answer": bool(str(response.get("answer") or "").strip()),
        "has_context_packet": bool(packet),
        "admitted_count": len(packet.get("admitted_evidence") or []),
        "rejected_count": len(packet.get("rejected_evidence") or []),
        "admitted_count_min": 1,
        "rejected_count_min": 1,
        "answer_has_evidence_citation": bool(citations),
        "mutations_count": len(response.get("mutations") or []),
        "mode": response.get("mode"),
        "status": response.get("status"),
        "warnings": response.get("warnings") or [],
    }

    out_dir = args.output_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "c2s23_live_query_context_smoke.json"
    out_path.write_text(json.dumps(smoke, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(out_path.relative_to(ROOT)), "smoke": smoke}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
