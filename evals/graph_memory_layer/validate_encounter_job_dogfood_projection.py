from __future__ import annotations

# Module: validate_encounter_job_dogfood_projection

import argparse
import json
from pathlib import Path
from typing import Any

from evals.graph_memory_layer.encounter_job_dogfood_fixture import dogfood_result_to_payload, run_glowkindle_encounter_job_dogfood
from evals.graph_memory_layer.report_encounter_job_dogfood_projection import render_report

DEFAULT_OUT_DIR = Path("evals/graph_memory_layer/artifacts/encounter_job_dogfood_projection")
ARTIFACT_NAME = "c1s1_glowkindle_fixture_candidate_graph.json"
REPORT_NAME = "c1s1_glowkindle_fixture_report.md"
EXPECTED_FALSE = {"has_duplicate_pc_nodes", "has_invalid_predicate_issues", "has_dropped_edges"}


def build_payload() -> dict[str, Any]:
    return dogfood_result_to_payload(run_glowkindle_encounter_job_dogfood())


def validate_payload(payload: dict[str, Any] | None = None, *, compare_artifact: bool = True, artifact_path: Path | None = None) -> dict[str, Any]:
    payload = payload or build_payload()
    checks = payload["checks"]
    failures = [k for k, v in checks.items() if (k in EXPECTED_FALSE and v is not False) or (k not in EXPECTED_FALSE and v is not True)]
    if failures:
        raise AssertionError(f"Encounter/job dogfood checks failed: {failures}")
    path = artifact_path or DEFAULT_OUT_DIR / ARTIFACT_NAME
    if compare_artifact and path.exists():
        checked_in = json.loads(path.read_text(encoding="utf-8"))
        if checked_in != payload:
            raise AssertionError(f"Checked-in artifact is stale: {path}")
    return payload


def write_artifacts(out_dir: Path = DEFAULT_OUT_DIR) -> dict[str, Any]:
    payload = validate_payload(compare_artifact=False)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / ARTIFACT_NAME).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / REPORT_NAME).write_text(render_report(payload), encoding="utf-8")
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args(argv)
    if args.write:
        write_artifacts(args.out_dir)
        print(f"Encounter/job dogfood projection artifacts written to {args.out_dir}")
    else:
        validate_payload(artifact_path=args.out_dir / ARTIFACT_NAME)
        print("Encounter/job dogfood projection validated successfully.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
