from __future__ import annotations

import argparse
import json
from pathlib import Path

from evals.graph_memory_layer import live_extractor_prompt_harness as h


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidate-output", required=True)
    a = ap.parse_args()
    raw = json.loads(Path(a.candidate_output).read_text(encoding="utf-8"))
    report = h.validate_candidate_output(raw)
    print("# Live Extractor Candidate Output Report")
    for k, v in report.get("candidate_class_counts", {}).items():
        print(f"- {k}: {v}")
    print(f"- evidence_ref_count: {report.get('evidence_ref_count')}")
    print(f"- canonical_ir_valid: {report.get('canonical_ir_valid')}")


if __name__ == "__main__":
    main()
