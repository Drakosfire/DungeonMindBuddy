from __future__ import annotations

import argparse
import json
from pathlib import Path

from evals.graph_memory_layer import live_extractor_prompt_harness as h
from evals.graph_memory_layer.live_vs_gold_compare import compare_live_candidate_file
from evals.graph_memory_layer.reconcile_live_candidate import validate_live_candidate_output


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-bundle", required=True)
    ap.add_argument("--source-recap", required=True)
    ap.add_argument("--candidate-output", required=True)
    ap.add_argument("--report-out", help="optional path to write JSON report")
    args = ap.parse_args()
    verified = h.verify_run_bundle_and_source(Path(args.run_bundle), Path(args.source_recap))
    allowed = {r["source_span_ref_id"] for r in h.source_packet_rows(verified)}
    raw = json.loads(Path(args.candidate_output).read_text(encoding="utf-8"))
    validation = validate_live_candidate_output(raw, run_bundle=Path(args.run_bundle), allowed_span_refs=allowed)
    comparison = compare_live_candidate_file(Path(args.candidate_output), reconciled_graph=validation["reconciled_candidate_graph"])
    report = {"validation": validation, "comparison": comparison}
    if args.report_out:
        Path(args.report_out).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
