#!/usr/bin/env python3
"""Run blind manifest-backed query/admission for C2S23 dogfood questions."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.live_play.manifest_context_query import QueryRequest, build_context_packet, load_manifest
from src.live_play.session_paths import repo_root

ROOT = repo_root()

DEFAULT_QUESTIONS = ROOT / "evals/c2_live_prep/benchmarks/c2s23_dogfood_questions.seed.json"
DEFAULT_MANIFEST = ROOT / "evals/c2_live_prep/benchmarks/c2s23_planning_corpus_manifest.json"
DEFAULT_OUTPUT_DIR = ROOT / "evals/c2_live_prep/artifacts/runs" / str(date.today())


def _utc_now_z() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_questions(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [q for q in list(payload.get("questions") or []) if isinstance(q, dict)]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--questions", type=Path, default=DEFAULT_QUESTIONS)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    manifest = load_manifest(args.manifest.resolve())
    questions = load_questions(args.questions.resolve())
    out_dir = args.output_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    packets: list[dict[str, Any]] = []
    for row in questions:
        qid = str(row.get("id") or "").strip()
        question = str(row.get("question") or "").strip()
        if not qid or not question:
            continue
        request = QueryRequest(question_id=qid, question=question, category=str(row.get("category") or "") or None)
        packet = build_context_packet(request, manifest, root=ROOT)
        packets.append(packet)
        out_path = out_dir / f"c2s23_manifest_query_context_packet_{qid}.json"
        out_path.write_text(json.dumps(packet, indent=2, ensure_ascii=False), encoding="utf-8")

    summary = {
        "schema": "dmb_c2s23_manifest_query_context_run_v1",
        "generated_at": _utc_now_z(),
        "manifest_path": str(args.manifest.resolve().relative_to(ROOT)),
        "questions_path": str(args.questions.resolve().relative_to(ROOT)),
        "packet_count": len(packets),
        "all_preconditions_present": all(
            bool(p.get("corpus_preconditions", {}).get("all_required_present")) for p in packets
        ),
        "packets": [
            {
                "question_id": p["question_id"],
                "intent_class": p["intent_class"],
                "retrieved_count": len(p["retrieved_evidence"]),
                "admitted_count": len(p["admitted_evidence"]),
                "rejected_count": len(p["rejected_evidence"]),
                "capability_status": p["capability_status"]["status"],
                "blocked_or_missing_count": len(p["blocked_or_missing"]),
            }
            for p in packets
        ],
    }
    summary_name = "c2s23_manifest_query_context_summary.json"
    (out_dir / summary_name).write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    last = ROOT / "evals/c2_live_prep/artifacts/last_c2s23_manifest_query_context_summary.json"
    last.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "output_dir": str(out_dir.relative_to(ROOT)),
                "summary": summary_name,
                "packet_count": len(packets),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
